"""
周期任务生成服务。

当前先支持每日重复：规则在有效日期内，每天最多生成一条待处理任务。
"""
import json
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.timezone import business_today
from app.models.models import RecurringTaskRule, Task, TaskColumn


def parse_due_time(value: str | None) -> time | None:
    if not value:
        return None
    hour_text, minute_text = value.split(":", 1)
    return time(hour=int(hour_text), minute=int(minute_text))


def build_due_datetime(occurrence_date: date, due_time: str | None):
    parsed_time = parse_due_time(due_time)
    if not parsed_time:
        return None
    return datetime.combine(occurrence_date, parsed_time)


def iter_dates(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def resolve_rule_column(db: Session, rule: RecurringTaskRule):
    if rule.column_id:
        column = db.query(TaskColumn).filter(TaskColumn.id == rule.column_id).first()
        if column and column.project_id == rule.project_id:
            return column
    return db.query(TaskColumn).filter(
        TaskColumn.project_id == rule.project_id,
        TaskColumn.name == "待处理",
    ).order_by(TaskColumn.order.asc(), TaskColumn.id.asc()).first()


def create_task_for_rule(db: Session, rule: RecurringTaskRule, occurrence_date: date) -> bool:
    exists = db.query(Task.id).filter(
        Task.recurrence_rule_id == rule.id,
        Task.recurrence_occurrence_date == occurrence_date,
    ).first()
    if exists:
        return False

    column = resolve_rule_column(db, rule)
    if not column:
        return False

    due_date = build_due_datetime(occurrence_date, rule.due_time)
    task = Task(
        project_id=rule.project_id,
        column_id=column.id,
        title=rule.title,
        description=rule.description,
        node_output=rule.node_output,
        linked_document_id=rule.linked_document_id,
        assignee_id=rule.assignee_id,
        due_date=due_date,
        delivery_dates=json.dumps([due_date.isoformat()]) if due_date else None,
        completed_by=json.dumps([]),
        recurrence_rule_id=rule.id,
        recurrence_occurrence_date=occurrence_date,
    )
    db.add(task)
    return True


def generate_due_recurring_tasks(db: Session, through_date: date | None = None) -> int:
    today = through_date or business_today()
    created_count = 0
    rules = db.query(RecurringTaskRule).filter(RecurringTaskRule.is_active == True).all()

    for rule in rules:
        if rule.recurrence_type != "daily":
            continue
        if rule.end_date and rule.end_date < today:
            rule.is_active = False
            continue

        start_date = rule.start_date
        if rule.last_generated_date:
            start_date = max(start_date, rule.last_generated_date + timedelta(days=1))
        else:
            start_date = max(start_date, today)

        end_date = min(today, rule.end_date or today)
        if start_date > end_date:
            continue

        for occurrence_date in iter_dates(start_date, end_date):
            if create_task_for_rule(db, rule, occurrence_date):
                created_count += 1
            rule.last_generated_date = occurrence_date

    return created_count
