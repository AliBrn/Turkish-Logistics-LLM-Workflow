from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    harici_mesaj_id: str | None
    telefon: str | None
    gonderen_adi: str | None
    firma_adi: str | None
    chat_id: str | None
    chat_adi: str | None
    mesaj_metni: str
    mesaj_tarihi: datetime | None
    islem_durumu: str
    siparis_sayisi: int


class OrderOut(BaseModel):
    id: int
    ham_mesaj_id: int
    cozumleme_id: int | None
    siparis_no: int
    nereden: str | None
    nereye: str | None
    yuk_tipi: str | None
    arac_tipi: str | None
    kasa_tipi: str | None
    durum: str
    operasyon_durumu: str
    manuel_duzenlendi_mi: bool
    gonderen_adi: str | None = None
    firma_adi: str | None = None


class OrderUpdate(BaseModel):
    nereden: str | None = None
    nereye: str | None = None
    yuk_tipi: str | None = None
    arac_tipi: str | None = None
    kasa_tipi: str | None = None
    durum: str | None = None
    operasyon_durumu: str | None = None


class StatusUpdate(BaseModel):
    durum: str | None = None
    operasyon_durumu: str | None = None
    not_metni: str | None = None


class ValidationIssueOut(BaseModel):
    id: int
    ham_mesaj_id: int | None
    siparis_id: int | None
    cozumleme_id: int | None
    sorun_tipi: str
    alan_adi: str | None
    mevcut_deger: str | None
    onerilen_deger: str | None
    durum: str
    not_metni: str | None


class ValidationResolve(BaseModel):
    onerilen_deger: str | None = None
    not_metni: str | None = None


class ManualReviewOrder(BaseModel):
    id: int | None = None
    nereden: str | None = None
    nereye: str | None = None
    yuk_tipi: str | None = None
    arac_tipi: str | None = None
    kasa_tipi: str | None = None
    durum: str | None = None


class ManualReviewSave(BaseModel):
    orders: list[ManualReviewOrder]


class ExtractionOut(BaseModel):
    ham_mesaj_id: int
    cozumleme_id: int
    duzeltilmis_json: dict[str, Any]
    basarili_mi: bool
    hata_mesaji: str | None
    siparisler: list[OrderOut]
    sorunlar: list[ValidationIssueOut]
