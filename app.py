import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, flash, jsonify, render_template, redirect, request, url_for, abort
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text, or_
from sqlalchemy.exc import IntegrityError
from src.extensions import database_url, db, login_manager
import src.models as models
import src.form_helpers as form_helpers

app = Flask(__name__)

secret_key = os.getenv("FLASK_SECRET_KEY")
if not secret_key:
    raise RuntimeError("Set FLASK_SECRET_KEY in your environment or .env file.")

app.config["SECRET_KEY"] = secret_key
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager.init_app(app)
csrf = CSRFProtect(app)

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(models.User, int(user_id))
    except (TypeError, ValueError):
        return None

#=========================== LOGIN ===========================
@app.route("/", methods=["GET", "POST"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = models.User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("index.html")


#=========================== LOGOUT ===========================
@app.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():

    return render_template(
        "dashboard.html"
    )


#=========================== WORKER CLASSES ===========================
@app.route("/worker-classes", methods=["GET", "POST"])
@login_required
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



#=========================== WORKER CLASSES: EDIT ===========================
@app.post("/worker-classes/<int:worker_class_id>/edit")
@login_required
def edit_worker_class(worker_class_id):
    worker_class = db.session.get(models.WorkerClass, worker_class_id)
    form_data = request.form.to_dict()
    form_data["is_active"] = request.form.get("is_active") == "true"

    if worker_class is None:
        abort(404)

    worker_class, error = form_helpers.save_record_from_form(
        db=db,
        model=models.WorkerClass,
        record=worker_class,
        form_data=request.form,
        field_rules={
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

    return redirect(url_for("worker_classes"))

#=========================== WORKER CLASSES: DELETE ===========================
@app.post("/worker-classes/<int:worker_class_id>/delete")
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

    return redirect(url_for("worker_classes"))


@app.get("/health/db")
def check_database():
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return jsonify(status="connected"), 200

    except Exception:
        app.logger.exception("Database health failed")
        return jsonify(status="error", message="Database connection failed"), 503

if __name__ == "__main__":
    app.run(debug=True)