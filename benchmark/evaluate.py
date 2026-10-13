import json
import csv
import re
import argparse
from typing import Any, Dict, List, Tuple, Optional


FIELDS = ["nereden", "nereye", "yuk_tipi", "arac_tipi", "kasa_tipi"]
PARTIAL_FIELDS = ["arac_tipi", "kasa_tipi"]


def normalize_text(value: Any) -> str:
    """
    Karşılaştırma için metni sadeleştirir.
    Büyük/küçük harf farkını kaldırır, fazla boşlukları temizler.
    Türkçe karakterler korunur.
    """
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text.upper()


def split_plus_values(value: Any) -> List[str]:
    """
    AÇIK + KAPALI gibi alternatifli alanları listeye çevirir.
    """
    text = normalize_text(value)

    if not text:
        return []

    parts = [part.strip() for part in text.split("+") if part.strip()]
    return sorted(parts)


def normalize_plus_values(value: Any) -> str:
    """
    AÇIK + KAPALI ile KAPALI + AÇIK aynı kabul edilsin diye
    + ile ayrılmış değerleri sıralar.
    """
    parts = split_plus_values(value)

    if not parts:
        return ""

    return " + ".join(parts)


def compare_partial_plus_field(gold_value: Any, model_value: Any) -> Tuple[float, str]:
    """
    arac_tipi ve kasa_tipi için puanlama yapar.

    Tam eşleşme:
        Gold: AÇIK + KAPALI
        Model: KAPALI + AÇIK
        Puan: 1

    Kısmi eşleşme:
        Gold: AÇIK + KAPALI
        Model: AÇIK
        Puan: 0.5

    Yanlış:
        Gold: AÇIK + KAPALI
        Model: FRİGO
        Puan: 0
    """
    gold_parts = split_plus_values(gold_value)
    model_parts = split_plus_values(model_value)

    gold_norm = " + ".join(gold_parts)
    model_norm = " + ".join(model_parts)

    if gold_norm == model_norm:
        return 1.0, "tam"

    if not gold_parts or not model_parts:
        return 0.0, "yanlış"

    common = set(gold_parts).intersection(set(model_parts))

    if common:
        return 0.5, "kısmi"

    return 0.0, "yanlış"


def split_location_parts(value: Any) -> List[str]:
    """
    Lokasyonu il/ilçe/parça seviyesinde ayırır.

    Örnek:
    'İstanbul/Başakşehir/İkitelli'
    -> ['İSTANBUL', 'BAŞAKŞEHİR', 'İKİTELLİ', 'İSTANBUL/BAŞAKŞEHİR/İKİTELLİ']

    Slash varsa parçalı karşılaştırma yapılır.
    Tam metin de listeye eklenir.
    """
    text = normalize_text(value)

    if not text:
        return []

    raw_parts = re.split(r"[\/]", text)

    parts = []
    for part in raw_parts:
        part = part.strip()
        if part:
            parts.append(part)

    if text not in parts:
        parts.append(text)

    return parts


def location_match(gold_value: Any, model_value: Any) -> bool:
    """
    nereden/nereye alanları için esnek karşılaştırma yapar.

    Doğru kabul edilen örnekler:
    - İstanbul/Başakşehir == Başakşehir
    - Kocaeli/Gebze == Gebze
    - İstanbul/Başakşehir == İstanbul
    - İstanbul Başakşehir == Başakşehir
    - Mersin/Akdeniz == Mersin
    """
    gold = normalize_text(gold_value)
    model = normalize_text(model_value)

    if gold == model:
        return True

    if not gold or not model:
        return False

    gold_parts = split_location_parts(gold)
    model_parts = split_location_parts(model)

    for g in gold_parts:
        for m in model_parts:
            if g == m:
                return True

    if gold in model or model in gold:
        return True

    return False


def load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def unwrap_examples(data: Any) -> List[Dict[str, Any]]:
    """
    Dosya şu şekillerde olabilir:
    1) Direkt liste: [{...}, {...}]
    2) Ana obje içinde ornekler: {"ornekler": [{...}]}
    3) Ana obje içinde examples: {"examples": [{...}]}
    4) Ana obje içinde data: {"data": [{...}]}
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if "ornekler" in data and isinstance(data["ornekler"], list):
            return data["ornekler"]

        if "examples" in data and isinstance(data["examples"], list):
            return data["examples"]

        if "data" in data and isinstance(data["data"], list):
            return data["data"]

    raise ValueError("Dosya formatı anlaşılmadı. Liste veya {'ornekler': [...]} formatı bekleniyor.")


def get_example_id(example: Dict[str, Any], index: int) -> str:
    """
    Örneğin eşleşme ID'sini bulur.
    Öncelik:
    id > ornek_no > kaynak_index > sıra numarası
    """
    if "id" in example:
        return str(example["id"])

    if "ornek_no" in example:
        return str(example["ornek_no"])

    if "kaynak_index" in example:
        return str(example["kaynak_index"])

    return str(index + 1)


def extract_gold_output(example: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Gold cevap farklı isimlerle gelebilir:
    - gold
    - expected_output
    - output
    - cevap
    - answer
    """
    for key in ["gold", "expected_output", "output", "cevap", "answer"]:
        if key in example and isinstance(example[key], dict):
            return example[key]

    return None


def parse_model_output(raw_output: Any) -> Tuple[Optional[Dict[str, Any]], bool, str]:
    """
    Model cevabını JSON objesine çevirir.

    Desteklenen durumlar:
    - model_output zaten dict ise direkt kullanılır.
    - model_output string ise json.loads denenir.
    - Markdown kod bloğu varsa temizlenir.
    - JSON öncesi/sonrası açıklama varsa ilk { ile son } arası alınır.
    """
    if isinstance(raw_output, dict):
        return raw_output, True, ""

    if raw_output is None:
        return None, False, "model_output boş"

    if not isinstance(raw_output, str):
        return None, False, f"model_output desteklenmeyen tip: {type(raw_output)}"

    text = raw_output.strip()

    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    first = text.find("{")
    last = text.rfind("}")

    if first != -1 and last != -1 and last > first:
        text = text[first:last + 1]

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed, True, ""
        return None, False, "JSON parse edildi ama obje değil"
    except json.JSONDecodeError as e:
        return None, False, f"JSON parse hatası: {e}"


def extract_model_output(example: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], bool, str]:
    """
    Model cevabı farklı isimlerle gelebilir:
    - model_output
    - output
    - response
    - cevap

    Ayrıca örneğin kendisi direkt siparis_sayisi + siparisler içeren obje de olabilir.
    """
    for key in ["model_output", "output", "response", "cevap"]:
        if key in example:
            return parse_model_output(example[key])

    if "siparis_sayisi" in example and "siparisler" in example:
        return example, True, ""

    return None, False, "Model cevabı bulunamadı. model_output/output/response alanı bekleniyor."


def build_model_map(model_examples: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Model çıktılarını ID'ye göre mapler.
    """
    model_map = {}

    for i, ex in enumerate(model_examples):
        ex_id = get_example_id(ex, i)
        model_map[ex_id] = ex

    return model_map


def compare_orders(
    gold_orders: List[Dict[str, Any]],
    model_orders: List[Dict[str, Any]]
) -> Tuple[Dict[str, float], List[str], float, int, int, int, int]:
    """
    Siparişleri rota bazlı eşleştirir ve alan puanlarını üretir.

    Dönenler:
    - field_scores: alan bazlı doğru/kısmi puanlar
    - notes: hata notları
    - earned: kazanılan puan
    - possible: maksimum alan puanı
    - matched_order_count: eşleşen sipariş sayısı
    - missing_order_count: gold'da olup modelde bulunamayan sipariş sayısı
    - extra_order_count: modelde olup gold ile eşleşmeyen sipariş sayısı
    """
    field_scores = {field: 0.0 for field in FIELDS}
    notes = []

    earned = 0.0
    possible = len(gold_orders) * len(FIELDS)

    used_model_indexes = set()
    matched_order_count = 0

    for gold_idx, gold_order in enumerate(gold_orders):
        matched_index = None

        for model_idx, model_order in enumerate(model_orders):
            if model_idx in used_model_indexes:
                continue

            if (
                location_match(gold_order.get("nereden", ""), model_order.get("nereden", ""))
                and
                location_match(gold_order.get("nereye", ""), model_order.get("nereye", ""))
            ):
                matched_index = model_idx
                break

        if matched_index is None:
            notes.append(
                f"Gold sipariş {gold_idx + 1} için rota eşleşmedi: "
                f"{gold_order.get('nereden', '')} -> {gold_order.get('nereye', '')}"
            )
            continue

        matched_order_count += 1
        used_model_indexes.add(matched_index)
        model_order = model_orders[matched_index]

        for field in FIELDS:
            gold_value = gold_order.get(field, "")
            model_value = model_order.get(field, "")

            score = 0.0

            if field in ["nereden", "nereye"]:
                score = 1.0 if location_match(gold_value, model_value) else 0.0

            elif field in PARTIAL_FIELDS:
                score, match_type = compare_partial_plus_field(gold_value, model_value)

                if score == 0.5:
                    notes.append(
                        f"Kısmi eşleşme [{field}] | "
                        f"Gold: '{gold_value}' | Model: '{model_value}'"
                    )

            else:
                gold_norm = normalize_text(gold_value)
                model_norm = normalize_text(model_value)
                score = 1.0 if gold_norm == model_norm else 0.0

            field_scores[field] += score
            earned += score

            if score == 0.0:
                notes.append(
                    f"Alan hatası [{field}] | "
                    f"Gold: '{gold_value}' | Model: '{model_value}'"
                )

    missing_order_count = len(gold_orders) - matched_order_count
    extra_order_count = len(model_orders) - matched_order_count

    if extra_order_count > 0:
        notes.append(f"Modelde gold ile eşleşmeyen fazladan sipariş sayısı: {extra_order_count}")

    if missing_order_count > 0:
        notes.append(f"Modelin kaçırdığı/eksik sipariş sayısı: {missing_order_count}")

    return (
        field_scores,
        notes,
        earned,
        possible,
        matched_order_count,
        missing_order_count,
        extra_order_count
    )


def evaluate_example(
    example_id: str,
    gold_output: Dict[str, Any],
    model_raw_example: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Tek örneği değerlendirir.
    """
    result = {
        "id": example_id,
        "json_valid": 0,
        "siparis_sayisi_score": 0,
        "matched_order_count": 0,
        "missing_order_count": 0,
        "extra_order_count": 0,
        "nereden_score": 0.0,
        "nereye_score": 0.0,
        "yuk_tipi_score": 0.0,
        "arac_tipi_score": 0.0,
        "kasa_tipi_score": 0.0,
        "earned_score": 0.0,
        "max_score": 0,
        "accuracy": 0.0,
        "notes": ""
    }

    gold_orders = gold_output.get("siparisler", [])

    if not isinstance(gold_orders, list):
        result["notes"] = "Gold siparisler listesi geçersiz"
        return result

    gold_count = gold_output.get("siparis_sayisi", len(gold_orders))

    max_score = 1 + 1 + (len(gold_orders) * len(FIELDS))
    result["max_score"] = max_score

    if model_raw_example is None:
        result["notes"] = "Model çıktısı bulunamadı"
        return result

    model_output, json_valid, parse_error = extract_model_output(model_raw_example)

    if not json_valid or model_output is None:
        result["notes"] = parse_error
        return result

    result["json_valid"] = 1
    result["earned_score"] += 1

    model_orders = model_output.get("siparisler", [])

    if not isinstance(model_orders, list):
        result["notes"] = "Model siparisler listesi geçersiz"
        result["accuracy"] = round(result["earned_score"] / result["max_score"], 4) if result["max_score"] else 0.0
        return result

    model_count = model_output.get("siparis_sayisi", len(model_orders))

    if model_count == gold_count and len(model_orders) == len(gold_orders):
        result["siparis_sayisi_score"] = 1
        result["earned_score"] += 1
    else:
        result["notes"] += (
            f"siparis_sayisi hatası | Gold: {gold_count}, "
            f"Model siparis_sayisi: {model_count}, "
            f"Model liste uzunluğu: {len(model_orders)}. "
        )

    (
        field_scores,
        notes,
        field_earned,
        field_possible,
        matched_order_count,
        missing_order_count,
        extra_order_count
    ) = compare_orders(gold_orders, model_orders)

    result["matched_order_count"] = matched_order_count
    result["missing_order_count"] = missing_order_count
    result["extra_order_count"] = extra_order_count

    for field in FIELDS:
        result[f"{field}_score"] = field_scores[field]

    result["earned_score"] += field_earned

    if notes:
        if result["notes"]:
            result["notes"] += " | "
        result["notes"] += " | ".join(notes)

    result["earned_score"] = round(result["earned_score"], 4)
    result["accuracy"] = round(result["earned_score"] / result["max_score"], 4) if result["max_score"] else 0.0

    return result


def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tüm örneklerin genel özetini çıkarır.
    """
    total_earned = sum(float(r["earned_score"]) for r in results)
    total_max = sum(int(r["max_score"]) for r in results)

    total_gold_orders = sum(
        max((int(r["max_score"]) - 2) // len(FIELDS), 0)
        for r in results
    )

    summary = {
        "total_examples": len(results),
        "total_gold_orders": total_gold_orders,
        "total_earned_score": round(total_earned, 4),
        "total_max_score": total_max,
        "overall_accuracy": round(total_earned / total_max, 4) if total_max else 0.0,
        "overall_accuracy_percent": round((total_earned / total_max) * 100, 2) if total_max else 0.0,
        "json_valid_rate": round(sum(r["json_valid"] for r in results) / len(results), 4) if results else 0.0,
        "siparis_sayisi_accuracy": round(sum(r["siparis_sayisi_score"] for r in results) / len(results), 4) if results else 0.0,
        "matched_order_count": sum(r["matched_order_count"] for r in results),
        "missing_order_count": sum(r["missing_order_count"] for r in results),
        "extra_order_count": sum(r["extra_order_count"] for r in results),
    }

    for field in FIELDS:
        score_key = f"{field}_score"
        total_field_correct = sum(float(r[score_key]) for r in results)

        summary[f"{field}_score_total"] = round(total_field_correct, 4)
        summary[f"{field}_accuracy"] = (
            round(total_field_correct / total_gold_orders, 4)
            if total_gold_orders else 0.0
        )
        summary[f"{field}_accuracy_percent"] = (
            round((total_field_correct / total_gold_orders) * 100, 2)
            if total_gold_orders else 0.0
        )

    return summary


def write_csv(results: List[Dict[str, Any]], output_path: str) -> None:
    fieldnames = [
        "id",
        "json_valid",
        "siparis_sayisi_score",
        "matched_order_count",
        "missing_order_count",
        "extra_order_count",
        "nereden_score",
        "nereye_score",
        "yuk_tipi_score",
        "arac_tipi_score",
        "kasa_tipi_score",
        "earned_score",
        "max_score",
        "accuracy",
        "notes"
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    parser = argparse.ArgumentParser(
        description="Gold JSON ile model cevabını karşılaştırır."
    )

    parser.add_argument(
        "--gold",
        required=True,
        help="Gold cevap dosyası yolu. Örn: gold.json"
    )

    parser.add_argument(
        "--pred",
        required=True,
        help="Model cevap dosyası yolu. Örn: qwen_cevabi.json"
    )

    parser.add_argument(
        "--out",
        default="score_results.csv",
        help="CSV skor çıktı dosyası"
    )

    parser.add_argument(
        "--summary",
        default="summary.json",
        help="Özet JSON çıktı dosyası"
    )

    args = parser.parse_args()

    gold_data = load_json_file(args.gold)
    pred_data = load_json_file(args.pred)

    gold_examples = unwrap_examples(gold_data)
    pred_examples = unwrap_examples(pred_data)

    pred_map = build_model_map(pred_examples)

    results = []

    for i, gold_example in enumerate(gold_examples):
        example_id = get_example_id(gold_example, i)
        gold_output = extract_gold_output(gold_example)

        if gold_output is None:
            results.append({
                "id": example_id,
                "json_valid": 0,
                "siparis_sayisi_score": 0,
                "matched_order_count": 0,
                "missing_order_count": 0,
                "extra_order_count": 0,
                "nereden_score": 0.0,
                "nereye_score": 0.0,
                "yuk_tipi_score": 0.0,
                "arac_tipi_score": 0.0,
                "kasa_tipi_score": 0.0,
                "earned_score": 0.0,
                "max_score": 0,
                "accuracy": 0.0,
                "notes": "Gold cevap bulunamadı"
            })
            continue

        pred_example = pred_map.get(example_id)

        result = evaluate_example(example_id, gold_output, pred_example)
        results.append(result)

    summary = summarize_results(results)

    write_csv(results, args.out)

    with open(args.summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("Değerlendirme tamamlandı.")
    print(f"CSV sonuç dosyası: {args.out}")
    print(f"Özet dosyası: {args.summary}")
    print()
    print("Genel Özet:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()