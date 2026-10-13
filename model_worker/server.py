from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .qwen25_inference import ADAPTER_ID, BASE_MODEL_ID, ModelOutputParseError, Qwen25Extractor


app = FastAPI(title="Qwen2.5 Lojistik Model Worker")
extractor = Qwen25Extractor()


class ExtractRequest(BaseModel):
    message_text: str
    max_new_tokens: int | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": extractor.is_loaded,
        "base_model": BASE_MODEL_ID,
        "adapter": ADAPTER_ID,
    }


@app.post("/extract")
def extract(payload: ExtractRequest):
    try:
        return extractor.extract(
            payload.message_text,
            max_new_tokens=payload.max_new_tokens or 1800,
        )
    except ModelOutputParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
