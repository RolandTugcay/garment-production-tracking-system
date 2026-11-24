from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from src.audit import snapshot_record, write_audit_log


#============================== CREATE/EDIT SAVE ENTRY ==============================
def save_record_from_form(*, db, model, form_data, field_rules, record=None):
    values = {}

    for field_name, rules in field_rules.items():
        column = getattr(model, field_name)
        label = rules.get("label", field_name.replace("_", " ").title())

        raw_value = form_data.get(field_name, "")
        value = raw_value.strip() if isinstance(raw_value, str) else raw_value

        if value == "":
            value = None

        if rules.get("required") and value is None:
            return None, f"{label} is required."

        if value is not None:
            max_length = rules.get("max_length")

            if max_length and isinstance(value, str) and len(value) > max_length:
                return None, f"{label} must be {max_length} characters or fewer."

            converter = rules.get("converter")
            if converter:
                try:
                    value = converter(value)
                except (TypeError, ValueError):
                    return None, f"{label} has an invalid value."

            if rules.get("unique"):
                query = db.select(model).where(column == value)

                if record is not None:
                    primary_keys = inspect(model).primary_key

                    if len(primary_keys) != 1:
                        raise ValueError(
                            "Updating records with composite primary keys "
                            "is not supported by this helper."
                        )

                    primary_key = primary_keys[0]
                    record_id = getattr(record, primary_key.key)
                    query = query.where(primary_key != record_id)

                existing_record = db.session.execute(
                    query.limit(1)
                ).scalar_one_or_none()

                if existing_record is not None:
                    return None, f"A record with this {label.lower()} already exists."

        values[field_name] = value

    # Before applying form values:
    old_values = snapshot_record(record) if record is not None else None

    if record is None:
        record = model(**values)
        db.session.add(record)
        action = "CREATE"
    else:
        for field_name, value in values.items():
            setattr(record, field_name, value)
        action = "UPDATE"

    try:
        db.session.flush()
        db.session.refresh(record)

        write_audit_log(
            db=db,
            record=record,
            action=action,
            old_values=old_values,
            new_values=snapshot_record(record),
            change_summary=f"{action.title()} {record.__table__.name}",
        )

        db.session.commit()
        return record, None

    except IntegrityError:
        db.session.rollback()
        return None, "Could not save the record. Check for duplicate or invalid values."

#============================== DELETE ENTRY ==============================
def delete_record(*, db, model, record_id, usage_checks=None):
    record = db.session.get(model, record_id)

    if record is None:
        return None, "not_found"

    for check in usage_checks or []:
        reference_model = check["model"]
        reference_column = getattr(reference_model, check["field"])

        reference_exists = db.session.execute(
            db.select(reference_model)
            .where(reference_column == record_id)
            .limit(1)
        ).first()

        if reference_exists is not None:
            return record, check["message"]

    old_values = snapshot_record(record)

    try:
        db.session.delete(record)

        write_audit_log(
            db=db,
            record=record,
            action="DELETE",
            old_values=old_values,
            change_summary=f"Deleted {model.__tablename__} record",
        )

        db.session.commit()
        return record, None

    except IntegrityError:
        db.session.rollback()
        return None, "This record is still referenced by another record."