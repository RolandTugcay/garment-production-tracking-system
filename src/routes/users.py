from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import String, cast, func, or_
from sqlalchemy.exc import IntegrityError

import src.models as models
from src.audit import snapshot_record, write_audit_log
from src.extensions import db

users_bp = Blueprint("users", __name__)

#=========================== Supported values used for form validation. ===========================
ALLOWED_ROLES = {"Administrator", "Manager", "User", "Guest"}
ALLOWED_STATUSES = {"Active", "Inactive"}


#=========================== USERS: LIST, SEARCH, FILTER, SORT, PAGINATE ===========================
@users_bp.get("/users")
@login_required
def list_users():
    # Read and limit the search and filter inputs from the request.
    search_query = (request.args.get("q", "", type=str) or "").strip()[:100]
    search_field = (
        request.args.get("search_field", "all_fields", type=str)
        or "all_fields"
    ).strip()
    worker_id = request.args.get("worker_id", type=int)

    worker_full_name = func.concat(
        models.Worker.first_name,
        " ",
        models.Worker.last_name,
    )

    search_columns = {
        "username": models.User.username,
        "worker_full_name": worker_full_name,
        "role": models.User.role,
        "status": models.User.status,
        "created_at": cast(models.User.created_at, String),
        "updated_at": cast(models.User.updated_at, String),
    }

    # Fall back to an all-fields search when the requested field is invalid.
    if search_field != "all_fields" and search_field not in search_columns:
        search_field = "all_fields"

    # Start with the user list and join worker details for search and display.
    statement = (
        db.select(models.User)
        .outerjoin(
            models.Worker,
            models.User.worker_id == models.Worker.id,
        )
    )

    # Apply text search across the selected field or all searchable fields.
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

    if worker_id is not None:
        statement = statement.where(models.User.worker_id == worker_id)

    # Map allowed sort options to model columns.
    sort_columns = {
        "id": models.User.id,
        "username": models.User.username,
        "worker_full_name": worker_full_name,
        "role": models.User.role,
        "status": models.User.status,
        "created_at": models.User.created_at,
        "updated_at": models.User.updated_at,
    }

    sort_by = request.args.get("sort", "id")
    if sort_by not in sort_columns:
        sort_by = "id"

    sort_direction = (request.args.get("direction", "asc") or "asc").lower()
    if sort_direction not in {"asc", "desc"}:
        sort_direction = "asc"

    # Build the final sort expression and paginate the result.
    sort_column = sort_columns[sort_by]
    order_by = (
        sort_column.asc().nulls_last()
        if sort_direction == "asc"
        else sort_column.desc().nulls_last()
    )

    statement = statement.order_by(order_by, models.User.id.asc())

    pagination = db.paginate(
        statement,
        page=request.args.get("page", 1, type=int),
        per_page=10,
        max_per_page=50,
    )

    # Collect user IDs linked to audit records so those accounts cannot be deleted.
    user_ids = [user.id for user in pagination.items]
    used_user_ids = set()

    if user_ids:
        used_user_ids = set(
            db.session.execute(
                db.select(models.AuditLog.action_by_user_id)
                .where(models.AuditLog.action_by_user_id.in_(user_ids))
                .distinct()
            ).scalars()
        )

    # Load worker/class pairs for user-row display; build an active-only dropdown list.
    worker_rows = db.session.execute(
        db.select(models.Worker, models.WorkerClass)
        .join(
            models.WorkerClass,
            models.Worker.worker_class_id == models.WorkerClass.id,
        )
        .order_by(models.Worker.first_name.asc(), models.Worker.last_name.asc())
    ).all()

    workers_by_id = {
        worker.id: worker
        for worker, worker_class in worker_rows
    }
    worker_classes_by_worker_id = {
        worker.id: worker_class
        for worker, worker_class in worker_rows
    }
    workers = [
        worker
        for worker, worker_class in worker_rows
        if worker.status == "Active"
    ]

    return render_template(
        "users.html",
        users=pagination.items,
        pagination=pagination,
        search_query=search_query,
        search_field=search_field,
        worker_id=worker_id,
        workers=workers,
        workers_by_id=workers_by_id,
        worker_classes_by_worker_id=worker_classes_by_worker_id,
        sort_by=sort_by,
        sort_direction=sort_direction,
        used_user_ids=used_user_ids,
    )

#=========================== USERS: READ FORM INPUTS ===========================
def read_user_form(*, user_id=None):
    # Read and normalize submitted account fields.
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    role = (request.form.get("role") or "").strip()
    status = (request.form.get("status") or "").strip()
    worker_id_value = (request.form.get("worker_id") or "").strip()

    # Validate the username and password requirements.
    if not username:
        return None, "Username is required."
    if len(username) < 8 or len(username) > 15:
        return None, "Username must be 8 to 15 characters."

    if user_id is None and not password:
        return None, "Password is required when creating a user."
    if password and len(password) < 8:
        return None, "Password must be at least 8 characters."

    # Validate role and status selections.
    if role not in ALLOWED_ROLES:
        return None, "Select a valid role."
    if status not in ALLOWED_STATUSES:
        return None, "Select a valid user status."

    # Convert and verify the selected worker.
    if worker_id_value:
        try:
            worker_id = int(worker_id_value)
        except ValueError:
            return None, "Select a valid worker."
    else:
        worker_id = None

    if (
        worker_id is not None
        and db.session.get(models.Worker, worker_id) is None
    ):
        return None, "The selected worker does not exist."

    # Reject duplicate usernames, excluding the account being edited.
    username_query = db.select(models.User.id).where(
        models.User.username == username
    )
    if user_id is not None:
        username_query = username_query.where(models.User.id != user_id)

    if db.session.execute(username_query).scalar_one_or_none() is not None:
        return None, "Username already exists."

    # Return normalized values for create or update operations.
    values = {
        "username": username,
        "role": role,
        "status": status,
        "worker_id": worker_id,
        "password": password,
    }
    return values, None


#=========================== USERS: CREATE ===========================
@users_bp.post("/users")
@login_required
def create_user():
    # Validate and normalize the submitted form.
    values, error = read_user_form()

    if error:
        flash(error, "danger")
        return redirect(url_for("users.list_users"))

    password = values.pop("password")
    user = models.User(**values)
    user.set_password(password)

    # Save the account and record its creation in the audit log.
    try:
        db.session.add(user)
        db.session.flush()
        db.session.refresh(user)

        write_audit_log(
            db=db,
            record=user,
            action="CREATE",
            new_values=snapshot_record(user),
            change_summary=f"User {user.username} created",
        )

        db.session.commit()
        flash("User added successfully.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(
            "Could not save the user. Check that the username is unique.",
            "danger",
        )

    return redirect(url_for("users.list_users"))


#=========================== USERS: EDIT ===========================
@users_bp.post("/users/<int:user_id>/edit")
@login_required
def edit_user(user_id):
    # Load the target account or return a 404 response.
    user = db.session.get(models.User, user_id)
    if user is None:
        abort(404)

    values, error = read_user_form(user_id=user_id)

    if error:
        flash(error, "danger")
        return redirect(url_for("users.list_users"))

    password = values.pop("password")

    # Compare submitted values against the existing account.
    changed_values = {
        field: value
        for field, value in values.items()
        if getattr(user, field) != value
    }
    password_changed = bool(password) and not user.check_password(password)

    if not changed_values and not password_changed:
        flash("No changes were made.", "info")
        return redirect(url_for("users.list_users"))

    # Capture the original state and apply changed fields.
    old_values = snapshot_record(user)

    for field, value in changed_values.items():
        setattr(user, field, value)

    if password_changed:
        user.set_password(password)

    # Save the changes and add an update audit entry.
    try:
        db.session.flush()
        db.session.refresh(user)

        write_audit_log(
            db=db,
            record=user,
            action="UPDATE",
            old_values=old_values,
            new_values=snapshot_record(user),
            change_summary=f"User {user.username} updated",
        )

        db.session.commit()
        flash("User updated successfully.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(
            "Could not update the user. Check that the username is unique.",
            "danger",
        )

    return redirect(url_for("users.list_users"))


#=========================== USERS: DELETE ===========================
@users_bp.post("/users/<int:user_id>/delete")
@login_required
def delete_user(user_id):
    # Load the target account or return a 404 response.
    user = db.session.get(models.User, user_id)
    if user is None:
        abort(404)

    if int(current_user.get_id()) == user_id:
        flash("You cannot delete the account you are currently using.", "danger")
        return redirect(url_for("users.list_users"))

    # Prevent deletion of accounts that performed audited actions.
    existing_audit = db.session.execute(
        db.select(models.AuditLog.id)
        .where(models.AuditLog.action_by_user_id == user_id)
        .limit(1)
    ).scalar_one_or_none()

    if existing_audit is not None:
        flash(
            "This user has performed actions and cannot be deleted.",
            "danger",
        )
        return redirect(url_for("users.list_users"))

    old_values = snapshot_record(user)

    # Delete the account and record the deletion in the audit log.
    try:
        db.session.delete(user)

        write_audit_log(
            db=db,
            record=user,
            action="DELETE",
            old_values=old_values,
            change_summary=f"User {user.username} deleted",
        )

        db.session.commit()
        flash("User deleted successfully.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(
            "This user is referenced by another record and cannot be deleted.",
            "danger",
        )

    return redirect(url_for("users.list_users"))
