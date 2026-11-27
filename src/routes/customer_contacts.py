from flask import Blueprint, flash, jsonify, redirect, request, url_for
from flask_login import login_required
from sqlalchemy import String, cast, func, or_
from sqlalchemy.exc import IntegrityError

import src.models as models
from src.audit import snapshot_record, write_audit_log
from src.extensions import db

customer_contacts_bp = Blueprint("customer_contacts", __name__)


# Accept JSON payloads for the backend API, with form data as a fallback.
def request_data():
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload
    return request.form.to_dict()


# Send browser form submissions back to the customer page; keep JSON API errors as JSON.
def mutation_error(message, status_code, customer_id=None):
    if request.method == "POST" and not request.is_json:
        flash(message, "danger")
        return redirect(url_for("customers.list_customers", customer_id=customer_id))
    return jsonify(error=message), status_code


# Return a suitable success response for browser forms and JSON API clients.
def mutation_success(message, *, contact=None, status_code=200, customer_id=None):
    if request.method == "POST" and not request.is_json:
        flash(message, "success")
        return redirect(
            url_for("customers.list_customers", customer_id=customer_id)
        )

    response = {"message": message}

    if contact is not None:
        response["customer_contact"] = serialize_customer_contact(contact)

    if customer_id is not None:
        response["customer_id"] = customer_id

    return jsonify(response), status_code


# Convert a contact payload into validated model field values.
def read_contact_data(payload, *, existing=None, partial=False):
    values = {}

    if "customer_id" in payload:
        customer_id_value = payload.get("customer_id")
    elif existing is not None and partial:
        customer_id_value = existing.customer_id
    else:
        customer_id_value = None
    try:
        customer_id = int(customer_id_value) if customer_id_value not in (None, "") else None
    except (TypeError, ValueError):
        return None, "customer_id must be a valid integer."

    if customer_id is None:
        return None, "customer_id is required."
    if db.session.get(models.Customer, customer_id) is None:
        return None, "The selected customer does not exist."
    values["customer_id"] = customer_id

    string_fields = {
        "first_name": ("First name", 100, True),
        "last_name": ("Last name", 100, True),
        "position": ("Position", 100, False),
        "phone": ("Phone", 30, True),
        "email": ("Email", 254, False),
    }

    for field_name, (label, max_length, required) in string_fields.items():
        if field_name in payload:
            raw_value = payload.get(field_name)
        elif existing is not None and partial:
            raw_value = getattr(existing, field_name)
        else:
            raw_value = None

        if raw_value is not None and not isinstance(raw_value, str):
            return None, f"{label} must be text."

        value = raw_value.strip() if isinstance(raw_value, str) else None
        if value == "":
            value = None

        if required and value is None:
            return None, f"{label} is required."
        if value is not None and len(value) > max_length:
            return None, f"{label} must be {max_length} characters or fewer."

        values[field_name] = value

    if "is_primary" in payload:
        raw_primary = payload.get("is_primary")
        if isinstance(raw_primary, bool):
            is_primary = "Yes" if raw_primary else "No"
        elif raw_primary in (1, 0):
            is_primary = "Yes" if raw_primary == 1 else "No"
        elif isinstance(raw_primary, str):
            normalized = raw_primary.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                is_primary = "Yes"
            elif normalized in {"false", "0", "no", "off", ""}:
                is_primary = "No"
            else:
                return None, "is_primary must be Yes or No."
        else:
            return None, "is_primary must be Yes or No."
    elif existing is not None and partial:
        is_primary = existing.is_primary
    else:
        is_primary = "No"

    values["is_primary"] = is_primary
    return values, None


# Format one contact as JSON-safe values for API responses.
def serialize_customer_contact(contact):
    customer = db.session.get(models.Customer, contact.customer_id)
    return {
        "id": contact.id,
        "customer_id": contact.customer_id,
        "customer_name": customer.name if customer else None,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "position": contact.position,
        "phone": contact.phone,
        "email": contact.email,
        "is_primary": contact.is_primary,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
    }


# Clear any other primary contact for this customer and audit those updates.
def clear_other_primary_contacts(customer_id, *, exclude_contact_id=None):
    statement = db.select(models.CustomerContact).where(
        models.CustomerContact.customer_id == customer_id,
        models.CustomerContact.is_primary == "Yes",
    )
    if exclude_contact_id is not None:
        statement = statement.where(
            models.CustomerContact.id != exclude_contact_id
        )

    contacts = db.session.execute(statement).scalars().all()
    for contact in contacts:
        old_values = snapshot_record(contact)
        contact.is_primary = "No"
        contact.updated_at = func.current_timestamp()
        db.session.flush()
        db.session.refresh(contact)
        write_audit_log(
            db=db,
            record=contact,
            action="UPDATE",
            old_values=old_values,
            new_values=snapshot_record(contact),
            change_summary=(
                f"Customer contact {contact.id} unset as primary"
            ),
        )

#==================== CUSTOMER CONTACT: CREATE ====================
# Create a contact and its audit row in the same transaction.
@customer_contacts_bp.post("/customer-contacts")
@login_required
def create_customer_contact():
    values, error = read_contact_data(request_data())
    if error:
        return mutation_error(error, 400)

    contact = models.CustomerContact(**values)
    try:
        if contact.is_primary == "Yes":
            clear_other_primary_contacts(contact.customer_id)

        db.session.add(contact)
        db.session.flush()
        db.session.refresh(contact)
        write_audit_log(
            db=db,
            record=contact,
            action="CREATE",
            new_values=snapshot_record(contact),
            change_summary=f"Customer contact {contact.id} created",
        )
        db.session.commit()
        return mutation_success(
            message="Customer contact added successfully.",
            contact=contact,
            status_code=201,
            customer_id=contact.customer_id
        )
    
    except IntegrityError:
        db.session.rollback()
        return mutation_error(
            message="Could not create the customer contact.", 
            status_code=409,
            customer_id=contact.customer_id
        )

    


#==================== CUSTOMER CONTACT: EDIT ====================
# Update a contact; PATCH may send only changed fields, while PUT validates the full record.
@customer_contacts_bp.route(
    "/customer-contacts/<int:contact_id>/edit",
    methods=["POST"],
    endpoint="edit_customer_contact",
)
@customer_contacts_bp.route(
    "/customer-contacts/<int:contact_id>", methods=["PUT", "PATCH"]
)
@login_required
def update_customer_contact(contact_id):
    contact = db.session.get(models.CustomerContact, contact_id)
    if contact is None:
        return jsonify(error="Customer contact not found."), 404

    payload = request_data()
    form_submission = request.method == "POST" and not request.is_json
    partial = request.method in {"PATCH", "POST"}
    if request.method == "PUT":
        required_fields = ("customer_id", "first_name", "last_name", "phone")
        missing = [field for field in required_fields if field not in payload]
        if missing:
            return mutation_error("PUT requires all contact fields.", 400)

    values, error = read_contact_data(
        payload,
        existing=contact,
        partial=partial,
    )
    if error:
        return mutation_error(error, 400, customer_id=contact.customer_id)

    changed_values = {
        field: value
        for field, value in values.items()
        if getattr(contact, field) != value
    }
    if not changed_values:
        if form_submission:
            flash("No changes were made.", "info")
            return redirect(url_for("customers.list_customers"))
        return jsonify(
            message="No changes were made.",
            customer_contact=serialize_customer_contact(contact),
        ), 200

    old_values = snapshot_record(contact)
    try:
        for field, value in changed_values.items():
            setattr(contact, field, value)

        contact.updated_at = func.current_timestamp()
        if contact.is_primary == "Yes":
            clear_other_primary_contacts(
                contact.customer_id,
                exclude_contact_id=contact.id,
            )

        db.session.flush()
        db.session.refresh(contact)
        write_audit_log(
            db=db,
            record=contact,
            action="UPDATE",
            old_values=old_values,
            new_values=snapshot_record(contact),
            change_summary=f"Customer contact {contact.id} updated",
        )
        db.session.commit()
        return mutation_success(
            message="Customer contact updated successfully.", 
            contact=contact,
            customer_id=contact.customer_id)
    
    except IntegrityError:
        db.session.rollback()
        return mutation_error(
            message="Could not update the customer contact.", 
            status_code=409,
            customer_id=contact.customer_id)


#==================== CUSTOMER CONTACT: DELETE ====================
# Delete a contact and record the deletion in the audit log.
@customer_contacts_bp.route(
    "/customer-contacts/<int:contact_id>/delete",
    methods=["POST"],
    endpoint="delete_customer_contact_form",
)
@customer_contacts_bp.delete("/customer-contacts/<int:contact_id>")
@login_required
def delete_customer_contact(contact_id):
    contact = db.session.get(models.CustomerContact, contact_id)
    if contact is None:
        return mutation_error("Customer contact not found.", 404)

    old_values = snapshot_record(contact)
    try:
        db.session.delete(contact)
        write_audit_log(
            db=db,
            record=contact,
            action="DELETE",
            old_values=old_values,
            change_summary=f"Customer contact {contact.id} deleted",
        )
        db.session.commit()
        return mutation_success(
            message="Customer contact deleted successfully.",
            customer_id=contact.customer_id)
    except IntegrityError:
        db.session.rollback()
        return mutation_error(
            message="Could not delete the customer contact.", 
            status_code=409,
            customer_id=contact.customer_id)
