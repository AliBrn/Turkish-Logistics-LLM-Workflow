import json
import re
from dataclasses import dataclass
from typing import Any

BASE_MODEL_ID = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
ADAPTER_ID = "AlBarann/lojistik-qwen25-7b-lora-adapter"

SYSTEM_PROMPT = (
    "Sen lojistik WhatsApp mesajlarından yapılandırılmış sipariş bilgisi çıkaran asistansın. "
    "Önce açık rota, yük, araç ve kasa bilgisini kullan. Eksik alanlarda lojistik bağlamı ve "
    "standart araç/kasa/yük tipi kurallarını uygula. Çoklu rotaları ayrı sipariş objelerine böl "
    "ve ortak bilgileri ilgili tüm siparişlere taşı. Çıktıda yalnızca geçerli JSON üret. "
    'JSON şeması: {"siparis_sayisi": number, "siparisler": [{"nereden": "string", '
    '"nereye": "string", "yuk_tipi": "string", "arac_tipi": "string", "kasa_tipi": "string"}]}'
)


class ModelOutputParseError(ValueError):
    pass


@dataclass
class LoadedModel:
    tokenizer: Any
    model: Any


_loaded: LoadedModel | None = None


def strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def extract_first_json(text: str) -> dict[str, Any]:
    clean = strip_think(text)
    start = clean.find("{")
    if start < 0:
        raise ModelOutputParseError("Model cevabında JSON başlangıcı bulunamadı.")

    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(clean[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                payload = clean[start : index + 1]
                parsed = json.loads(payload)
                if not isinstance(parsed, dict):
                    raise ModelOutputParseError("Model JSON cevabı obje değil.")
                return parsed

    raise ModelOutputParseError("Model cevabındaki JSON tamamlanmamış görünüyor.")


def load_model() -> LoadedModel:
    global _loaded
    if _loaded is not None:
        return _loaded

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    quant_config = BitsAndBytesConfig(load_in_4bit=True)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
    model = PeftModel.from_pretrained(base_model, ADAPTER_ID)
    model.eval()

    _loaded = LoadedModel(tokenizer=tokenizer, model=model)
    return _loaded


class Qwen25Extractor:
    """server.py tarafından kullanılan yüksek seviyeli sınıf."""

    def __init__(self) -> None:
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return _loaded is not None

    def extract(self, message_text: str, max_new_tokens: int = 1200) -> dict[str, Any]:
        raw_text, parsed = generate(message_text, max_new_tokens=max_new_tokens)
        return {"raw_text": raw_text, "parsed_json": parsed}


def generate(message_text: str, max_new_tokens: int = 1200) -> tuple[str, dict[str, Any]]:
    import torch

    loaded = load_model()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message_text},
    ]
    prompt = loaded.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = loaded.tokenizer(prompt, return_tensors="pt").to(loaded.model.device)
    with torch.no_grad():
        outputs = loaded.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            pad_token_id=loaded.tokenizer.eos_token_id,
        )

    new_tokens = outputs[0][inputs["input_ids"].shape[-1] :]
    raw_text = loaded.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    parsed = extract_first_json(raw_text)
    return raw_text, parsed
