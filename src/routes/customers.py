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
from sqlalchemy import String, cast, or_
from sqlalchemy.exc import IntegrityError

import src.models as models
from src.audit import snapshot_record, write_audit_log
from src.extensions import db


#=========================== BLUEPRINT AND CONSTANTS ===========================
customers_bp = Blueprint("customers", __name__)

CUSTOMER_STATUSES = {"Active", "Inactive"}


#=========================== CUSTOMERS: LIST, SEARCH, SORT, PAGINATE ===========================
@customers_bp.get("/customers")
@login_required
def list_customers():
    # Read and normalize search options from the query string.
    search_query = (request.args.get("q", "", type=str) or "").strip()[:100]
    search_field = (
        request.args.get("search_field", "all_fields", type=str)
        or "all_fields"
    ).strip()

    # Map searchable field names to their database columns.
    search_columns = {
        "id": cast(models.Customer.id, String),
        "code": models.Customer.code,
        "name": models.Customer.name,
        "status": models.Customer.status,
        "address": models.Customer.address,
        "notes": models.Customer.notes,
        "created_at": cast(models.Customer.created_at, String),
        "updated_at": cast(models.Customer.updated_at, String),
    }

    # Fall back to searching all fields if the requested field is invalid.
    if search_field != "all_fields" and search_field not in search_columns:
        search_field = "all_fields"

    # Build the base customer query.
    statement = db.select(models.Customer)

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
        "id": models.Customer.id,
        "code": models.Customer.code,
        "name": models.Customer.name,
        "status": models.Customer.status,
        "address": models.Customer.address,
        "notes": models.Customer.notes,
        "created_at": models.Customer.created_at,
        "updated_at": models.Customer.updated_at,
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
    statement = statement.order_by(order_by, models.Customer.id.asc())

    # Retrieve a paginated customer result set.
    pagination = db.paginate(
        statement,
        page=request.args.get("page", 1, type=int),
        per_page=10,
        max_per_page=50,
    )

    # Find which customers on this page are referenced by purchase orders.
    customer_ids = [customer.id for customer in pagination.items]
    customers_with_orders = set()

    if customer_ids:
        customers_with_orders = set(
            db.session.execute(
                db.select(models.PurchaseOrder.customer_id)
                .where(models.PurchaseOrder.customer_id.in_(customer_ids))
                .distinct()
            ).scalars()
        )

    # Send customer records and page controls to the template.
    return render_template(
        "customers.html",
        customers=pagination.items,
        pagination=pagination,
        search_query=search_query,
        search_field=search_field,
        sort_by=sort_by,
        sort_direction=sort_direction,
        customers_with_orders=customers_with_orders
    )


#=========================== CUSTOMERS: READ AND VALIDATE FORM ===========================
def read_customer_form(customer_id=None):
    # Read and normalize values submitted by the customer form.
    code = (request.form.get("code") or "").strip()
    name = (request.form.get("name") or "").strip()
    status = (request.form.get("status") or "").strip()
    address = (request.form.get("address") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    # Customer codes are required only when creating a customer.
    if customer_id is None:
        if not code:
            return None, "Customer code is required."
        if len(code) > 20:
            return None, "Customer code must be 20 characters or fewer."

    # Validate the customer name.
    if not name:
        return None, "Customer name is required."
    if len(name) > 150:
        return None, "Customer name must be 150 characters or fewer."

    # Validate the selected status.
    if status not in CUSTOMER_STATUSES:
        return None, "Select a valid customer status."

    # Check whether another customer already uses the submitted code.
    if customer_id is None:
        code_query = db.select(models.Customer.id).where(
            models.Customer.code == code
        )
        if db.session.execute(code_query).scalar_one_or_none() is not None:
            return None, "A customer with this code already exists."

    # Return the code for creates and editable fields only for updates.
    if customer_id is None:
        return {
            "code": code,
            "name": name,
            "status": status,
            "address": address,
            "notes": notes,
        }, None

    return {
        "name": name,
        "status": status,
        "address": address,
        "notes": notes,
    }, None


#=========================== CUSTOMERS: CREATE ===========================
@customers_bp.post("/customers")
@login_required
def create_customer():
    # Validate and extract submitted customer values.
    values, error = read_customer_form()

    if error:
        flash(error, "danger")
        return redirect(url_for("customers.list_customers"))

    # Construct a customer model from the validated values.
    customer = models.Customer(**values)

    try:
        # Insert and refresh the customer so audit values include generated fields.
        db.session.add(customer)
        db.session.flush()
        db.session.refresh(customer)

        # Record the CREATE action in the audit log.
        write_audit_log(
            db=db,
            record=customer,
            action="CREATE",
            new_values=snapshot_record(customer),
            change_summary=f"Customer {customer.code} created",
        )

        # Commit the customer and audit row together.
        db.session.commit()
        flash("Customer added successfully.", "success")
    except IntegrityError:
        # Roll back both operations when database constraints fail.
        db.session.rollback()
        flash(
            "Could not save the customer. Check that the customer code is unique.",
            "danger",
        )

    return redirect(url_for("customers.list_customers"))


#=========================== CUSTOMERS: EDIT ===========================
@customers_bp.post("/customers/<int:customer_id>/edit")
@login_required
def edit_customer(customer_id):
    # Load the customer or return 404 if it does not exist.
    customer = db.session.get(models.Customer, customer_id)
    if customer is None:
        abort(404)

    # Validate and extract submitted values.
    values, error = read_customer_form(customer_id=customer_id)

    if error:
        flash(error, "danger")
        return redirect(url_for("customers.list_customers"))

    # Compare editable fields before touching updated_at or writing an audit row.
    changed_values = {
        field: value
        for field, value in values.items()
        if getattr(customer, field) != value
    }

    # Stop without changing anything when no editable field is different.
    if not changed_values:
        flash("No changes were made.", "info")
        return redirect(url_for("customers.list_customers"))

    # Capture the original values for the audit log.
    old_values = snapshot_record(customer)

    # Apply only the fields that changed.
    for field, value in changed_values.items():
        setattr(customer, field, value)

    # Refresh updated_at because the table default only applies on insert.
    customer.updated_at = db.func.current_timestamp()

    try:
        # Flush and refresh so audit values include the final database state.
        db.session.flush()
        db.session.refresh(customer)

        # Record the UPDATE action with old and new values.
        write_audit_log(
            db=db,
            record=customer,
            action="UPDATE",
            old_values=old_values,
            new_values=snapshot_record(customer),
            change_summary=f"Customer {customer.code} updated",
        )

        # Commit the customer update and audit row together.
        db.session.commit()
        flash("Customer updated successfully.", "success")
    except IntegrityError:
        # Roll back all changes when database constraints fail.
        db.session.rollback()
        flash(
            "Could not update the customer. Check that the customer code is unique.",
            "danger",
        )

    return redirect(url_for("customers.list_customers"))


#=========================== CUSTOMERS: DELETE ===========================
@customers_bp.post("/customers/<int:customer_id>/delete")
@login_required
def delete_customer(customer_id):
    # Load the customer or return 404 if it does not exist.
    customer = db.session.get(models.Customer, customer_id)
    if customer is None:
        abort(404)

    # Check whether the customer is referenced by an existing purchase order.
    has_purchase_orders = db.session.execute(
        db.select(models.PurchaseOrder.id)
        .where(models.PurchaseOrder.customer_id == customer_id)
        .limit(1)
    ).scalar_one_or_none()

    if has_purchase_orders is not None:
        flash(
            "This customer has purchase orders and cannot be deleted.",
            "danger",
        )
        return redirect(url_for("customers.list_customers"))

    # Capture original values for the DELETE audit row.
    old_values = snapshot_record(customer)

    try:
        # Remove the customer and record the DELETE action.
        db.session.delete(customer)

        write_audit_log(
            db=db,
            record=customer,
            action="DELETE",
            old_values=old_values,
            change_summary=f"Customer {customer.code} deleted",
        )

        # Commit the deletion and audit row together.
        db.session.commit()
        flash("Customer deleted successfully.", "success")
    except IntegrityError:
        # Roll back the deletion if it conflicts with database references.
        db.session.rollback()
        flash(
            "This customer is referenced by another record and cannot be deleted.",
            "danger",
        )

    return redirect(url_for("customers.list_customers"))
