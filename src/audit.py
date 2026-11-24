from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from flask import g, has_request_context
from flask_login import current_user
from sqlalchemy import inspect

import src.models as models


SENSITIVE_FIELD_PARTS = (
    "password",
    "token",
    "secret",
)


def snapshot_record(record):
    """Return the record's column values in a JSON-compatible dictionary."""
    values = {}

    for attribute in inspect(record).mapper.column_attrs:
        field_name = attribute.key

        if any(part in field_name.lower() for part in SENSITIVE_FIELD_PARTS):
            continue

        value = getattr(record, field_name)

        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        elif isinstance(value, (Decimal, UUID)):
            value = str(value)
        elif isinstance(value, Enum):
            value = value.value

        values[field_name] = value

    return values


def write_audit_log(
    *,
    db,
    record,
    action,
    old_values=None,
    new_values=None,
    change_summary=None,
):
    """Add an audit row to the current transaction. Does not commit."""
    action_by_user_id = None
    request_id = None

    if has_request_context():
        if current_user.is_authenticated:
            action_by_user_id = int(current_user.get_id())

        request_id = getattr(g, "request_id", None)

    primary_key_values = [
        str(getattr(record, column.key))
        for column in inspect(record).mapper.primary_key
    ]

    db.session.add(
        models.AuditLog(
            action_by_user_id=action_by_user_id,
            table_name=record.__table__.name,
            record_id=",".join(primary_key_values),
            action=action.upper(),
            old_values=old_values,
            new_values=new_values,
            change_summary=change_summary,
            request_id=request_id,
        )
    )