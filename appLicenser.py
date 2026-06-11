from flask import (
    Flask, jsonify, request, session,
    redirect, url_for, render_template
)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import inspect, text
<<<<<<< HEAD
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from functools import wraps
=======
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from cryptography.fernet import Fernet
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
import os

# ================= APP INIT =================
app = Flask(__name__)

<<<<<<< HEAD
# ================= DATABASE (POSTGRES + SQLITE FALLBACK) =================
uri = os.getenv("DATABASE_URL")

if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri or "sqlite:///licenser.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

=======
# ================= DATABASE =================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///licenser.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
db = SQLAlchemy(app)

# ================= SECURITY =================
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
API_KEY = os.getenv("API_KEY", "dev-secret")

<<<<<<< HEAD
# ================= FERNET =================
=======
# ================= FERNET KEY (FIXED FOR RENDER) =================
# IMPORTANT: MUST be set in Render environment variables
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
FERNET_KEY = os.getenv("FERNET_KEY")

if not FERNET_KEY:
    raise Exception("FERNET_KEY is missing in environment variables")

cipher = Fernet(FERNET_KEY.encode())

<<<<<<< HEAD

=======
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
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
<<<<<<< HEAD
            col["name"] for col in inspector.get_columns(table_name)
=======
            col["name"]
            for col in inspector.get_columns(table_name)
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
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
<<<<<<< HEAD
=======

>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
                print(f"[SCHEMA] Added {table_name}.{column.name}")

            except Exception as e:
                print(f"[SCHEMA ERROR] {table_name}.{column.name}: {e}")

    db.session.commit()

<<<<<<< HEAD

=======
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
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


class LicenserUser(db.Model):
    __tablename__ = "licenser_user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
<<<<<<< HEAD

    role = db.Column(db.String(20), default="licenser")
=======
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

<<<<<<< HEAD

=======
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
# ================= ENCRYPTION =================
def encrypt_text(text):
    return cipher.encrypt(text.encode()).decode()

def decrypt_text(text):
    return cipher.decrypt(text.encode()).decode()

<<<<<<< HEAD

=======
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
# ================= DEFAULT USER =================
def ensure_licenser_created():
    licenser = LicenserUser.query.first()

    if not licenser:
<<<<<<< HEAD
        licenser = LicenserUser(username="licenser", role="admin")
=======
        licenser = LicenserUser(username="licenser")
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
        licenser.set_password("ChangeMe123")

        db.session.add(licenser)
        db.session.commit()

<<<<<<< HEAD
        print("[INIT] Default admin account created")


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


# ================= API =================
@app.route("/request-update", methods=["POST"])
def request_update():

    if request.headers.get("X-API-KEY") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
=======
        print("[LICENSER] Default account created")

# ================= API =================
@app.route("/request-update", methods=["POST"])
def request_update():
    api_key = request.headers.get("X-API-KEY")

    if api_key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92

    req = UpdateRequest(
        admin_name=data["admin_name"],
        admin_email=data.get("admin_email"),
        reason=data["reason"]
    )

    db.session.add(req)
    db.session.commit()

    return jsonify({"success": True, "request_id": req.id})


@app.route("/requests")
@admin_required
def requests_list():
    all_requests = UpdateRequest.query.all()

    return jsonify([
        {
            "id": r.id,
            "admin_name": r.admin_name,
            "reason": r.reason,
            "status": r.status
        }
        for r in all_requests
    ])


@app.route("/approve/<int:req_id>", methods=["POST"])
<<<<<<< HEAD
@admin_required
def approve_request(req_id):

    req = UpdateRequest.query.get_or_404(req_id)
    data = request.get_json() or {}
=======
def approve_request(req_id):

    if not session.get("licenser_id"):
        return jsonify({"error": "login required"}), 403

    req = UpdateRequest.query.get_or_404(req_id)
    data = request.json
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92

    req.licenser_email = data["licenser_email"]
    req.licenser_password = encrypt_text(data["licenser_password"])
    req.status = "approved"

    db.session.commit()

    return jsonify({"success": True})


@app.route("/get-update/<int:req_id>")
def get_update(req_id):

    req = UpdateRequest.query.get_or_404(req_id)

    if req.status != "approved":
        return jsonify({"status": req.status})

    return jsonify({
        "status": "approved",
        "licenser_email": req.licenser_email,
        "licenser_password": decrypt_text(req.licenser_password)
    })

<<<<<<< HEAD

=======
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
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


<<<<<<< HEAD
# ================= PASSWORD CHANGE =================
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


=======
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
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

# ================= INIT (RENDER SAFE) =================
with app.app_context():
    sync_database_schema()
    ensure_licenser_created()

<<<<<<< HEAD
# ================= INIT =================
with app.app_context():
    sync_database_schema()
    ensure_licenser_created()


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
=======
# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
>>>>>>> 8f15c204a39791ee8aa383f3b13564aaa8d25a92
