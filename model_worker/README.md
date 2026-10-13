# Qwen2.5 Model Worker

Bu klasör Qwen2.5 base model + lojistik LoRA adapter test ve servis dosyalarını içerir.

Kullanılan model:

- Base model: `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`
- Adapter: `AlBarann/lojistik-qwen25-7b-lora-adapter`

Adapter tek başına çalışmaz. Her zaman base modelin üstüne takılarak kullanılır.

## 1. Bağımsız Test

```powershell
cd "C:\Users\msi\Desktop\Benchmark Testi\WorkFlow Project"
py -m venv .model-venv
.model-venv\Scripts\python.exe -m pip install -r model_worker\requirements-model.txt
.model-venv\Scripts\python.exe model_worker\test_qwen25_client.py
```

İlk çalıştırmada base model ve adapter indirileceği için zaman alabilir.

## 2. Model Worker Başlatma

```powershell
cd "C:\Users\msi\Desktop\Benchmark Testi\WorkFlow Project"
.model-venv\Scripts\python.exe -m uvicorn model_worker.server:app --host 127.0.0.1 --port 8010
```

Sağlık kontrolü:

```text
http://127.0.0.1:8010/health
```

Çıkarım endpointi:

```text
POST http://127.0.0.1:8010/extract
```

Örnek istek:

```json
{
  "message_text": "Mersin -> Batman açık 1360 kasa içi makina"
}
```

## 3. Backend'i Gerçek Model Modunda Çalıştırma

Model worker açıkken ayrı terminalde:

```powershell
cd "C:\Users\msi\Desktop\Benchmark Testi\WorkFlow Project"
powershell -ExecutionPolicy Bypass -File backend\run_backend_qwen25.ps1
```

Frontend aynı kalır. `AI ile Çözümle` butonu backend'e gider, backend de model worker'a istek atar.

## Not

Worker kapalıysa backend çökmemeli; ilgili mesaj `hata` durumuna düşer ve doğrulama sorunu açılır.
