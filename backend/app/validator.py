ALLOWED_YUK_TIPI = {"KOMPLE", "PARÇA", "PALETLİ", "DÖKME", "YÜKÜSTÜ"}
ALLOWED_ARAC_TIPI = {
    "1360",
    "860",
    "10 TEKER",
    "8 TEKER",
    "6 TEKER",
    "4 TEKER",
    "40 AYAK",
    "KAMYONET",
    "KIRKAYAK",
    "PIKUP",
}
ALLOWED_KASA_PARTS = {"AÇIK", "KAPALI", "DAMPERLİ", "FRİGO", "LOWBED", "MEGA"}


def validate_extraction(payload: dict) -> tuple[dict, list[dict]]:
    orders = payload.get("siparisler") if isinstance(payload, dict) else None
    if not isinstance(orders, list):
        return {"siparis_sayisi": 0, "siparisler": []}, [
            {
                "sorun_tipi": "json_hatasi",
                "alan_adi": "siparisler",
                "mevcut_deger": "",
                "onerilen_deger": "",
                "not_metni": "Model çıktısı siparişler listesi içermiyor.",
            }
        ]

    normalized_orders = []
    issues = []
    for index, order in enumerate(orders, start=1):
        if not isinstance(order, dict):
            issues.append(
                {
                    "siparis_no": index,
                    "sorun_tipi": "json_hatasi",
                    "alan_adi": "siparisler",
                    "mevcut_deger": str(order),
                    "onerilen_deger": "",
                    "not_metni": "Sipariş elemanı JSON obje değil.",
                }
            )
            continue

        normalized = {
            "nereden": (order.get("nereden") or "").strip(),
            "nereye": (order.get("nereye") or "").strip(),
            "yuk_tipi": (order.get("yuk_tipi") or "").strip().upper(),
            "arac_tipi": (order.get("arac_tipi") or "").strip().upper(),
            "kasa_tipi": (order.get("kasa_tipi") or "").strip().upper(),
        }
        normalized_orders.append(normalized)

        for field in ["nereden", "nereye", "yuk_tipi", "arac_tipi", "kasa_tipi"]:
            if not normalized[field]:
                issues.append(
                    {
                        "siparis_no": index,
                        "sorun_tipi": "eksik_alan",
                        "alan_adi": field,
                        "mevcut_deger": "",
                        "onerilen_deger": "",
                        "not_metni": f"{field} alanı boş geldi.",
                    }
                )

        if normalized["yuk_tipi"] and normalized["yuk_tipi"] not in ALLOWED_YUK_TIPI:
            issues.append(_standard_issue(index, "yuk_tipi", normalized["yuk_tipi"]))

        if normalized["arac_tipi"] and normalized["arac_tipi"] not in ALLOWED_ARAC_TIPI:
            issues.append(_standard_issue(index, "arac_tipi", normalized["arac_tipi"]))

        if normalized["kasa_tipi"]:
            parts = {part.strip() for part in normalized["kasa_tipi"].split("+")}
            if not parts.issubset(ALLOWED_KASA_PARTS):
                issues.append(_standard_issue(index, "kasa_tipi", normalized["kasa_tipi"]))

    normalized_payload = {
        "siparis_sayisi": len(normalized_orders),
        "siparisler": normalized_orders,
    }
    return normalized_payload, issues


def _standard_issue(index: int, field: str, value: str) -> dict:
    return {
        "siparis_no": index,
        "sorun_tipi": "standart_disi_deger",
        "alan_adi": field,
        "mevcut_deger": value,
        "onerilen_deger": "",
        "not_metni": f"{field} standart değer listesinde bulunamadı.",
    }
