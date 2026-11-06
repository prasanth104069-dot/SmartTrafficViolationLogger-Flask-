import os
import uuid
from datetime import datetime, date

import qrcode
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

# ----------------------------------------------------------------------
# App / Config
# ----------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "traffic.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

QR_FOLDER = os.path.join(BASE_DIR, "static", "qrcodes")
os.makedirs(QR_FOLDER, exist_ok=True)

db = SQLAlchemy(app)


# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------
class Violation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challan_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    vehicle_number = db.Column(db.String(20), nullable=False, index=True)
    violation_type = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    violation_date = db.Column(db.Date, nullable=False, default=date.today)
    fine_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(10), nullable=False, default="Unpaid")  # Unpaid / Paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    qr_path = db.Column(db.String(255))

    @property
    def public_url(self):
        return url_for("status_page", challan_id=self.challan_id, _external=True)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
VIOLATION_TYPES = [
    "No Helmet", "Overspeeding", "Signal Jump", "No Seatbelt",
    "Wrong Parking", "Drunk Driving", "No License", "Triple Riding",
    "Using Phone While Driving", "Other",
]


def generate_qr_for_violation(violation):
    """Create a QR code image pointing to the public status page."""
    img = qrcode.make(violation.public_url)
    filename = f"{violation.challan_id}.png"
    filepath = os.path.join(QR_FOLDER, filename)
    img.save(filepath)
    violation.qr_path = f"qrcodes/{filename}"
    db.session.commit()


# ----------------------------------------------------------------------
# Home + Public Vehicle Lookup
# ----------------------------------------------------------------------
@app.route("/")
def index():
    total = Violation.query.count()
    unpaid = Violation.query.filter_by(status="Unpaid").count()
    paid = Violation.query.filter_by(status="Paid").count()
    recent = Violation.query.order_by(Violation.created_at.desc()).limit(5).all()
    return render_template("index.html", total=total, unpaid=unpaid, paid=paid, recent=recent)


@app.route("/check")
def check_vehicle():
    """Public lookup: enter a vehicle number, see if it owes any fines."""
    vehicle = request.args.get("vehicle", "").strip().upper()
    violations = []
    searched = bool(vehicle)
    if vehicle:
        violations = (
            Violation.query.filter(Violation.vehicle_number == vehicle)
            .order_by(Violation.violation_date.desc())
            .all()
        )
    unpaid_total = sum(v.fine_amount for v in violations if v.status == "Unpaid")
    return render_template(
        "check_status.html",
        vehicle=vehicle,
        violations=violations,
        searched=searched,
        unpaid_total=unpaid_total,
    )


@app.route("/status/<challan_id>")
def status_page(challan_id):
    violation = Violation.query.filter_by(challan_id=challan_id).first_or_404()
    return render_template("status.html", v=violation)


# ----------------------------------------------------------------------
# Violation Management Routes (no login required)
# ----------------------------------------------------------------------
@app.route("/add", methods=["GET", "POST"])
def add_violation():
    if request.method == "POST":
        try:
            vehicle_number = request.form["vehicle_number"].strip().upper()
            violation_type = request.form["violation_type"]
            location = request.form["location"].strip()
            violation_date = datetime.strptime(request.form["violation_date"], "%Y-%m-%d").date()
            fine_amount = float(request.form["fine_amount"])
        except (KeyError, ValueError):
            flash("Please fill all fields correctly.", "danger")
            return render_template("add_violation.html", violation_types=VIOLATION_TYPES)

        violation = Violation(
            vehicle_number=vehicle_number,
            violation_type=violation_type,
            location=location,
            violation_date=violation_date,
            fine_amount=fine_amount,
            status="Unpaid",
        )
        db.session.add(violation)
        db.session.commit()

        generate_qr_for_violation(violation)

        flash("Violation recorded and challan generated.", "success")
        return redirect(url_for("challan", violation_id=violation.id))

    return render_template("add_violation.html", violation_types=VIOLATION_TYPES)


@app.route("/challan/<int:violation_id>")
def challan(violation_id):
    violation = Violation.query.get_or_404(violation_id)
    return render_template("challan.html", v=violation)


@app.route("/history")
def history():
    query = Violation.query

    vehicle = request.args.get("vehicle", "").strip()
    status = request.args.get("status", "")
    vtype = request.args.get("type", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    if vehicle:
        query = query.filter(Violation.vehicle_number.ilike(f"%{vehicle}%"))
    if status in ("Paid", "Unpaid"):
        query = query.filter_by(status=status)
    if vtype:
        query = query.filter_by(violation_type=vtype)
    if date_from:
        query = query.filter(Violation.violation_date >= datetime.strptime(date_from, "%Y-%m-%d").date())
    if date_to:
        query = query.filter(Violation.violation_date <= datetime.strptime(date_to, "%Y-%m-%d").date())

    violations = query.order_by(Violation.created_at.desc()).all()
    return render_template(
        "history.html",
        violations=violations,
        violation_types=VIOLATION_TYPES,
        filters=request.args,
    )


@app.route("/update-status/<int:violation_id>", methods=["POST"])
def update_status(violation_id):
    violation = Violation.query.get_or_404(violation_id)
    violation.status = "Paid" if violation.status == "Unpaid" else "Unpaid"
    db.session.commit()
    flash(f"Marked challan for {violation.vehicle_number} as {violation.status}.", "success")
    return redirect(request.referrer or url_for("history"))


# ----------------------------------------------------------------------
# CLI helper: create tables
# ----------------------------------------------------------------------
@app.cli.command("init-db")
def init_db():
    """Run with: flask --app app init-db"""
    db.create_all()
    print("Database initialized.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
