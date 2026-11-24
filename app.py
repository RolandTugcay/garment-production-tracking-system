import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import or_, text

from src.extensions import database_url, db, login_manager
from src.routes.worker_classes import worker_classes_bp
import src.models as models

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

app.register_blueprint(worker_classes_bp)

#=========================== LOGIN ===========================
@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(models.User, int(user_id))
    except (TypeError, ValueError):
        return None
#=========================== LOGIN VALIDATION ===========================
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

#=========================== /HEALTH/DB ===========================
@app.get("/health/db")
def check_database():
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return jsonify(status="connected"), 200

    except Exception:
        app.logger.exception("Database health failed")
        return jsonify(status="error", message="Database connection failed"), 503

@app.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)

