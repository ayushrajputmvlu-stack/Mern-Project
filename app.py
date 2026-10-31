import os
from datetime import date
from functools import wraps

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Enable this only when the site is served over HTTPS:
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
)

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3307")),
        user=os.getenv("DB_USER", "health_app"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "community_health_db"),
        charset="utf8mb4",
    )

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "worker_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "worker_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped

def csrf_token():
    # Simple session-bound token for this small learning project.
    import secrets
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]

app.jinja_env.globals["csrf_token"] = csrf_token

@app.before_request
def check_csrf():
    if request.method == "POST":
        supplied = request.form.get("_csrf_token", "")
        expected = session.get("_csrf_token", "")
        import hmac
        if not supplied or not expected or not hmac.compare_digest(supplied, expected):
            flash("Your form expired. Please try again.", "danger")
            return redirect(request.referrer or url_for("dashboard"))

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "worker_id" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if "worker_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = None
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, full_name, email, password_hash, role FROM workers WHERE email=%s AND is_active=1", (email,))
            worker = cur.fetchone()
            cur.close()
            if worker and check_password_hash(worker["password_hash"], password):
                session.clear()
                session["worker_id"] = worker["id"]
                session["worker_name"] = worker["full_name"]
                session["role"] = worker["role"]
                flash("Welcome back!", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "danger")
        except mysql.connector.Error:
            app.logger.exception("Database error during login")
            flash("Cannot connect to the database. Check your .env settings and run database.sql.", "danger")
        finally:
            if conn and conn.is_connected():
                conn.close()
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = None
    stats = {"people": 0, "pending": 0, "upcoming": 0, "recent": []}
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS total FROM people")
        stats["people"] = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM followups WHERE status='Pending'")
        stats["pending"] = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM followups WHERE status='Pending' AND followup_date >= CURDATE()")
        stats["upcoming"] = cur.fetchone()["total"]
        cur.execute("SELECT id, full_name, blood_group, created_at FROM people ORDER BY created_at DESC LIMIT 6")
        stats["recent"] = cur.fetchall()
        cur.close()
    except mysql.connector.Error:
        app.logger.exception("Database error loading dashboard")
        flash("Could not load dashboard data. Check your database setup.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template("dashboard.html", stats=stats)

def clean_person_form(form):
    name = form.get("full_name", "").strip()
    if not name:
        return None, "Full name is required."
    blood_group = form.get("blood_group", "").strip() or None
    allowed_blood = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"}
    if blood_group and blood_group not in allowed_blood:
        return None, "Select a valid blood group."
    dob = form.get("date_of_birth", "").strip() or None
    if dob:
        try:
            date.fromisoformat(dob)
        except ValueError:
            return None, "Enter a valid date of birth."
    phone = form.get("phone", "").strip() or None
    if phone and len(phone) > 20:
        return None, "Phone number is too long."
    return {
        "full_name": name,
        "date_of_birth": dob,
        "gender": form.get("gender", "").strip() or None,
        "phone": phone,
        "address": form.get("address", "").strip() or None,
        "blood_group": blood_group,
        "allergies": form.get("allergies", "").strip() or None,
        "health_issues": form.get("health_issues", "").strip() or None,
        "emergency_contact": form.get("emergency_contact", "").strip() or None,
    }, None

PERSON_FIELDS = ("full_name", "date_of_birth", "gender", "phone", "address",
                 "blood_group", "allergies", "health_issues", "emergency_contact")

@app.route("/people")
@login_required
def people():
    q = request.args.get("q", "").strip()
    conn = None
    records = []
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        if q:
            like = f"%{q}%"
            if q.isdigit():
                cur.execute("""SELECT id, full_name, date_of_birth, gender, phone, blood_group
                               FROM people WHERE full_name LIKE %s OR phone LIKE %s OR id=%s
                               ORDER BY full_name LIMIT 200""", (like, like, int(q)))
            else:
                cur.execute("""SELECT id, full_name, date_of_birth, gender, phone, blood_group
                               FROM people WHERE full_name LIKE %s OR phone LIKE %s
                               ORDER BY full_name LIMIT 200""", (like, like))
        else:
            cur.execute("""SELECT id, full_name, date_of_birth, gender, phone, blood_group
                           FROM people ORDER BY created_at DESC LIMIT 200""")
        records = cur.fetchall()
        cur.close()
    except mysql.connector.Error:
        app.logger.exception("Database error listing people")
        flash("Could not load records. Check your database setup.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template("people.html", records=records, q=q)

@app.route("/people/add", methods=["GET", "POST"])
@login_required
def add_person():
    if request.method == "POST":
        data, error = clean_person_form(request.form)
        if error:
            flash(error, "danger")
            return render_template("person_form.html", person=request.form, page_title="Register a person", mode="add")
        conn = None
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""INSERT INTO people
                (full_name, date_of_birth, gender, phone, address, blood_group, allergies,
                 health_issues, emergency_contact, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                tuple(data[k] for k in PERSON_FIELDS) + (session["worker_id"],))
            new_id = cur.lastrowid
            conn.commit()
            cur.close()
            flash(f"Record #{new_id} was saved.", "success")
            return redirect(url_for("person_detail", person_id=new_id))
        except mysql.connector.Error:
            if conn:
                conn.rollback()
            app.logger.exception("Database error adding person")
            flash("Could not save the record. Check database connection.", "danger")
        finally:
            if conn and conn.is_connected():
                conn.close()
        return render_template("person_form.html", person=request.form, page_title="Register a person", mode="add")
    return render_template("person_form.html", person={}, page_title="Register a person", mode="add")

@app.route("/people/<int:person_id>")
@login_required
def person_detail(person_id):
    conn = None
    person = None
    followups = []
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM people WHERE id=%s", (person_id,))
        person = cur.fetchone()
        if person:
            cur.execute("SELECT * FROM followups WHERE person_id=%s ORDER BY followup_date DESC", (person_id,))
            followups = cur.fetchall()
        cur.close()
    except mysql.connector.Error:
        app.logger.exception("Database error opening person")
        flash("Could not open this record.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    if not person:
        flash("Record not found.", "warning")
        return redirect(url_for("people"))
    return render_template("person_detail.html", person=person, followups=followups)

@app.route("/people/<int:person_id>/edit", methods=["GET", "POST"])
@login_required
def edit_person(person_id):
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM people WHERE id=%s", (person_id,))
        person = cur.fetchone()
        cur.close()
        if not person:
            flash("Record not found.", "warning")
            return redirect(url_for("people"))
        if request.method == "POST":
            data, error = clean_person_form(request.form)
            if error:
                flash(error, "danger")
                return render_template("person_form.html", person=request.form, page_title="Edit record", mode="edit", person_id=person_id)
            cur = conn.cursor()
            cur.execute("""UPDATE people SET full_name=%s, date_of_birth=%s, gender=%s, phone=%s,
                address=%s, blood_group=%s, allergies=%s, health_issues=%s, emergency_contact=%s
                WHERE id=%s""", tuple(data[k] for k in PERSON_FIELDS) + (person_id,))
            conn.commit()
            cur.close()
            flash("Record updated successfully.", "success")
            return redirect(url_for("person_detail", person_id=person_id))
        return render_template("person_form.html", person=person, page_title="Edit record", mode="edit", person_id=person_id)
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        app.logger.exception("Database error editing person")
        flash("Could not load or update this record.", "danger")
        return redirect(url_for("people"))
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route("/people/<int:person_id>/followups/add", methods=["POST"])
@login_required
def add_followup(person_id):
    followup_date = request.form.get("followup_date", "").strip()
    reason = request.form.get("reason", "").strip()
    if not followup_date:
        flash("Follow-up date is required.", "danger")
        return redirect(url_for("person_detail", person_id=person_id))
    try:
        date.fromisoformat(followup_date)
    except ValueError:
        flash("Enter a valid follow-up date.", "danger")
        return redirect(url_for("person_detail", person_id=person_id))
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM people WHERE id=%s", (person_id,))
        if not cur.fetchone():
            flash("Record not found.", "warning")
            return redirect(url_for("people"))
        cur.execute("INSERT INTO followups (person_id, followup_date, reason) VALUES (%s,%s,%s)",
                    (person_id, followup_date, reason or None))
        conn.commit()
        cur.close()
        flash("Follow-up added.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        app.logger.exception("Database error adding follow-up")
        flash("Could not add follow-up.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return redirect(url_for("person_detail", person_id=person_id))

@app.route("/followups")
@login_required
def followups():
    conn = None
    rows = []
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT f.id, f.followup_date, f.reason, f.status, p.id AS person_id, p.full_name
                       FROM followups f JOIN people p ON p.id=f.person_id
                       ORDER BY (f.status='Pending') DESC, f.followup_date ASC LIMIT 300""")
        rows = cur.fetchall()
        cur.close()
    except mysql.connector.Error:
        app.logger.exception("Database error loading follow-ups")
        flash("Could not load follow-ups.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template("followups.html", rows=rows)

@app.route("/followups/<int:followup_id>/status", methods=["POST"])
@login_required
def update_followup_status(followup_id):
    status = request.form.get("status", "")
    if status not in {"Pending", "Completed", "Missed"}:
        flash("Invalid follow-up status.", "danger")
        return redirect(url_for("followups"))
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE followups SET status=%s WHERE id=%s", (status, followup_id))
        conn.commit()
        cur.close()
        flash("Follow-up status updated.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        app.logger.exception("Database error updating follow-up")
        flash("Could not update follow-up status.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return redirect(url_for("followups"))

if __name__ == "__main__":
    # For local development only; do not expose the Flask development server publicly.
    app.run(debug=True)
