from src.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import text, Computed, BigInteger, Identity, Index, UniqueConstraint

#===================== AUDIT_LOGS =====================
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    __table_args__ = (
        Index(
            "ix_audit_logs_record_history",
            "table_name",
            "record_id",
            "action_date",
        ),
        Index(
            "ix_audit_logs_action_user_date",
            "action_by_user_id",
            "action_date",
        ),
        {"schema": "public"},
    )

    id = db.Column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )

    action_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("public.users.id"),
        nullable=True,
    )

    table_name = db.Column(db.String(100), nullable=False)
    record_id = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    action_date = db.Column(
        db.DateTime(timezone=False),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )

    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    change_summary = db.Column(db.String(500))
    request_id = db.Column(db.String(100))

#===================== USERS =====================
class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    worker_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "public.workers.id",
            onupdate="NO ACTION",
            ondelete="NO ACTION",
        ),
        unique=False,
        nullable=True,
    )

    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False,server_default="Active")

    created_at = db.Column(db.DateTime(timezone=False),nullable=False,server_default=db.func.current_timestamp(),)
    updated_at = db.Column(db.DateTime(timezone=False),nullable=False,server_default=db.func.current_timestamp(),)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

#===================== WORKER_CLASSES =====================
class WorkerClass(db.Model):
    __tablename__ = "worker_classes"
    __table_args__ = {"schema": "public"}

    id = db.Column(db.Integer,Identity(always=False),primary_key=True,)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, server_default='Active')

    created_at = db.Column(db.DateTime(timezone=False),nullable=False,server_default=db.func.current_timestamp(),)
    updated_at = db.Column(db.DateTime(timezone=False),nullable=False,server_default=db.func.current_timestamp(),)

    def __repr__(self):
        return f"<WorkerClass {self.code}: {self.name}>"

#===================== WORKERS =====================
class Worker(db.Model):
    __tablename__ = "workers"
    __table_args__ = {"schema": "public"}

    id = db.Column(
        db.Integer,
        Identity(always=False),
        primary_key=True,
    )

    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(254), unique=True)
    hire_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, server_default='Active')
    notes = db.Column(db.Text)
    address = db.Column(db.String(500))

    created_at = db.Column(
        db.DateTime(timezone=False),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=False),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )

    code = db.Column(
        db.String(20),
        Computed("'W-' || lpad(id::text, 4, '0')", persisted=True),
        nullable=False,
        unique=True,
    )

    worker_class_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "public.worker_classes.id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    def __repr__(self):
        return f"<Worker {self.code}: {self.first_name} {self.last_name}>"

#===================== CUSTOMERS =====================
class Customer(db.Model):
    __tablename__ = "customers"
    __table_args__ = {"schema": "public"}

    id = db.Column(
        db.Integer,
        Identity(always=False),
        primary_key=True,
    )

    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(150), nullable=False)
    status = db.Column(
        db.String(20),
        nullable=False,
        server_default="Active",
    )
    address = db.Column(db.Text)
    notes = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime(timezone=False),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=False),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )

    def __repr__(self):
        return f"<Customer {self.code}: {self.name}>"

#===================== CUSTOMER CONTACTS =====================
class CustomerContact(db.Model):
    __tablename__ = "customer_contacts"

    __table_args__ = (
        Index(
            "uq_customer_contacts_one_primary_per_customer",
            "id",
            unique=True,
            postgresql_where=text("is_primary = 'Yes'"),
        ),
        {"schema": "public"},
    )

    id = db.Column(
        db.Integer,
        Identity(always=False),
        primary_key=True,
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "public.customers.id",
            name="fk_customer_contacts_customer",
            onupdate="NO ACTION",
            ondelete="NO ACTION",
        ),
        nullable=False,
    )

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100))
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(254))

    created_at = db.Column(
        db.DateTime(timezone=False),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=False),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
    is_primary = db.Column(
        db.String(20),
        nullable=False,
        server_default='No',
    )

    def __repr__(self):
        return (
            f"<CustomerContact {self.id}: "
            f"{self.first_name} {self.last_name}>"
        )

#===================== PURCHASE ORDER =====================
class PurchaseOrder(db.Model):
    __tablename__ = "purchase_order"

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "po_number",
            name="uq_purchase_order_customer_code",
        ),
        {"schema": "public"},
    )

    id = db.Column(
        db.Integer,
        Identity(always=False),
        primary_key=True,
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "public.customers.id",
            name="fk_purchase_order_customer",
            onupdate="NO ACTION",
            ondelete="NO ACTION",
        ),
        nullable=False,
    )

    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "public.users.id",
            name="fk_purchase_order_created_by",
            onupdate="NO ACTION",
            ondelete="NO ACTION",
        ),
        nullable=False,
    )

    po_number = db.Column(db.String(50), nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.String(30),
        nullable=False,
        server_default="received",
    )
    notes = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime(timezone=False),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=False),
        nullable=False,
        server_default=db.func.current_timestamp(),
    )

    def __repr__(self):
        return f"<PurchaseOrder {self.po_number}>"