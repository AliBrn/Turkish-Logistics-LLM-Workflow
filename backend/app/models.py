from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Gonderen(Base):
    __tablename__ = "gonderenler"

    id: Mapped[int] = mapped_column(primary_key=True)
    telefon: Mapped[str | None] = mapped_column(String(30), unique=True)
    gonderen_adi: Mapped[str | None] = mapped_column(String(150))
    firma_adi: Mapped[str | None] = mapped_column(String(150))

    mesajlar: Mapped[list["HamMesaj"]] = relationship(back_populates="gonderen")


class HamMesaj(Base):
    __tablename__ = "ham_mesajlar"

    id: Mapped[int] = mapped_column(primary_key=True)
    harici_mesaj_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    gonderen_id: Mapped[int | None] = mapped_column(ForeignKey("gonderenler.id"))
    chat_id: Mapped[str | None] = mapped_column(String(120))
    chat_adi: Mapped[str | None] = mapped_column(String(200))
    mesaj_metni: Mapped[str] = mapped_column(Text)
    mesaj_tarihi: Mapped[DateTime | None] = mapped_column(DateTime)
    islem_durumu: Mapped[str] = mapped_column(String(30), default="bekliyor")

    gonderen: Mapped[Gonderen | None] = relationship(back_populates="mesajlar")
    cozumlemeler: Mapped[list["CozumlemeKaydi"]] = relationship(back_populates="ham_mesaj")
    siparisler: Mapped[list["Siparis"]] = relationship(back_populates="ham_mesaj")


class CozumlemeKaydi(Base):
    __tablename__ = "cozumleme_kayitlari"

    id: Mapped[int] = mapped_column(primary_key=True)
    ham_mesaj_id: Mapped[int] = mapped_column(ForeignKey("ham_mesajlar.id", ondelete="CASCADE"))
    ham_model_cevabi: Mapped[str | None] = mapped_column(Text)
    duzeltilmis_json: Mapped[dict | None] = mapped_column(JSONB)
    basarili_mi: Mapped[bool] = mapped_column(Boolean, default=False)
    hata_mesaji: Mapped[str | None] = mapped_column(Text)

    ham_mesaj: Mapped[HamMesaj] = relationship(back_populates="cozumlemeler")
    siparisler: Mapped[list["Siparis"]] = relationship(back_populates="cozumleme")


class Siparis(Base):
    __tablename__ = "siparisler"

    id: Mapped[int] = mapped_column(primary_key=True)
    ham_mesaj_id: Mapped[int] = mapped_column(ForeignKey("ham_mesajlar.id", ondelete="CASCADE"))
    cozumleme_id: Mapped[int | None] = mapped_column(ForeignKey("cozumleme_kayitlari.id", ondelete="SET NULL"))
    siparis_no: Mapped[int] = mapped_column(Integer)
    nereden: Mapped[str | None] = mapped_column(String(200))
    nereye: Mapped[str | None] = mapped_column(String(200))
    yuk_tipi: Mapped[str | None] = mapped_column(String(50))
    arac_tipi: Mapped[str | None] = mapped_column(String(80))
    kasa_tipi: Mapped[str | None] = mapped_column(String(120))
    durum: Mapped[str] = mapped_column(String(40), default="inceleniyor")
    operasyon_durumu: Mapped[str] = mapped_column(String(40), default="yeni")
    manuel_duzenlendi_mi: Mapped[bool] = mapped_column(Boolean, default=False)

    ham_mesaj: Mapped[HamMesaj] = relationship(back_populates="siparisler")
    cozumleme: Mapped[CozumlemeKaydi | None] = relationship(back_populates="siparisler")
    durum_gecmisi: Mapped[list["SiparisDurumGecmisi"]] = relationship(back_populates="siparis")


class SiparisDurumGecmisi(Base):
    __tablename__ = "siparis_durum_gecmisi"

    id: Mapped[int] = mapped_column(primary_key=True)
    siparis_id: Mapped[int] = mapped_column(ForeignKey("siparisler.id", ondelete="CASCADE"))
    eski_durum: Mapped[str | None] = mapped_column(String(40))
    yeni_durum: Mapped[str] = mapped_column(String(40))
    not_metni: Mapped[str | None] = mapped_column(Text)
    degisim_tarihi: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    siparis: Mapped[Siparis] = relationship(back_populates="durum_gecmisi")


class DogrulamaSorunu(Base):
    __tablename__ = "dogrulama_sorunlari"

    id: Mapped[int] = mapped_column(primary_key=True)
    ham_mesaj_id: Mapped[int | None] = mapped_column(ForeignKey("ham_mesajlar.id", ondelete="CASCADE"))
    siparis_id: Mapped[int | None] = mapped_column(ForeignKey("siparisler.id", ondelete="CASCADE"))
    cozumleme_id: Mapped[int | None] = mapped_column(ForeignKey("cozumleme_kayitlari.id", ondelete="SET NULL"))
    sorun_tipi: Mapped[str] = mapped_column(String(80))
    alan_adi: Mapped[str | None] = mapped_column(String(80))
    mevcut_deger: Mapped[str | None] = mapped_column(Text)
    onerilen_deger: Mapped[str | None] = mapped_column(Text)
    durum: Mapped[str] = mapped_column(String(30), default="acik")
    not_metni: Mapped[str | None] = mapped_column(Text)


class JsonImportState(Base):
    __tablename__ = "json_import_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(120), unique=True)
    last_imported_index: Mapped[int] = mapped_column(Integer, default=-1)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
