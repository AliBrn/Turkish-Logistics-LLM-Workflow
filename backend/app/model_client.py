import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from .model_utils import ModelOutputParseError, coerce_model_payload


class ModelClientError(RuntimeError):
    def __init__(self, message: str, raw_output: str = ""):
        super().__init__(message)
        self.raw_output = raw_output


class ModelClient(Protocol):
    def extract(self, message_text: str) -> dict:
        ...


def _fallback_enabled() -> bool:
    return os.getenv("MODEL_FALLBACK_FAKE", "0").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class FakeModelClient:
    """Temporary client that returns the same JSON schema as the real model."""

    def extract(self, message_text: str) -> dict:
        text = message_text.lower()

        if "frigo" in text and "kamyon" in text:
            orders = [
                {"nereden": "Mersin", "nereye": "Giresun", "yuk_tipi": "KOMPLE", "arac_tipi": "KAMYONET", "kasa_tipi": "FRİGO"},
                {"nereden": "Mersin", "nereye": "Van", "yuk_tipi": "KOMPLE", "arac_tipi": "KAMYONET", "kasa_tipi": "FRİGO"},
            ]
        elif "kömür" in text or "komur" in text or "mısır" in text or "misir" in text or "damper" in text:
            orders = [
                {"nereden": "Şırnak", "nereye": "Muş/Bulanık", "yuk_tipi": "DÖKME", "arac_tipi": "860", "kasa_tipi": "AÇIK + DAMPERLİ"}
            ]
        elif "palet" in text and "zekeriya" in text:
            orders = [
                {"nereden": "Nevşehir", "nereye": "İstanbul/Sarıyer/Zekeriyaköy", "yuk_tipi": "PALETLİ", "arac_tipi": "", "kasa_tipi": ""}
            ]
        elif "çorlu" in text or "corlu" in text:
            orders = [
                {"nereden": "Tekirdağ/Çorlu", "nereye": "İzmir", "yuk_tipi": "KOMPLE", "arac_tipi": "1360", "kasa_tipi": "AÇIK + KAPALI"},
                {"nereden": "Tekirdağ/Çorlu", "nereye": "Manisa", "yuk_tipi": "KOMPLE", "arac_tipi": "1360", "kasa_tipi": "KAPALI"},
            ]
        else:
            orders = [
                {"nereden": "Mersin", "nereye": "Batman", "yuk_tipi": "YÜKÜSTÜ", "arac_tipi": "1360", "kasa_tipi": "AÇIK"}
            ]

        return {"siparis_sayisi": len(orders), "siparisler": orders}


@dataclass
class Qwen25HttpModelClient:
    worker_url: str = "http://127.0.0.1:8010/extract"
    timeout_seconds: int = 12

    def extract(self, message_text: str) -> dict:
        body = json.dumps({"message_text": message_text}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.worker_url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return self._fallback_or_raise(message_text, f"Model worker HTTP hata döndürdü: {exc.code}", exc)
        except urllib.error.URLError as exc:
            return self._fallback_or_raise(message_text, f"Model worker bağlantısı kurulamadı: {exc}", exc)
        except TimeoutError as exc:
            return self._fallback_or_raise(message_text, "Model worker zaman aşımına uğradı.", exc)
        except json.JSONDecodeError as exc:
            return self._fallback_or_raise(message_text, f"Model worker JSON dışı cevap verdi: {exc}", exc)

        try:
            if "parsed_json" in response_payload:
                return coerce_model_payload(response_payload["parsed_json"])
            return coerce_model_payload(response_payload)
        except ModelOutputParseError as exc:
            return self._fallback_or_raise(message_text, str(exc), exc)

    def _fallback_or_raise(self, message_text: str, message: str, exc: Exception) -> dict:
        if _fallback_enabled():
            return FakeModelClient().extract(message_text)
        raise ModelClientError(message) from exc


@dataclass
class LMStudioModelClient:
    """LM Studio Local Server'a bağlanan OpenAI-uyumlu client (port 1234)."""

    base_url: str = "http://127.0.0.1:1234"
    model_name: str = "local-model"
    timeout_seconds: int = 60

    _SYSTEM_PROMPT: str = (
        "Lojistik mesajından JSON çıkar. Çoklu rotayı ayır. Sadece JSON döndür. "
        'Şema: {"siparis_sayisi":N,"siparisler":[{"nereden":"","nereye":"","yuk_tipi":"","arac_tipi":"","kasa_tipi":""}]}'
    )

    def extract(self, message_text: str) -> dict:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": message_text},
            ],
            "temperature": 0,
            "max_tokens": int(os.getenv("LMSTUDIO_MAX_TOKENS", "1600")),
            "stream": False,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return self._fallback_or_raise(message_text, f"LM Studio HTTP hata: {exc.code}", exc)
        except urllib.error.URLError as exc:
            return self._fallback_or_raise(message_text, f"LM Studio bağlantısı kurulamadı: {exc}", exc)
        except TimeoutError as exc:
            return self._fallback_or_raise(message_text, "LM Studio zaman aşımına uğradı.", exc)
        except json.JSONDecodeError as exc:
            return self._fallback_or_raise(message_text, f"LM Studio JSON dışı cevap verdi: {exc}", exc)

        try:
            raw_text = resp_data["choices"][0]["message"]["content"].strip()
            from .model_utils import extract_first_json_object
            parsed = extract_first_json_object(raw_text)
            return coerce_model_payload(parsed)
        except (KeyError, IndexError) as exc:
            return self._fallback_or_raise(message_text, f"LM Studio beklenmedik cevap formatı: {exc}", exc)
        except ModelOutputParseError as exc:
            return self._fallback_or_raise(message_text, str(exc), exc, raw_text)

    def _fallback_or_raise(self, message_text: str, message: str, exc: Exception, raw_output: str = "") -> dict:
        if _fallback_enabled():
            return FakeModelClient().extract(message_text)
        raise ModelClientError(message, raw_output) from exc


def get_model_client() -> ModelClient:
    mode = os.getenv("MODEL_CLIENT_MODE", "fake").strip().lower()
    if mode in {"qwen25", "qwen25_http", "http"}:
        return Qwen25HttpModelClient(
            worker_url=os.getenv("MODEL_WORKER_URL", "http://127.0.0.1:8010/extract"),
            timeout_seconds=int(os.getenv("MODEL_WORKER_TIMEOUT", "12")),
        )
    if mode == "lmstudio":
        return LMStudioModelClient(
            base_url=os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234"),
            model_name=os.getenv("LMSTUDIO_MODEL_NAME", "local-model"),
            timeout_seconds=int(os.getenv("MODEL_WORKER_TIMEOUT", "60")),
        )
    return FakeModelClient()


def get_model_client_status() -> dict:
    mode = os.getenv("MODEL_CLIENT_MODE", "fake").strip().lower()
    if mode in {"qwen25", "qwen25_http", "http"}:
        active = "Qwen25HttpModelClient"
    elif mode == "lmstudio":
        active = "LMStudioModelClient"
    else:
        active = "FakeModelClient"
    return {
        "mode": mode,
        "worker_url": os.getenv("MODEL_WORKER_URL", "http://127.0.0.1:8010/extract"),
        "lmstudio_url": os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234"),
        "lmstudio_model": os.getenv("LMSTUDIO_MODEL_NAME", "local-model"),
        "active_client": active,
        "fallback_fake": _fallback_enabled(),
        "timeout_seconds": int(os.getenv("MODEL_WORKER_TIMEOUT", "60")),
        "lmstudio_max_tokens": int(os.getenv("LMSTUDIO_MAX_TOKENS", "1600")),
    }
