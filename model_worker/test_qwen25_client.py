import json
import time

from qwen25_inference import Qwen25Extractor


SAMPLE_MESSAGES = [
    "Mersin -> Batman açık 1360 kasa içi makina",
    "YARIN SABAH ÇERKEZKÖYDEN YÜKLER\nKAĞITHANE AÇIK 10 TEKER",
    (
        "Mersin -> Ankara Frigo Tır\n"
        "Mersin -> Konya Frigo Tır\n"
        "Mersin -> Kayseri Frigo Kamyon"
    ),
    (
        "📌Mersin Akdeniz-İzmir Konak Tenteli TIR 25ton 25Palet\n"
        "📌Düzce-İzmir Çiğli TIR 8ton\n"
        "📌Antalya-Adana Kapalı/Açık 10 teker\n"
        "📌Ankara Şereflikoçhisar-Kocaeli Gölcük Kapalı/Açık TIR"
    ),
]


def print_result(label: str, message: str, result: dict) -> None:
    print("\n" + "=" * 80)
    print(label)
    print("-" * 80)
    print("MESAJ:")
    print(message)
    print("-" * 80)
    print("RAW:")
    print(result["raw_text"])
    print("-" * 80)
    print("PARSED JSON:")
    print(json.dumps(result["parsed_json"], ensure_ascii=False, indent=2))


def main() -> None:
    extractor = Qwen25Extractor()
    print("Qwen2.5 base + lojistik adapter yükleniyor. İlk çalıştırma model indirebilir.")
    extractor.load()
    print("Model hazır.")

    for index, message in enumerate(SAMPLE_MESSAGES, start=1):
        started_at = time.perf_counter()
        result = extractor.extract(message)
        elapsed = time.perf_counter() - started_at
        print_result(f"ÖRNEK TEST {index} - {elapsed:.1f} sn", message, result)

    while True:
        print("\nKendi mesajını yaz. Çıkmak için boş bırakıp Enter bas.")
        message = input("> ").strip()
        if not message:
            break
        started_at = time.perf_counter()
        result = extractor.extract(message)
        elapsed = time.perf_counter() - started_at
        print_result(f"MANUEL TEST - {elapsed:.1f} sn", message, result)


if __name__ == "__main__":
    main()
