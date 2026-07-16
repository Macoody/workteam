"""
数字员工项目：手机资产、客户记录和服务跟进。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.core.timezone import business_now, to_business_time
from app.models.models import (
    DigitalCustomer,
    DigitalPhone,
    DigitalServiceItem,
    DigitalServiceRecord,
    User,
)
from app.routers.auth import (
    build_user_response,
    get_current_user,
    require_admin,
    _update_last_active_time,
)
from app.schemas.schemas import (
    DigitalCustomerCreate,
    DigitalCustomerResponse,
    DigitalCustomerSummary,
    DigitalCustomerUpdate,
    DigitalOverviewResponse,
    DigitalPhoneCreate,
    DigitalPhoneResponse,
    DigitalPhoneSummary,
    DigitalPhoneUpdate,
    DigitalServiceItemCreate,
    DigitalServiceItemResponse,
    DigitalServiceItemUpdate,
    DigitalServiceRecordResponse,
    DigitalServiceRecordUpdate,
)

router = APIRouter()

DEFAULT_SERVICE_ITEMS = ["人设录入", "数字人录入", "声音克隆"]
PHONE_CONDITIONS = {"new", "used"}
PHONE_STATUSES = {"in_stock", "assigned", "sold"}


def _clean_optional(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _clean_required(value: str | None, field_name: str):
    value = _clean_optional(value)
    if not value:
        raise HTTPException(status_code=400, detail=f"{field_name}不能为空")
    return value


def _validate_choice(value: str | None, allowed: set[str], field_name: str):
    value = _clean_required(value, field_name)
    if value not in allowed:
        raise HTTPException(status_code=400, detail=f"{field_name}无效")
    return value


def _validate_holder(db: Session, holder_id: int | None):
    if holder_id is None:
        return None
    user = db.query(User).filter(User.id == holder_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=404, detail="归属成员不存在")
    return user


def _validate_customer(db: Session, customer_id: int | None):
    if customer_id is None:
        return None
    customer = db.query(DigitalCustomer).filter(DigitalCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    return customer


def ensure_default_service_items(db: Session) -> bool:
    existing_names = {
        item.name
        for item in db.query(DigitalServiceItem)
        .filter(DigitalServiceItem.name.in_(DEFAULT_SERVICE_ITEMS))
        .all()
    }
    changed = False
    for index, name in enumerate(DEFAULT_SERVICE_ITEMS):
        if name in existing_names:
            continue
        db.add(
            DigitalServiceItem(
                name=name,
                description="",
                is_active=True,
                sort_order=(index + 1) * 10,
            )
        )
        changed = True
    if changed:
        db.flush()
    return changed


def ensure_customer_service_records(db: Session, customer_id: int) -> bool:
    active_items = db.query(DigitalServiceItem).filter(
        DigitalServiceItem.is_active.is_(True)
    ).all()
    existing_ids = {
        item_id
        for (item_id,) in db.query(DigitalServiceRecord.service_item_id)
        .filter(DigitalServiceRecord.customer_id == customer_id)
        .all()
    }
    changed = False
    for item in active_items:
        if item.id in existing_ids:
            continue
        db.add(
            DigitalServiceRecord(
                customer_id=customer_id,
                service_item_id=item.id,
                is_done=False,
            )
        )
        changed = True
    if changed:
        db.flush()
    return changed


def _service_item_query(db: Session):
    return db.query(DigitalServiceItem).order_by(
        DigitalServiceItem.sort_order.asc(),
        DigitalServiceItem.id.asc(),
    )


def _phone_query(db: Session):
    return db.query(DigitalPhone).options(
        joinedload(DigitalPhone.holder),
        joinedload(DigitalPhone.customer),
        joinedload(DigitalPhone.creator),
    )


def _customer_query(db: Session):
    return db.query(DigitalCustomer).options(
        joinedload(DigitalCustomer.creator),
        selectinload(DigitalCustomer.phones),
        selectinload(DigitalCustomer.service_records).joinedload(DigitalServiceRecord.service_item),
        selectinload(DigitalCustomer.service_records).joinedload(DigitalServiceRecord.updated_user),
    )


def build_service_item_response(item: DigitalServiceItem):
    response = DigitalServiceItemResponse.model_validate(item)
    response.created_at = to_business_time(item.created_at)
    response.updated_at = to_business_time(item.updated_at)
    return response


def build_service_record_response(record: DigitalServiceRecord):
    response = DigitalServiceRecordResponse.model_validate(record)
    response.service_item = (
        build_service_item_response(record.service_item)
        if record.service_item
        else None
    )
    response.updated_user = (
        build_user_response(record.updated_user)
        if record.updated_user
        else None
    )
    response.completed_at = to_business_time(record.completed_at)
    response.created_at = to_business_time(record.created_at)
    response.updated_at = to_business_time(record.updated_at)
    return response


def build_phone_summary(phone: DigitalPhone):
    return DigitalPhoneSummary(
        id=phone.id,
        model=phone.model,
        memory=phone.memory,
        serial_number=phone.serial_number,
        activation_code=phone.activation_code,
        status=phone.status,
        bound_phone=phone.bound_phone,
    )


def build_customer_summary(customer: DigitalCustomer):
    return DigitalCustomerSummary(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        device_number=customer.device_number,
    )


def build_phone_response(phone: DigitalPhone):
    response = DigitalPhoneResponse.model_validate(phone)
    response.holder = build_user_response(phone.holder) if phone.holder else None
    response.customer = build_customer_summary(phone.customer) if phone.customer else None
    response.creator = build_user_response(phone.creator) if phone.creator else None
    response.created_at = to_business_time(phone.created_at)
    response.updated_at = to_business_time(phone.updated_at)
    return response


def build_customer_response(customer: DigitalCustomer):
    records = [
        record
        for record in customer.service_records or []
        if not record.service_item or record.service_item.is_active
    ]
    records = sorted(
        records,
        key=lambda record: (
            record.service_item.sort_order if record.service_item else 0,
            record.service_item_id,
        ),
    )
    response = DigitalCustomerResponse.model_validate(customer)
    response.creator = build_user_response(customer.creator) if customer.creator else None
    response.phones = [build_phone_summary(phone) for phone in customer.phones or []]
    response.service_records = [build_service_record_response(record) for record in records]
    response.service_start_at = to_business_time(customer.service_start_at)
    response.service_end_at = to_business_time(customer.service_end_at)
    response.created_at = to_business_time(customer.created_at)
    response.updated_at = to_business_time(customer.updated_at)
    return response


def _attach_customer_phones(db: Session, customer: DigitalCustomer, phone_ids: list[int] | None):
    if phone_ids is None:
        return
    selected_ids = {int(phone_id) for phone_id in phone_ids if phone_id}

    current_phones = db.query(DigitalPhone).filter(DigitalPhone.customer_id == customer.id).all()
    for phone in current_phones:
        if phone.id in selected_ids:
            continue
        phone.customer_id = None
        if phone.status == "sold":
            phone.status = "assigned" if phone.holder_id else "in_stock"
        phone.updated_at = business_now()

    if not selected_ids:
        return

    phones = db.query(DigitalPhone).filter(DigitalPhone.id.in_(selected_ids)).all()
    if len(phones) != len(selected_ids):
        raise HTTPException(status_code=404, detail="关联手机不存在")
    for phone in phones:
        if phone.customer_id and phone.customer_id != customer.id:
            raise HTTPException(status_code=400, detail=f"手机 {phone.model} 已关联其他客户")
        phone.customer_id = customer.id
        if phone.status == "in_stock":
            phone.status = "sold"
        phone.updated_at = business_now()


@router.get("/overview", response_model=DigitalOverviewResponse)
def get_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if ensure_default_service_items(db):
        db.commit()
    return DigitalOverviewResponse(
        total_phones=db.query(DigitalPhone).count(),
        in_stock_phones=db.query(DigitalPhone).filter(DigitalPhone.status == "in_stock").count(),
        assigned_phones=db.query(DigitalPhone).filter(DigitalPhone.status == "assigned").count(),
        sold_phones=db.query(DigitalPhone).filter(DigitalPhone.status == "sold").count(),
        customers=db.query(DigitalCustomer).count(),
        active_service_items=db.query(DigitalServiceItem)
        .filter(DigitalServiceItem.is_active.is_(True))
        .count(),
        unfinished_service_records=db.query(DigitalServiceRecord)
        .filter(DigitalServiceRecord.is_done.is_(False))
        .count(),
    )


@router.get("/phones", response_model=list[DigitalPhoneResponse])
def list_phones(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    phones = _phone_query(db).order_by(
        func.coalesce(DigitalPhone.updated_at, DigitalPhone.created_at).desc(),
        DigitalPhone.id.desc(),
    ).all()
    return [build_phone_response(phone) for phone in phones]


@router.post("/phones", response_model=DigitalPhoneResponse)
def create_phone(data: DigitalPhoneCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    model = _clean_required(data.model, "手机型号")
    memory = _clean_required(data.memory, "内存")
    serial_number = _clean_optional(data.serial_number)
    if serial_number and db.query(DigitalPhone).filter(DigitalPhone.serial_number == serial_number).first():
        raise HTTPException(status_code=400, detail="序列号已存在")
    _validate_holder(db, data.holder_id)
    _validate_customer(db, data.customer_id)

    status = _validate_choice(data.status, PHONE_STATUSES, "手机状态")
    if data.customer_id and status == "in_stock":
        status = "sold"

    phone = DigitalPhone(
        model=model,
        memory=memory,
        serial_number=serial_number,
        activation_code=_clean_optional(data.activation_code),
        condition=_validate_choice(data.condition, PHONE_CONDITIONS, "新旧状态"),
        color=_clean_optional(data.color),
        status=status,
        holder_id=data.holder_id,
        customer_id=data.customer_id,
        bound_phone=_clean_optional(data.bound_phone),
        douyin_account=_clean_optional(data.douyin_account),
        xiaohongshu_account=_clean_optional(data.xiaohongshu_account),
        wechat_account=_clean_optional(data.wechat_account),
        kuaishou_account=_clean_optional(data.kuaishou_account),
        notes=_clean_optional(data.notes),
        created_by=current_user.id,
    )
    db.add(phone)
    db.commit()
    _update_last_active_time(db, current_user)
    db.refresh(phone)
    return build_phone_response(phone)


@router.put("/phones/{phone_id}", response_model=DigitalPhoneResponse)
def update_phone(phone_id: int, data: DigitalPhoneUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    phone = _phone_query(db).filter(DigitalPhone.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="手机不存在")

    updates = data.model_dump(exclude_unset=True)
    if "model" in updates:
        phone.model = _clean_required(updates["model"], "手机型号")
    if "memory" in updates:
        phone.memory = _clean_required(updates["memory"], "内存")
    if "serial_number" in updates:
        serial_number = _clean_optional(updates["serial_number"])
        exists = db.query(DigitalPhone).filter(
            DigitalPhone.serial_number == serial_number,
            DigitalPhone.id != phone.id,
        ).first() if serial_number else None
        if exists:
            raise HTTPException(status_code=400, detail="序列号已存在")
        phone.serial_number = serial_number
    if "condition" in updates:
        phone.condition = _validate_choice(updates["condition"], PHONE_CONDITIONS, "新旧状态")
    if "status" in updates:
        phone.status = _validate_choice(updates["status"], PHONE_STATUSES, "手机状态")
    if "holder_id" in updates:
        _validate_holder(db, updates["holder_id"])
        phone.holder_id = updates["holder_id"]
    if "customer_id" in updates:
        _validate_customer(db, updates["customer_id"])
        phone.customer_id = updates["customer_id"]
        if phone.customer_id and phone.status == "in_stock":
            phone.status = "sold"

    for field in [
        "color",
        "activation_code",
        "bound_phone",
        "douyin_account",
        "xiaohongshu_account",
        "wechat_account",
        "kuaishou_account",
        "notes",
    ]:
        if field in updates:
            setattr(phone, field, _clean_optional(updates[field]))

    phone.updated_at = business_now()
    db.commit()
    _update_last_active_time(db, current_user)
    db.refresh(phone)
    return build_phone_response(phone)


@router.delete("/phones/{phone_id}")
def delete_phone(phone_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    phone = db.query(DigitalPhone).filter(DigitalPhone.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="手机不存在")
    db.delete(phone)
    db.commit()
    return {"ok": True}


@router.get("/customers", response_model=list[DigitalCustomerResponse])
def list_customers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    changed = ensure_default_service_items(db)
    customer_ids = [customer_id for (customer_id,) in db.query(DigitalCustomer.id).all()]
    for customer_id in customer_ids:
        changed = ensure_customer_service_records(db, customer_id) or changed
    if changed:
        db.commit()

    customers = _customer_query(db).order_by(
        func.coalesce(DigitalCustomer.updated_at, DigitalCustomer.created_at).desc(),
        DigitalCustomer.id.desc(),
    ).all()
    return [build_customer_response(customer) for customer in customers]


@router.post("/customers", response_model=DigitalCustomerResponse)
def create_customer(data: DigitalCustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    name = _clean_required(data.name, "客户名称")
    start_at = to_business_time(data.service_start_at)
    end_at = to_business_time(data.service_end_at)
    if start_at and end_at and end_at < start_at:
        raise HTTPException(status_code=400, detail="服务结束时间不能早于开始时间")

    ensure_default_service_items(db)
    customer = DigitalCustomer(
        name=name,
        phone=_clean_optional(data.phone),
        wechat=_clean_optional(data.wechat),
        device_number=_clean_optional(data.device_number),
        source=_clean_optional(data.source),
        payment_amount=_clean_optional(data.payment_amount),
        payment_method=_clean_optional(data.payment_method),
        payment_status=_clean_optional(data.payment_status) or "unpaid",
        payment_note=_clean_optional(data.payment_note),
        service_start_at=start_at,
        service_end_at=end_at,
        notes=_clean_optional(data.notes),
        created_by=current_user.id,
    )
    db.add(customer)
    db.flush()
    _attach_customer_phones(db, customer, data.phone_ids)
    ensure_customer_service_records(db, customer.id)
    db.commit()
    _update_last_active_time(db, current_user)
    customer = _customer_query(db).filter(DigitalCustomer.id == customer.id).first()
    return build_customer_response(customer)


@router.get("/customers/{customer_id}", response_model=DigitalCustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exists = db.query(DigitalCustomer.id).filter(DigitalCustomer.id == customer_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="客户不存在")
    changed = ensure_default_service_items(db)
    changed = ensure_customer_service_records(db, customer_id) or changed
    if changed:
        db.commit()
    customer = _customer_query(db).filter(DigitalCustomer.id == customer_id).first()
    return build_customer_response(customer)


@router.put("/customers/{customer_id}", response_model=DigitalCustomerResponse)
def update_customer(customer_id: int, data: DigitalCustomerUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = db.query(DigitalCustomer).filter(DigitalCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    updates = data.model_dump(exclude_unset=True)
    if "name" in updates:
        customer.name = _clean_required(updates["name"], "客户名称")
    for field in [
        "phone",
        "wechat",
        "device_number",
        "source",
        "payment_amount",
        "payment_method",
        "payment_status",
        "payment_note",
        "notes",
    ]:
        if field in updates:
            value = _clean_optional(updates[field])
            if field == "payment_status" and not value:
                value = "unpaid"
            setattr(customer, field, value)
    if "service_start_at" in updates:
        customer.service_start_at = to_business_time(updates["service_start_at"])
    if "service_end_at" in updates:
        customer.service_end_at = to_business_time(updates["service_end_at"])
    if customer.service_start_at and customer.service_end_at and customer.service_end_at < customer.service_start_at:
        raise HTTPException(status_code=400, detail="服务结束时间不能早于开始时间")
    if "phone_ids" in updates:
        _attach_customer_phones(db, customer, updates["phone_ids"])

    customer.updated_at = business_now()
    db.commit()
    _update_last_active_time(db, current_user)
    customer = _customer_query(db).filter(DigitalCustomer.id == customer_id).first()
    return build_customer_response(customer)


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    customer = db.query(DigitalCustomer).filter(DigitalCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    for phone in db.query(DigitalPhone).filter(DigitalPhone.customer_id == customer.id).all():
        phone.customer_id = None
        if phone.status == "sold":
            phone.status = "assigned" if phone.holder_id else "in_stock"
        phone.updated_at = business_now()
    db.delete(customer)
    db.commit()
    return {"ok": True}


@router.get("/service-items", response_model=list[DigitalServiceItemResponse])
def list_service_items(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if ensure_default_service_items(db):
        db.commit()
    items = _service_item_query(db).all()
    return [build_service_item_response(item) for item in items]


@router.post("/service-items", response_model=DigitalServiceItemResponse)
def create_service_item(data: DigitalServiceItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    name = _clean_required(data.name, "服务内容")
    exists = db.query(DigitalServiceItem).filter(DigitalServiceItem.name == name).first()
    if exists:
        raise HTTPException(status_code=400, detail="服务内容已存在")
    max_order = db.query(func.max(DigitalServiceItem.sort_order)).scalar() or 0
    item = DigitalServiceItem(
        name=name,
        description=_clean_optional(data.description),
        is_active=bool(data.is_active),
        sort_order=data.sort_order if data.sort_order is not None else max_order + 10,
    )
    db.add(item)
    db.flush()
    if item.is_active:
        for customer_id, in db.query(DigitalCustomer.id).all():
            ensure_customer_service_records(db, customer_id)
    db.commit()
    _update_last_active_time(db, current_user)
    db.refresh(item)
    return build_service_item_response(item)


@router.put("/service-items/{item_id}", response_model=DigitalServiceItemResponse)
def update_service_item(item_id: int, data: DigitalServiceItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(DigitalServiceItem).filter(DigitalServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="服务内容不存在")
    updates = data.model_dump(exclude_unset=True)
    if "name" in updates:
        name = _clean_required(updates["name"], "服务内容")
        exists = db.query(DigitalServiceItem).filter(
            DigitalServiceItem.name == name,
            DigitalServiceItem.id != item.id,
        ).first()
        if exists:
            raise HTTPException(status_code=400, detail="服务内容已存在")
        item.name = name
    if "description" in updates:
        item.description = _clean_optional(updates["description"])
    if "is_active" in updates:
        item.is_active = bool(updates["is_active"])
    if "sort_order" in updates:
        item.sort_order = updates["sort_order"] or 0
    item.updated_at = business_now()
    db.flush()
    if item.is_active:
        for customer_id, in db.query(DigitalCustomer.id).all():
            ensure_customer_service_records(db, customer_id)
    db.commit()
    _update_last_active_time(db, current_user)
    db.refresh(item)
    return build_service_item_response(item)


@router.put("/customers/{customer_id}/service-records/{service_item_id}", response_model=DigitalServiceRecordResponse)
def update_service_record(
    customer_id: int,
    service_item_id: int,
    data: DigitalServiceRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.query(DigitalCustomer).filter(DigitalCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    item = db.query(DigitalServiceItem).filter(DigitalServiceItem.id == service_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="服务内容不存在")

    record = db.query(DigitalServiceRecord).filter(
        DigitalServiceRecord.customer_id == customer_id,
        DigitalServiceRecord.service_item_id == service_item_id,
    ).first()
    if not record:
        record = DigitalServiceRecord(
            customer_id=customer_id,
            service_item_id=service_item_id,
        )
        db.add(record)

    done_changed = bool(record.is_done) != bool(data.is_done)
    record.is_done = bool(data.is_done)
    if record.is_done and (done_changed or not record.completed_at):
        record.completed_at = business_now()
    if not record.is_done:
        record.completed_at = None
    record.notes = _clean_optional(data.notes)
    record.updated_by = current_user.id
    record.updated_at = business_now()
    customer.updated_at = business_now()
    db.commit()
    _update_last_active_time(db, current_user)
    record = db.query(DigitalServiceRecord).options(
        joinedload(DigitalServiceRecord.service_item),
        joinedload(DigitalServiceRecord.updated_user),
    ).filter(DigitalServiceRecord.id == record.id).first()
    return build_service_record_response(record)
