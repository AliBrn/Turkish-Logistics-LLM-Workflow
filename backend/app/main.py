import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .model_client import ModelClientError, get_model_client, get_model_client_status
from .models import CozumlemeKaydi, DogrulamaSorunu, Gonderen, HamMesaj, JsonImportState, Siparis, SiparisDurumGecmisi
from .schemas import ExtractionOut, ManualReviewSave, OrderOut, OrderUpdate, StatusUpdate, ValidationIssueOut, ValidationResolve
from .validator import validate_extraction

app = FastAPI(title="WorkFlow Lojistik AI API")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_IMPORT_SOURCE = "mesajlar.json"
JSON_IMPORT_PATH = PROJECT_ROOT / JSON_IMPORT_SOURCE
JSON_IMPORT_BATCH_SIZE = 2
JSON_IMPORT_INTERVAL_SECONDS = 5 * 60

_import_lock = asyncio.Lock()
_import_worker_task: asyncio.Task | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.on_event("startup")
async def start_json_import_worker():
    global _import_worker_task
    if _import_worker_task is None or _import_worker_task.done():
        _import_worker_task = asyncio.create_task(_json_import_loop())


@app.on_event("shutdown")
async def stop_json_import_worker():
    global _import_worker_task
    if _import_worker_task and not _import_worker_task.done():
        _import_worker_task.cancel()
        try:
            await _import_worker_task
        except asyncio.CancelledError:
            pass
    _import_worker_task = None


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok", "database": "connected"}


@app.get("/api/model/status")
def model_status():
    return get_model_client_status()


@app.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total_messages = db.query(func.count(HamMesaj.id)).scalar() or 0
    processed = db.query(func.count(HamMesaj.id)).filter(HamMesaj.islem_durumu == "islendi").scalar() or 0
    waiting = db.query(func.count(HamMesaj.id)).filter(HamMesaj.islem_durumu == "bekliyor").scalar() or 0
    processing = db.query(func.count(HamMesaj.id)).filter(HamMesaj.islem_durumu == "isleniyor").scalar() or 0
    manual = db.query(func.count(HamMesaj.id)).filter(HamMesaj.islem_durumu == "manuel_kontrol").scalar() or 0
    error = db.query(func.count(HamMesaj.id)).filter(HamMesaj.islem_durumu == "hata").scalar() or 0
    total_orders = db.query(func.count(Siparis.id)).scalar() or 0
    open_issues = db.query(func.count(DogrulamaSorunu.id)).filter(DogrulamaSorunu.durum == "acik").scalar() or 0
    return {
        "totalMessages": total_messages,
        "processedMessages": processed,
        "pendingMessages": waiting + processing,
        "waitingMessages": waiting,
        "processingMessages": processing,
        "manualMessages": manual,
        "errorMessages": error,
        "totalOrders": total_orders,
        "openIssues": open_issues,
    }


@app.get("/api/messages")
def list_messages(db: Session = Depends(get_db)):
    messages = db.query(HamMesaj).order_by(HamMesaj.id).all()
    return [_message_out(message) for message in messages]


@app.get("/api/messages/{message_id}")
def get_message(message_id: int, db: Session = Depends(get_db)):
    message = db.get(HamMesaj, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Ham mesaj bulunamadı.")
    return _message_out(message)


@app.post("/api/messages/reset-manuel-kontrol")
def reset_manuel_kontrol(db: Session = Depends(get_db)):
    """Takılı 'manuel_kontrol' kayıtlarını 'bekliyor'a çevirir — kullanıcı tekrar AI çözümleme yapabilsin."""
    affected = (
        db.query(HamMesaj)
        .filter(HamMesaj.islem_durumu == "manuel_kontrol")
        .update({"islem_durumu": "bekliyor"}, synchronize_session=False)
    )
    db.commit()
    return {"status": "ok", "updated": affected}


@app.post("/api/messages/import-sample")
def import_sample(db: Session = Depends(get_db)):
    if db.query(HamMesaj).first():
        return {"status": "skipped", "message": "Veritabanında mesaj var; örnek veri tekrar eklenmedi."}

    sender = Gonderen(telefon="905425307960", gonderen_adi="Burak Özhan", firma_adi="KYR Taşımacılık")
    db.add(sender)
    db.flush()
    db.add(
        HamMesaj(
            harici_mesaj_id="sample-001",
            gonderen_id=sender.id,
            chat_id="sample-chat",
            chat_adi="Örnek Lojistik Grubu",
            mesaj_metni="Mersin -> Batman açık 1360 kasa içi makina",
            mesaj_tarihi=datetime.now(),
            islem_durumu="bekliyor",
        )
    )
    db.commit()
    return {"status": "ok", "message": "Örnek mesaj eklendi."}


@app.get("/api/import/status")
def import_status():
    return _get_import_status_sync()


@app.post("/api/import/tick")
async def import_tick():
    async with _import_lock:
        return await asyncio.to_thread(_import_next_messages_sync, True)


@app.post("/api/import/reset")
def import_reset():
    db = SessionLocal()
    try:
        state = _get_or_create_import_state(db)
        state.last_imported_index = -1
        state.updated_at = datetime.now()
        db.commit()
        return _get_import_status_sync()
    finally:
        db.close()


@app.post("/api/messages/{message_id}/extract", response_model=ExtractionOut)
def extract_message(message_id: int, db: Session = Depends(get_db)):
    return _extract_message_by_id(message_id, db)


def _extract_message_by_id(message_id: int, db: Session) -> dict:
    message = db.get(HamMesaj, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Ham mesaj bulunamadı.")

    # Zaten başarıyla çözümlendiyse AI'a gitme — DB'deki kaydı döndür
    if message.islem_durumu in {"islendi", "manuel_kontrol"}:
        existing = (
            db.query(CozumlemeKaydi)
            .filter(CozumlemeKaydi.ham_mesaj_id == message.id)
            .order_by(CozumlemeKaydi.id.desc())
            .first()
        )
        existing_orders = db.query(Siparis).filter(Siparis.ham_mesaj_id == message.id).all()
        existing_issues = (
            db.query(DogrulamaSorunu)
            .filter(DogrulamaSorunu.ham_mesaj_id == message.id, DogrulamaSorunu.durum == "acik")
            .all()
        )
        return {
            "ham_mesaj_id": message.id,
            "cozumleme_id": existing.id if existing else None,
            "duzeltilmis_json": existing.duzeltilmis_json if existing else {},
            "basarili_mi": existing.basarili_mi if existing else True,
            "hata_mesaji": "",
            "siparisler": [_order_out(o) for o in existing_orders],
            "sorunlar": [_issue_out(i) for i in existing_issues],
        }

    if message.islem_durumu == "isleniyor":
        raise HTTPException(status_code=409, detail="Bu mesaj icin AI cozumleme zaten calisiyor.")

    message.islem_durumu = "isleniyor"
    db.commit()
    db.refresh(message)

    try:
        model_payload = get_model_client().extract(message.mesaj_metni)
    except ModelClientError as exc:
        normalized_json = {"siparis_sayisi": 0, "siparisler": []}
        cozumleme = CozumlemeKaydi(
            ham_mesaj_id=message.id,
            ham_model_cevabi=getattr(exc, "raw_output", ""),
            duzeltilmis_json=normalized_json,
            basarili_mi=False,
            hata_mesaji=str(exc),
        )
        db.add(cozumleme)
        db.flush()

        db.query(DogrulamaSorunu).filter(DogrulamaSorunu.ham_mesaj_id == message.id).delete()
        issue = DogrulamaSorunu(
            ham_mesaj_id=message.id,
            siparis_id=None,
            cozumleme_id=cozumleme.id,
            sorun_tipi="model_hatasi",
            alan_adi=None,
            mevcut_deger="",
            onerilen_deger="",
            durum="acik",
            not_metni=str(exc),
        )
        db.add(issue)
        message.islem_durumu = "hata"
        db.commit()
        return {
            "ham_mesaj_id": message.id,
            "cozumleme_id": cozumleme.id,
            "duzeltilmis_json": normalized_json,
            "basarili_mi": False,
            "hata_mesaji": str(exc),
            "siparisler": [],
            "sorunlar": [_issue_out(issue)],
        }

    normalized_json, issues = validate_extraction(model_payload)
    cozumleme = CozumlemeKaydi(
        ham_mesaj_id=message.id,
        ham_model_cevabi=str(model_payload),
        duzeltilmis_json=normalized_json,
        basarili_mi=len(issues) == 0,
        hata_mesaji="" if not issues else "Validator manuel kontrol gerektiren alanlar buldu.",
    )
    db.add(cozumleme)
    db.flush()

    db.query(Siparis).filter(Siparis.ham_mesaj_id == message.id).delete()
    created_orders = []
    for index, order in enumerate(normalized_json["siparisler"], start=1):
        has_issue = any(issue.get("siparis_no") == index for issue in issues)
        siparis = Siparis(
            ham_mesaj_id=message.id,
            cozumleme_id=cozumleme.id,
            siparis_no=index,
            nereden=order.get("nereden"),
            nereye=order.get("nereye"),
            yuk_tipi=order.get("yuk_tipi"),
            arac_tipi=order.get("arac_tipi") or None,
            kasa_tipi=order.get("kasa_tipi") or None,
            durum="manuel_kontrol" if has_issue else "inceleniyor",
            operasyon_durumu="yeni",
        )
        db.add(siparis)
        db.flush()
        db.add(SiparisDurumGecmisi(
            siparis_id=siparis.id,
            eski_durum=None,
            yeni_durum=siparis.durum,
            not_metni="AI çözümlemeden oluştu.",
        ))
        created_orders.append(siparis)

    db.query(DogrulamaSorunu).filter(DogrulamaSorunu.ham_mesaj_id == message.id).delete()
    created_issues = []
    for issue in issues:
        order_index = max((issue.get("siparis_no", 1) or 1) - 1, 0)
        order = created_orders[order_index] if order_index < len(created_orders) else None
        row = DogrulamaSorunu(
            ham_mesaj_id=message.id,
            siparis_id=order.id if order else None,
            cozumleme_id=cozumleme.id,
            sorun_tipi=issue["sorun_tipi"],
            alan_adi=issue.get("alan_adi"),
            mevcut_deger=issue.get("mevcut_deger"),
            onerilen_deger=issue.get("onerilen_deger"),
            durum="acik",
            not_metni=issue.get("not_metni"),
        )
        db.add(row)
        created_issues.append(row)

    message.islem_durumu = "manuel_kontrol" if issues else "islendi"
    db.commit()
    return {
        "ham_mesaj_id": message.id,
        "cozumleme_id": cozumleme.id,
        "duzeltilmis_json": normalized_json,
        "basarili_mi": cozumleme.basarili_mi,
        "hata_mesaji": cozumleme.hata_mesaji,
        "siparisler": [_order_out(order) for order in created_orders],
        "sorunlar": [_issue_out(issue) for issue in created_issues],
    }


@app.get("/api/orders")
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Siparis).order_by(Siparis.id).all()
    return [_order_out(order) for order in orders]


@app.get("/api/resolutions")
def list_resolutions(db: Session = Depends(get_db)):
    records = db.query(CozumlemeKaydi).order_by(CozumlemeKaydi.id.desc()).all()
    return [_resolution_out(record) for record in records]


@app.get("/api/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Siparis, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı.")
    return _order_out(order)


@app.patch("/api/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: int, payload: OrderUpdate, db: Session = Depends(get_db)):
    order = db.get(Siparis, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    order.manuel_duzenlendi_mi = True
    db.commit()
    return _order_out(order)


@app.patch("/api/messages/{message_id}/manual-review")
def save_manual_review(message_id: int, payload: ManualReviewSave, db: Session = Depends(get_db)):
    message = db.get(HamMesaj, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Ham mesaj bulunamadı.")
    if not payload.orders:
        raise HTTPException(status_code=400, detail="En az bir sipariş gönderilmelidir.")

    latest_resolution = (
        db.query(CozumlemeKaydi)
        .filter(CozumlemeKaydi.ham_mesaj_id == message.id)
        .order_by(CozumlemeKaydi.id.desc())
        .first()
    )
    existing_orders = {order.id: order for order in db.query(Siparis).filter(Siparis.ham_mesaj_id == message.id).all()}
    kept_ids = set()
    saved_orders = []

    for index, draft in enumerate(payload.orders, start=1):
        order = existing_orders.get(draft.id) if draft.id else None
        if order is None:
            order = Siparis(
                ham_mesaj_id=message.id,
                cozumleme_id=latest_resolution.id if latest_resolution else None,
                siparis_no=index,
                operasyon_durumu="yeni",
            )
            db.add(order)
            db.flush()

        order.siparis_no = index
        order.nereden = (draft.nereden or "").strip()
        order.nereye = (draft.nereye or "").strip()
        order.yuk_tipi = (draft.yuk_tipi or "").strip()
        order.arac_tipi = (draft.arac_tipi or "").strip() or None
        order.kasa_tipi = (draft.kasa_tipi or "").strip() or None
        order.manuel_duzenlendi_mi = True
        order.durum = "inceleniyor" if _order_has_required_fields(order) else "manuel_kontrol"
        kept_ids.add(order.id)
        saved_orders.append(order)

    for order_id, order in existing_orders.items():
        if order_id not in kept_ids:
            db.delete(order)

    all_complete = bool(saved_orders) and all(_order_has_required_fields(order) for order in saved_orders)
    open_issues = (
        db.query(DogrulamaSorunu)
        .filter(DogrulamaSorunu.ham_mesaj_id == message.id, DogrulamaSorunu.durum == "acik")
        .all()
    )

    if all_complete:
        for issue in open_issues:
            issue.durum = "cozuldu"
            issue.not_metni = issue.not_metni or "Manuel kontrolde kaydedildi."
        message.islem_durumu = "islendi"
        for order in saved_orders:
            if order.durum == "manuel_kontrol":
                order.durum = "inceleniyor"
    else:
        message.islem_durumu = "manuel_kontrol"

    db.commit()
    refreshed_orders = db.query(Siparis).filter(Siparis.ham_mesaj_id == message.id).order_by(Siparis.siparis_no).all()
    refreshed_issues = db.query(DogrulamaSorunu).filter(DogrulamaSorunu.ham_mesaj_id == message.id).all()
    return {
        "message": _message_out(message),
        "siparisler": [_order_out(order) for order in refreshed_orders],
        "sorunlar": [_issue_out(issue) for issue in refreshed_issues],
        "completed": message.islem_durumu == "islendi",
    }


@app.patch("/api/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    order = db.get(Siparis, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı.")
    if payload.durum is None and payload.operasyon_durumu is None:
        raise HTTPException(status_code=400, detail="durum veya operasyon_durumu gönderilmelidir.")

    if payload.durum is not None:
        old_status = order.durum
        order.durum = payload.durum
        db.add(SiparisDurumGecmisi(
            siparis_id=order.id,
            eski_durum=old_status,
            yeni_durum=payload.durum,
            not_metni=payload.not_metni,
        ))

    if payload.operasyon_durumu is not None:
        old_operation_status = order.operasyon_durumu
        order.operasyon_durumu = payload.operasyon_durumu
        db.add(SiparisDurumGecmisi(
            siparis_id=order.id,
            eski_durum=old_operation_status,
            yeni_durum=payload.operasyon_durumu,
            not_metni=payload.not_metni or "Operasyon durumu güncellendi.",
        ))

    db.commit()
    return _order_out(order)


@app.get("/api/validation-issues")
def list_validation_issues(db: Session = Depends(get_db)):
    issues = db.query(DogrulamaSorunu).order_by(DogrulamaSorunu.id).all()
    return [_issue_out(issue) for issue in issues]


@app.patch("/api/validation-issues/{issue_id}/resolve", response_model=ValidationIssueOut)
def resolve_validation_issue(issue_id: int, payload: ValidationResolve, db: Session = Depends(get_db)):
    issue = db.get(DogrulamaSorunu, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Doğrulama sorunu bulunamadı.")
    issue.durum = "cozuldu"
    if payload.onerilen_deger is not None:
        issue.onerilen_deger = payload.onerilen_deger
        order = db.get(Siparis, issue.siparis_id) if issue.siparis_id else None
        if order and issue.alan_adi:
            setattr(order, issue.alan_adi, payload.onerilen_deger)
            order.manuel_duzenlendi_mi = True
    if payload.not_metni:
        issue.not_metni = payload.not_metni
    db.commit()
    return _issue_out(issue)


async def _json_import_loop():
    while True:
        await asyncio.sleep(JSON_IMPORT_INTERVAL_SECONDS)
        try:
            async with _import_lock:
                await asyncio.to_thread(_import_next_messages_sync, True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"JSON import loop error: {exc}")


def _load_json_messages() -> list[dict]:
    if not JSON_IMPORT_PATH.exists():
        return []
    with JSON_IMPORT_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    messages = payload.get("messages", [])
    return messages if isinstance(messages, list) else []


def _get_or_create_import_state(db: Session) -> JsonImportState:
    state = db.query(JsonImportState).filter(JsonImportState.source_name == JSON_IMPORT_SOURCE).first()
    if state:
        return state
    state = JsonImportState(source_name=JSON_IMPORT_SOURCE, last_imported_index=-1, updated_at=datetime.now())
    db.add(state)
    db.flush()
    return state


def _get_import_status_sync() -> dict:
    messages = _load_json_messages()
    db = SessionLocal()
    try:
        state = db.query(JsonImportState).filter(JsonImportState.source_name == JSON_IMPORT_SOURCE).first()
        last_index = state.last_imported_index if state else -1
        next_index = last_index + 1 if last_index + 1 < len(messages) else None
        return {
            "source_name": JSON_IMPORT_SOURCE,
            "source_path": str(JSON_IMPORT_PATH),
            "total_records": len(messages),
            "last_imported_index": last_index,
            "next_index": next_index,
            "batch_size": JSON_IMPORT_BATCH_SIZE,
            "interval_seconds": JSON_IMPORT_INTERVAL_SECONDS,
            "updated_at": state.updated_at if state else None,
            "source_exists": JSON_IMPORT_PATH.exists(),
        }
    finally:
        db.close()


def _import_next_messages_sync(run_ai: bool = True) -> dict:
    messages = _load_json_messages()
    db = SessionLocal()
    imported_ids: list[int] = []
    skipped_duplicates: list[str] = []
    processed_results: list[dict] = []
    start_index = None
    end_index = None

    try:
        state = _get_or_create_import_state(db)
        index = state.last_imported_index + 1
        start_index = index

        while index < len(messages) and len(imported_ids) < JSON_IMPORT_BATCH_SIZE:
            record = messages[index]
            external_id = str(record.get("id") or "").strip()
            if not external_id:
                state.last_imported_index = index
                index += 1
                continue

            existing = db.query(HamMesaj).filter(HamMesaj.harici_mesaj_id == external_id).first()
            if existing:
                skipped_duplicates.append(external_id)
                state.last_imported_index = index
                index += 1
                continue

            message = _create_message_from_json_record(db, record)
            imported_ids.append(message.id)
            state.last_imported_index = index
            index += 1

        state.updated_at = datetime.now()
        db.commit()
        end_index = state.last_imported_index

        if run_ai:
            for message_id in imported_ids:
                try:
                    processed_results.append(_extract_message_by_id(message_id, db))
                except Exception as exc:
                    processed_results.append({"ham_mesaj_id": message_id, "error": str(exc)})

        return {
            "status": "ok",
            "source_name": JSON_IMPORT_SOURCE,
            "start_index": start_index,
            "end_index": end_index,
            "imported_count": len(imported_ids),
            "imported_message_ids": imported_ids,
            "skipped_duplicates": skipped_duplicates,
            "ai_processed_count": len(processed_results),
            "ai_results": processed_results,
            "remaining_records": max(len(messages) - (end_index + 1 if end_index is not None else 0), 0),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _create_message_from_json_record(db: Session, record: dict) -> HamMesaj:
    phone = str(record.get("from") or "").strip() or None
    sender_name = str(record.get("sender_name") or "").strip() or None
    sender = None
    if phone:
        sender = db.query(Gonderen).filter(Gonderen.telefon == phone).first()
    if sender is None:
        sender = Gonderen(telefon=phone, gonderen_adi=sender_name, firma_adi=sender_name)
        db.add(sender)
        db.flush()
    else:
        if sender_name and not sender.gonderen_adi:
            sender.gonderen_adi = sender_name
        if sender_name and not sender.firma_adi:
            sender.firma_adi = sender_name

    message = HamMesaj(
        harici_mesaj_id=str(record.get("id") or "").strip(),
        gonderen_id=sender.id if sender else None,
        chat_id=str(record.get("chat_id") or "").strip() or None,
        chat_adi=str(record.get("chat_name") or "").strip() or None,
        mesaj_metni=str(record.get("body") or ""),
        mesaj_tarihi=_parse_json_message_datetime(record),
        islem_durumu="bekliyor",
    )
    db.add(message)
    db.flush()
    return message


def _parse_json_message_datetime(record: dict) -> datetime | None:
    readable = record.get("timestamp_readable")
    if readable:
        try:
            return datetime.strptime(str(readable), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    timestamp = record.get("timestamp")
    if timestamp is not None:
        try:
            return datetime.fromtimestamp(float(timestamp))
        except (TypeError, ValueError, OSError):
            pass
    return None


def _order_has_required_fields(order: Siparis) -> bool:
    return all([
        bool((order.nereden or "").strip()),
        bool((order.nereye or "").strip()),
        bool((order.yuk_tipi or "").strip()),
        bool((order.arac_tipi or "").strip()),
        bool((order.kasa_tipi or "").strip()),
    ])


def _message_out(message: HamMesaj) -> dict:
    return {
        "id": message.id,
        "harici_mesaj_id": message.harici_mesaj_id,
        "telefon": message.gonderen.telefon if message.gonderen else None,
        "gonderen_adi": message.gonderen.gonderen_adi if message.gonderen else None,
        "firma_adi": message.gonderen.firma_adi if message.gonderen else None,
        "chat_id": message.chat_id,
        "chat_adi": message.chat_adi,
        "mesaj_metni": message.mesaj_metni,
        "mesaj_tarihi": message.mesaj_tarihi,
        "islem_durumu": message.islem_durumu,
        "siparis_sayisi": len(message.siparisler),
    }


def _order_out(order: Siparis) -> dict:
    message = order.ham_mesaj
    return {
        "id": order.id,
        "ham_mesaj_id": order.ham_mesaj_id,
        "cozumleme_id": order.cozumleme_id,
        "siparis_no": order.siparis_no,
        "nereden": order.nereden,
        "nereye": order.nereye,
        "yuk_tipi": order.yuk_tipi,
        "arac_tipi": order.arac_tipi,
        "kasa_tipi": order.kasa_tipi,
        "durum": order.durum,
        "operasyon_durumu": order.operasyon_durumu,
        "manuel_duzenlendi_mi": order.manuel_duzenlendi_mi,
        "gonderen_adi": message.gonderen.gonderen_adi if message and message.gonderen else None,
        "firma_adi": message.gonderen.firma_adi if message and message.gonderen else None,
    }


def _resolution_out(record: CozumlemeKaydi) -> dict:
    return {
        "id": record.id,
        "ham_mesaj_id": record.ham_mesaj_id,
        "ham_model_cevabi": record.ham_model_cevabi,
        "duzeltilmis_json": record.duzeltilmis_json,
        "basarili_mi": record.basarili_mi,
        "hata_mesaji": record.hata_mesaji,
    }


def _issue_out(issue: DogrulamaSorunu) -> dict:
    return {
        "id": issue.id,
        "ham_mesaj_id": issue.ham_mesaj_id,
        "siparis_id": issue.siparis_id,
        "cozumleme_id": issue.cozumleme_id,
        "sorun_tipi": issue.sorun_tipi,
        "alan_adi": issue.alan_adi,
        "mevcut_deger": issue.mevcut_deger,
        "onerilen_deger": issue.onerilen_deger,
        "durum": issue.durum,
        "not_metni": issue.not_metni,
    }
