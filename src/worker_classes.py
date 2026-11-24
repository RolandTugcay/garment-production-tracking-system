from flask import Flask, flash, jsonify, render_template, redirect, request, url_for, abort
from src.extensions import db
from sqlalchemy import or_
import src.models as models
import src.form_helpers as form_helpers


def worker_classes():
    #========== SAVE RECORD ==========
    if request.method == "POST":
        worker_class, error = form_helpers.save_record_from_form(
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

        return redirect(url_for("worker_classes"))
    

    #========== GET ==========
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

    # Default sort = id
    sort_by = request.args.get("sort", "id")
    if sort_by not in sort_columns:
        sort_by = "id"

    # Default sort = asc
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

    # get used worker class ids
    # delete button disable if worker class id is used
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