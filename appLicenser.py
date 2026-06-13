from flask import (
    Flask, jsonify, request, session,
    redirect, url_for, render_template
)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from functools import wraps
import os

# ================= APP INIT =================
app = Flask(__name__)

# ================= DATABASE =================
uri = os.getenv("DATABASE_URL")

if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri or "sqlite:///licenser.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= SECURITY =================
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
API_KEY = os.getenv("API_KEY", "dev-secret")

# ================= FERNET =================
FERNET_KEY = os.getenv("FERNET_KEY")

if not FERNET_KEY:
    raise Exception("FERNET_KEY is missing in environment variables")

cipher = Fernet(FERNET_KEY.encode())

# ================= SCHEMA SYNC =================
def sync_database_schema():
    db.create_all()

    inspector = inspect(db.engine)

    for model in db.Model.__subclasses__():

        if not hasattr(model, "__table__"):
            continue

        table_name = model.__tablename__

        if table_name not in inspector.get_table_names():
            continue

        existing_columns = {
            col["name"] for col in inspector.get_columns(table_name)
        }

        for column in model.__table__.columns:

            if column.name in existing_columns:
                continue

            try:
                col_type = column.type.compile(db.engine.dialect)

                sql = f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column.name} {col_type}
                """

                db.session.execute(text(sql))
                print(f"[SCHEMA] Added {table_name}.{column.name}")

            except Exception as e:
                print(f"[SCHEMA ERROR] {table_name}.{column.name}: {e}")

    db.session.commit()


# ================= MODELS =================
class UpdateRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    admin_name = db.Column(db.String(100), nullable=False)
    admin_email = db.Column(db.String(120))
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default="pending")

    licenser_email = db.Column(db.String(120))
    licenser_password = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# NEW: API LOG TABLE
class APILog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(120))
    method = db.Column(db.String(10))
    payload = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class LicenserUser(db.Model):
    __tablename__ = "licenser_user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="licenser")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ================= ENCRYPTION =================
def encrypt_text(text):
    return cipher.encrypt(text.encode()).decode()

def decrypt_text(text):
    return cipher.decrypt(text.encode()).decode()


# ================= LOGGING HELPER =================
def log_api(endpoint):
    try:
        log = APILog(
            endpoint=endpoint,
            method=request.method,
            payload=str(request.get_json() or {})
        )
        db.session.add(log)
        db.session.commit()
    except:
        pass


# ================= ADMIN DECORATOR =================
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        user_id = session.get("licenser_id")
        if not user_id:
            return redirect(url_for("licenser_login"))

        user = LicenserUser.query.get(user_id)

        if not user or user.role != "admin":
            return jsonify({"error": "admin only"}), 403

        return f(*args, **kwargs)

    return wrapper


# ================= DEFAULT USER =================
def ensure_licenser_created():
    user = LicenserUser.query.first()

    if not user:
        user = LicenserUser(username="licenser", role="admin")
        user.set_password("ChangeMe123")

        db.session.add(user)
        db.session.commit()

        print("[INIT] Default admin account created")


# ================= API =================
@app.route("/request-update", methods=["POST"])
def request_update():

    if request.headers.get("X-API-KEY") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    req = UpdateRequest(
        admin_name=data["admin_name"],
        admin_email=data.get("admin_email"),
        reason=data["reason"]
    )

    db.session.add(req)
    db.session.commit()

    log_api("/request-update")

    return jsonify({"success": True, "request_id": req.id})

@app.route("/api/requests")
@admin_required
def requests_api():

    return jsonify([
        {
            "id": r.id,
            "admin_name": r.admin_name,
            "reason": r.reason,
            "status": r.status
        }
        for r in UpdateRequest.query.all()
    ])

@app.route("/requests")
@admin_required
def requests_list():

    log_api("/requests")

    requests_data = UpdateRequest.query.order_by(
        UpdateRequest.id.desc()
    ).all()

    return render_template(
        "requests.html",
        requests_list=requests_data
    )


@app.route("/approve/<int:req_id>", methods=["POST"])
@admin_required
def approve_request(req_id):

    req = UpdateRequest.query.get_or_404(req_id)
    data = request.get_json() or {}

    req.licenser_email = data["licenser_email"]
    req.licenser_password = encrypt_text(data["licenser_password"])
    req.status = "approved"

    db.session.commit()

    log_api("/approve")

    return jsonify({"success": True})


@app.route("/get-update/<int:req_id>")
def get_update(req_id):

    req = UpdateRequest.query.get_or_404(req_id)

    log_api("/get-update")

    if req.status != "approved":
        return jsonify({"status": req.status})

    return jsonify({
        "status": "approved",
        "licenser_email": req.licenser_email,
        "licenser_password": decrypt_text(req.licenser_password)
    })


# ================= API LOGS DASHBOARD (NEW) =================
@app.route("/api-logs")
@admin_required
def api_logs():

    logs = APILog.query.order_by(APILog.timestamp.desc()).all()

    return render_template("api_logs.html", logs=logs)


# ================= AUTH =================
@app.route("/")
def home():
    if session.get("licenser_id"):
        return redirect(url_for("licenser_dashboard"))
    return redirect(url_for("licenser_login"))


@app.route("/licenser/login", methods=["GET", "POST"])
def licenser_login():

    if request.method == "POST":

        user = LicenserUser.query.filter_by(
            username=request.form["username"]
        ).first()

        if user and user.check_password(request.form["password"]):
            session["licenser_id"] = user.id
            return redirect(url_for("licenser_dashboard"))

        return render_template("licenser_login.html", error="Invalid login")

    return render_template("licenser_login.html")


@app.route("/licenser/change-password", methods=["GET", "POST"])
def change_password():

    if not session.get("licenser_id"):
        return redirect(url_for("licenser_login"))

    user = LicenserUser.query.get(session["licenser_id"])

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]

        if not user.check_password(current_password):
            return render_template(
                "change_password.html",
                error="Current password is incorrect"
            )

        user.set_password(new_password)
        db.session.commit()

        return render_template(
            "change_password.html",
            success="Password updated successfully"
        )

    return render_template("change_password.html")


@app.route("/licenser/logout")
def licenser_logout():
    session.clear()
    return redirect(url_for("licenser_login"))


@app.route("/licenser/dashboard")
def licenser_dashboard():

    if not session.get("licenser_id"):
        return redirect(url_for("licenser_login"))

    requests_list = UpdateRequest.query.order_by(
        UpdateRequest.id.desc()
    ).all()

    return render_template(
        "licenser_dashboard.html",
        requests_list=requests_list
    )


@app.route("/licenser/approve/<int:req_id>", methods=["GET", "POST"])
def approve_page(req_id):

    if not session.get("licenser_id"):
        return redirect(url_for("licenser_login"))

    req = UpdateRequest.query.get_or_404(req_id)

    if request.method == "POST":

        req.licenser_email = request.form["licenser_email"]
        req.licenser_password = encrypt_text(
            request.form["licenser_password"]
        )
        req.status = "approved"

        db.session.commit()

        return redirect(url_for("licenser_dashboard"))

    return render_template("approve_page.html", req=req)


# ================= INIT =================
with app.app_context():
    sync_database_schema()
    ensure_licenser_created()


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
