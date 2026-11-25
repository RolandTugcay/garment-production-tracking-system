from datetime import date

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from flask_login import login_required
from sqlalchemy import String, cast, or_
from sqlalchemy.exc import IntegrityError

import src.models as models
from src.audit import snapshot_record, write_audit_log
from src.extensions import db

workers_bp = Blueprint("workers", __name__)


#==================== WORKERS: LIST, SEARCH, FILTER, SORT, PAGINATE ====================
@workers_bp.get("/workers")
@login_required
def list_workers():
    search_query = (request.args.get("q", "", type=str) or "").strip()[:100]
    search_field = (request.args.get("search_field", "all_fields", type=str) or "all_fields").strip()
    worker_class_id = request.args.get("worker_class_id", type=int)

    search_columns = {
        "code": models.Worker.code,
        "worker_class": models.WorkerClass.name,
        "status": models.Worker.status,
        "first_name": models.Worker.first_name,
        "last_name": models.Worker.last_name,
        "phone": models.Worker.phone,
        "email": models.Worker.email,
        "address": models.Worker.address,
        "hire_date": cast(models.Worker.hire_date, String),
        "notes": models.Worker.notes,
        "created_at": cast(models.Worker.created_at, String),
        "updated_at": cast(models.Worker.updated_at, String),
    }

    # Ignore unknown field names supplied in the URL.
    if search_field != "all_fields" and search_field not in search_columns:
        search_field = "all_fields"

    statement = (
        db.select(models.Worker)
        .join(
            models.WorkerClass,
            models.Worker.worker_class_id == models.WorkerClass.id,
        )
    )

    if search_query:
        search_pattern = f"%{search_query}%"

        if search_field == "all_fields":
            statement = statement.where(
                or_(
                    *(
                        column.ilike(search_pattern)
                        for column in search_columns.values()
                    )
                )
            )
        else:
            statement = statement.where(
                search_columns[search_field].ilike(search_pattern)
            )

    if worker_class_id is not None:
        statement = statement.where(
            models.Worker.worker_class_id == worker_class_id
        )

    sort_columns = {
        "id": models.Worker.id,
        "first_name": models.Worker.first_name,
        "last_name": models.Worker.last_name,
        "phone": models.Worker.phone,
        "email": models.Worker.email,
        "address": models.Worker.address,
        "hire_date": models.Worker.hire_date,
        "notes": models.Worker.notes,
        "code": models.Worker.code,
        "status": models.Worker.status,
        "worker_class": models.WorkerClass.name,
        "created_at": models.Worker.created_at,
        "updated_at": models.Worker.updated_at,
    }

    sort_by = request.args.get("sort", "id")
    if sort_by not in sort_columns:
        sort_by = "id"

    sort_direction = (request.args.get("direction", "asc") or "asc").lower()
    if sort_direction not in {"asc", "desc"}:
        sort_direction = "asc"

    sort_column = sort_columns[sort_by]
    order_by = (
        sort_column.asc().nulls_last()
        if sort_direction == "asc"
        else sort_column.desc().nulls_last()
    )

    statement = statement.order_by(order_by, models.Worker.id.asc())

    pagination = db.paginate(
        statement,
        page=request.args.get("page", 1, type=int),
        per_page=10,
        max_per_page=50,
    )

    # Disable deletion for workers linked to user accounts.
    worker_ids = [worker.id for worker in pagination.items]
    used_worker_ids = set()

    if worker_ids:
        used_worker_ids = set(
            db.session.execute(
                db.select(models.User.worker_id)
                .where(models.User.worker_id.in_(worker_ids))
                .distinct()
            ).scalars()
        )

    worker_classes = db.session.execute(
        db.select(models.WorkerClass).filter_by(status='Active').order_by(models.WorkerClass.name.asc())
    ).scalars().all()

    return render_template(
        "workers.html",
        workers=pagination.items,
        pagination=pagination,
        search_query=search_query,
        worker_class_id=worker_class_id,
        worker_classes=worker_classes,
        sort_by=sort_by,
        sort_direction=sort_direction,
        used_worker_ids=used_worker_ids,
        search_field=search_field,
    )


#==================== RAED FORM INPUTS ====================
def read_worker_form(worker_id=None):
    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    phone = (request.form.get("phone") or "").strip() or None
    email = (request.form.get("email") or "").strip().lower() or None
    hire_date_value = (request.form.get("hire_date") or "").strip()
    status = (request.form.get("status") or "").strip()
    address = (request.form.get("address") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None
    worker_class_id_value = (request.form.get("worker_class_id") or "").strip()

    # Validate inputs
    if not first_name:
        return None, "First name is required."
    if len(first_name) > 50:
        return None, "First name must be 50 characters or fewer."
    if not last_name:
        return None, "Last name is required."
    if len(last_name) > 50:
        return None, "Last name must be 50 characters or fewer."
    if phone and len(phone) > 30:
        return None, "Phone must be 30 characters or fewer."
    if email and len(email) > 254:
        return None, "Email must be 254 characters or fewer."
    if status not in {"Active", "Inactive", "Terminated", "On leave"}:
        return None, "Select a valid worker status."

    try:
        worker_class_id = int(worker_class_id_value) if worker_class_id_value else None
    except (TypeError, ValueError):
        worker_class_id = None

    if worker_class_id is None:
        return None, "Select a worker class."

    worker_class = db.session.get(models.WorkerClass, worker_class_id)
    if worker_class is None:
        return None, "The selected worker class does not exist."

    hire_date = None
    if hire_date_value:
        try:
            hire_date = date.fromisoformat(hire_date_value)
        except ValueError:
            return None, "Enter a valid hire date."


    if email:
        email_query = db.select(models.Worker.id).where(
            models.Worker.email == email
        )

        if worker_id is not None:
            email_query = email_query.where(models.Worker.id != worker_id)

        if db.session.execute(email_query).scalar_one_or_none() is not None:
            return None, "A worker with that email already exists."

    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "email": email,
        "hire_date": hire_date,
        "status": status,
        "address": address,
        "notes": notes,
        "worker_class_id": worker_class_id,
    }, None


#==================== WORKERS: CREATE ====================
@workers_bp.post("/workers")
@login_required
def create_worker():
    values, error = read_worker_form()

    if error:
        flash(error, "danger")
        return redirect(url_for("workers.list_workers"))

    worker = models.Worker(**values)

    try:
        db.session.add(worker)
        db.session.flush()
        db.session.refresh(worker)

        write_audit_log(
            db=db,
            record=worker,
            action="CREATE",
            new_values=snapshot_record(worker),
            change_summary=f"Worker {worker.code} created",
        )

        db.session.commit()
        flash("Worker added successfully.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Could not save the worker. Check that the email is unique.", "danger")

    return redirect(url_for("workers.list_workers"))


#==================== WORKERS: EDIT ====================
@workers_bp.post("/workers/<int:worker_id>/edit")
@login_required
def edit_worker(worker_id):
    worker = db.session.get(models.Worker, worker_id)
    if worker is None:
        abort(404)

    values, error = read_worker_form(worker_id=worker_id)

    if error:
        flash(error, "danger")
        return redirect(url_for("workers.list_workers"))

    # Skip the database update and audit entry when submitted fields are unchanged.
    changed_values = {
        field: value
        for field, value in values.items()
        if getattr(worker, field) != value
    }

    if not changed_values:
        flash("No changes were made.", "info")
        return redirect(url_for("workers.list_workers"))

    old_values = snapshot_record(worker)

    for field, value in changed_values.items():
        setattr(worker, field, value)

    try:
        db.session.flush()
        db.session.refresh(worker)

        write_audit_log(
            db=db,
            record=worker,
            action="UPDATE",
            old_values=old_values,
            new_values=snapshot_record(worker),
            change_summary=f"Worker {worker.code} updated",
        )

        db.session.commit()
        flash("Worker updated successfully.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Could not update the worker. Check that the email is unique.", "danger")

    return redirect(url_for("workers.list_workers"))


#==================== WORKERS: DELETE ====================
@workers_bp.post("/workers/<int:worker_id>/delete")
@login_required
def delete_worker(worker_id):
    worker = db.session.get(models.Worker, worker_id)
    if worker is None:
        abort(404)

    # A worker linked to a user account cannot be deleted.
    linked_user = db.session.execute(
        db.select(models.User.id)
        .where(models.User.worker_id == worker_id)
        .limit(1)
    ).scalar_one_or_none()

    if linked_user is not None:
        flash(
            "This worker is linked to a user account and cannot be deleted.",
            "danger",
        )
        return redirect(url_for("workers.list_workers"))

    old_values = snapshot_record(worker)

    try:
        db.session.delete(worker)

        write_audit_log(
            db=db,
            record=worker,
            action="DELETE",
            old_values=old_values,
            change_summary=f"Worker {worker.code} deleted",
        )

        db.session.commit()
        flash("Worker deleted successfully.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("This worker is used by another record and cannot be deleted.", "danger")

    return redirect(url_for("workers.list_workers"))
