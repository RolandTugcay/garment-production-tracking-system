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
from sqlalchemy import or_

import src.models as models
import src.form_helpers as form_helpers
from src.extensions import db

worker_classes_bp = Blueprint("worker_classes", __name__)

#=========================== WORKER CLASS: LIST, SEARCH, SORT, PAGINATE ===========================
@worker_classes_bp.get("/worker-classes")
@login_required
def list_worker_classes():
    search_query = (request.args.get("q", "", type=str) or "").strip()[:100]

    statement = db.select(models.WorkerClass)

    if search_query:
        search_pattern = f"%{search_query}%"
        statement = statement.where(
            or_(
                models.WorkerClass.code.ilike(search_pattern),
                models.WorkerClass.name.ilike(search_pattern),
                models.WorkerClass.description.ilike(search_pattern),
            )
        )

    sort_columns = {
        "id": models.WorkerClass.id,
        "code": models.WorkerClass.code,
        "name": models.WorkerClass.name,
        "status": models.WorkerClass.status,
        "description": models.WorkerClass.description,
        "created_at": models.WorkerClass.created_at,
        "updated_at": models.WorkerClass.updated_at,
    }

    sort_by = request.args.get("sort", "id")
    if sort_by not in sort_columns:
        sort_by = "id"

    sort_direction = request.args.get("direction", "asc").lower()
    if sort_direction not in {"asc", "desc"}:
        sort_direction = "asc"

    sort_column = sort_columns[sort_by]
    order_by = (
        sort_column.asc().nulls_last()
        if sort_direction == "asc"
        else sort_column.desc().nulls_last()
    )

    statement = statement.order_by(order_by, models.WorkerClass.id.asc())

    pagination = db.paginate(
        statement,
        page=request.args.get("page", 1, type=int),
        per_page=10,
        max_per_page=50,
    )

    # Used to disable Delete for worker classes assigned to workers.
    worker_class_ids = [item.id for item in pagination.items]
    used_worker_class_ids = set()

    if worker_class_ids:
        used_worker_class_ids = set(
            db.session.execute(
                db.select(models.Worker.worker_class_id)
                .where(
                    models.Worker.worker_class_id.in_(worker_class_ids)
                )
                .distinct()
            ).scalars().all()
        )

    return render_template(
        "worker-classes.html",
        worker_classes=pagination.items,
        pagination=pagination,
        search_query=search_query,
        sort_by=sort_by,
        sort_direction=sort_direction,
        used_worker_class_ids=used_worker_class_ids,
    )


#=========================== WORKER CLASS: CREATE ===========================
@worker_classes_bp.post("/worker-classes")
@login_required
def create_worker_class():
    _, error = form_helpers.save_record_from_form(
        db=db,
        model=models.WorkerClass,
        form_data=request.form,
        field_rules={
            "code": {
                "label": "Worker class code",
                "required": True,
                "max_length": 20,
                "unique": True,
            },
            "name": {
                "label": "Worker class name",
                "required": True,
                "max_length": 50,
                "unique": True,
            },
            "description": {
                "label": "Description",
                "required": False,
            },
            "status": {
                "label": "Status",
                "required": True,
            },
        },
    )

    if error:
        flash(error, "danger")
    else:
        flash("Worker class added successfully.", "success")

    return redirect(url_for("worker_classes.list_worker_classes"))


#=========================== WORKER CLASS: EDIT ===========================
@worker_classes_bp.post("/worker-classes/<int:worker_class_id>/edit")
@login_required
def edit_worker_class(worker_class_id):
    worker_class = db.session.get(models.WorkerClass, worker_class_id)

    if worker_class is None:
        abort(404)

    _, error = form_helpers.save_record_from_form(
        db=db,
        model=models.WorkerClass,
        record=worker_class,
        form_data=request.form,
        field_rules={
            # Code is intentionally omitted so it cannot be edited.
            "name": {
                "label": "Worker class name",
                "required": True,
                "max_length": 50,
                "unique": True,
            },
            "description": {
                "label": "Description",
                "required": False,
            },
            "status": {
                "label": "Status",
                "required": True,
            },
        },
    )

    if error:
        flash(error, "danger")
    else:
        flash("Worker class updated successfully.", "success")

    return redirect(url_for("worker_classes.list_worker_classes"))


#=========================== WORKER CLASS: DELETE ===========================
@worker_classes_bp.post("/worker-classes/<int:worker_class_id>/delete")
@login_required
def delete_worker_class(worker_class_id):
    _, error = form_helpers.delete_record(
        db=db,
        model=models.WorkerClass,
        record_id=worker_class_id,
        usage_checks=[
            {
                "model": models.Worker,
                "field": "worker_class_id",
                "message": (
                    "This worker class is assigned to a worker "
                    "and cannot be deleted."
                ),
            }
        ],
    )

    if error == "not_found":
        abort(404)

    if error:
        flash(error, "danger")
    else:
        flash("Worker class deleted successfully.", "success")

    return redirect(url_for("worker_classes.list_worker_classes"))