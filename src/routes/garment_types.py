#=========================== IMPORTS AND DEPENDENCIES ===========================
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
from sqlalchemy import String, cast, func, or_
from sqlalchemy.exc import IntegrityError

import src.models as models
from src.audit import snapshot_record, write_audit_log
from src.extensions import db


#=========================== BLUEPRINT AND CONSTANTS ===========================
garment_types_bp = Blueprint("garment_types", __name__)

GARMENT_TYPE_STATUSES = {"Active", "Inactive"}

#=========================== GARMENT TYPES LIST, SEARCH, SORT, PAGINATE ===========================
@garment_types_bp.get("/garment_types")
@login_required
def list_garment_types():

    # Read and normalize search options from the query string.
    search_query = (request.args.get("q", "", type=str) or "").strip()[:100]
    search_field = (
        request.args.get("search_field", "all_fields", type=str)
        or "all_fields"
    ).strip()

    # Map searchable field names to their database columns.
    search_columns = {
        "code": models.GarmentType.code,
        "name": models.GarmentType.name,
        "description": models.GarmentType.description,
        "created_at": cast(models.GarmentType.created_at, String),
        "updated_at": cast(models.GarmentType.updated_at, String),
    }

    # Fall back to searching all fields if the requested field is invalid.
    if search_field != "all_fields" and search_field not in search_columns:
        search_field = "all_fields"

    # Build the base garment type query.
    statement = db.select(models.GarmentType)

    # Apply a search across all fields or one selected field.
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

    # Map sort names to database columns.
    sort_columns = {
        "id": models.GarmentType.id,
        "code": models.GarmentType.code,
        "name": models.GarmentType.name,
        "description": models.GarmentType.description,
        "created_at": models.GarmentType.created_at,
        "updated_at": models.GarmentType.updated_at,
    }

    # Validate the requested sort field and direction.
    sort_by = request.args.get("sort", "id")
    if sort_by not in sort_columns:
        sort_by = "id"

    sort_direction = (request.args.get("direction", "asc") or "asc").lower()
    if sort_direction not in {"asc", "desc"}:
        sort_direction = "asc"

    # Build and apply the sort expression.
    sort_column = sort_columns[sort_by]
    order_by = (
        sort_column.asc().nulls_last()
        if sort_direction == "asc"
        else sort_column.desc().nulls_last()
    )
    statement = statement.order_by(order_by, models.GarmentType.id.asc())

    # Retrieve a paginated garment type result set.
    pagination = db.paginate(
        statement,
        page=request.args.get("page", 1, type=int),
        per_page=10,
        max_per_page=50,
    )

    # Find which garment_types on this page are referenced by garment job templates.
    garment_type_ids = [garment_type.id for garment_type in pagination.items]
    used_garment_type_ids = set()

    if garment_type_ids:
        used_garment_type_ids = set(
            db.session.execute(
                db.select(models.GarmentJobTemplate.garment_type_id)
                .where(models.GarmentJobTemplate.garment_type_id.in_(garment_type_ids))
                .distinct()
            ).scalars()
        )

    # Send garment type records and page controls to the template.
    return render_template(
        "garment_types.html",
        garment_types=pagination.items,
        pagination=pagination,
        search_query=search_query,
        search_field=search_field,
        sort_by=sort_by,
        sort_direction=sort_direction,
        used_garment_type_ids=used_garment_type_ids,
    )


#=========================== GARMENT TYPES READ AND VALIDATE FORM ===========================
def read_garment_type_form(garment_type_id=None):
    # Read and normalize values submitted by the garment type form.
    code = (request.form.get("code") or "").strip()
    name = (request.form.get("name") or "").strip()
    status = (request.form.get("status") or "").strip()
    description = (request.form.get("description") or "").strip() or None

    # Garment type codes are required only when creating a garment_type.
    if garment_type_id is None:
        if not code:
            return None, "Garment type code is required."
        if len(code) > 10:
            return None, "Garment type code must be 10 characters or fewer."

    # Validate the garment type name.
    if not name:
        return None, "Garment type name is required."
    if len(name) > 50:
        return None, "Garment type name must be 50 characters or fewer."

    # Validate the selected status.
    if status not in GARMENT_TYPE_STATUSES:
        return None, "Select a valid customer status."

    # Check whether another garment type already uses the submitted code.
    if garment_type_id is None:
        code_query = db.select(models.GarmentType.id).where(
            models.GarmentType.code == code
        )
        if db.session.execute(code_query).scalar_one_or_none() is not None:
            return None, "A garment type with this code already exists."

    # Check whether another garment type already uses the submitted code.
    if garment_type_id is None:
        name_query = db.select(models.GarmentType.id).where(
            models.GarmentType.name == name
        )
        if db.session.execute(name_query).scalar_one_or_none() is not None:
            return None, "A garment type with this name already exists."

    # Return the code for creates and editable fields only for updates.
    if garment_type_id is None:
        return {
            "code": code,
            "name": name,
            "status":status,
            "description": description
        }, None

    return {
        "name": name,
        "status":status,
        "description": description
    }, None


#=========================== GARMENT TYPES CREATE ===========================
@garment_types_bp.post("/garment_types")
@login_required
def create_garment_type():
    # Validate and extract submitted garment type values.
    values, error = read_garment_type_form()

    if error:
        flash(error, "danger")
        return redirect(url_for("garment_types.list_garment_types"))

    # Construct a garment type model from the validated values.
    garment_type = models.GarmentType(**values)

    try:
        # Insert and refresh the garment type.
        db.session.add(garment_type)
        db.session.flush()
        db.session.refresh(garment_type)

        # Record the CREATE action in the audit log.
        write_audit_log(
            db=db,
            record=garment_type,
            action="CREATE",
            new_values=snapshot_record(garment_type),
            change_summary=f"Garment type {garment_type.code} created",
        )

        # Commit the garment type and audit row together.
        db.session.commit()
        flash("Garment type added successfully.", "success")
    except IntegrityError:
        # Roll back both operations when database constraints fail.
        db.session.rollback()
        flash(
            "Could not save the garment type. Check that the garment type name and code are unique.",
            "danger",
        )

    return redirect(url_for("garment_types.list_garment_types"))


#=========================== GARMENT TYPES EDIT ===========================
@garment_types_bp.post("/garment_types/<int:garment_type_id>/edit")
@login_required
def edit_garment_type(garment_type_id):
    # Load the garment type or return 404 if it does not exist.
    garment_type = db.session.get(models.GarmentType, garment_type_id)
    if garment_type is None:
        abort(404)

    # Validate and extract submitted values.
    values, error = read_garment_type_form(garment_type_id=garment_type_id)

    if error:
        flash(error, "danger")
        return redirect(url_for("garment_types.list_garment_types"))

    # Compare editable fields before touching updated_at or writing an audit row.
    changed_values = {
        field: value
        for field, value in values.items()
        if getattr(garment_type, field) != value
    }

    # Stop without changing anything when no editable field is different.
    if not changed_values:
        flash("No changes were made.", "info")
        return redirect(url_for("garment_types.list_garment_types"))

    # Capture the original values for the audit log.
    old_values = snapshot_record(garment_type)

    # Apply only the fields that changed.
    for field, value in changed_values.items():
        setattr(garment_type, field, value)

    # Refresh updated_at because the table default only applies on insert.
    garment_type.updated_at = db.func.current_timestamp()

    try:
        # Flush and refresh so audit values include the final database state.
        db.session.flush()
        db.session.refresh(garment_type)

        # Record the UPDATE action with old and new values.
        write_audit_log(
            db=db,
            record=garment_type,
            action="UPDATE",
            old_values=old_values,
            new_values=snapshot_record(garment_type),
            change_summary=f"Garment type {garment_type.code} updated",
        )

        # Commit the garment type update and audit row together.
        db.session.commit()
        flash("Garment type updated successfully.", "success")
    except IntegrityError:
        # Roll back all changes when database constraints fail.
        db.session.rollback()
        flash(
            "Could not update the garment type. Check that the garment type name is unique.",
            "danger",
        )

    return redirect(url_for("garment_types.list_garment_types"))


#=========================== GARMENT TYPES DELETE ===========================
@garment_types_bp.post("/garment_types/<int:garment_type_id>/delete")
@login_required
def delete_garment_type(garment_type_id):
    # Load the garment type or return 404 if it does not exist.
    garment_type = db.session.get(models.GarmentType, garment_type_id)
    if garment_type is None:
        abort(404)

    # Check whether the garment type is referenced by an existing garment job template.
    has_job_templates = db.session.execute(
        db.select(models.GarmentJobTemplate.id)
        .where(models.GarmentJobTemplate.garment_type_id == garment_type_id)
        .limit(1)
    ).scalar_one_or_none()

    if has_job_templates is not None:
        flash(
            "This garment type has job templates and cannot be deleted.",
            "danger",
        )
        return redirect(url_for("garment_types.list_garment_types"))

    # Capture original values for the DELETE audit row.
    old_values = snapshot_record(garment_type)

    try:
        # Remove the garment type and record the DELETE action.
        db.session.delete(garment_type)

        write_audit_log(
            db=db,
            record=garment_type,
            action="DELETE",
            old_values=old_values,
            change_summary=f"Garment type {garment_type.code} deleted",
        )

        # Commit the deletion and audit row together.
        db.session.commit()
        flash("Garment type deleted successfully.", "success")
    except IntegrityError:
        # Roll back the deletion if it conflicts with database references.
        db.session.rollback()
        flash(
            "This garment type is referenced by another record and cannot be deleted.",
            "danger",
        )

    return redirect(url_for("garment_types.list_garment_types"))
