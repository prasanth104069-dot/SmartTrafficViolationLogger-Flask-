"""
seed_data.py — populate traffic.db with sample test records
using Tamil Nadu style vehicle number plates.

Run from the project folder (after `flask --app app init-db`):
    python seed_data.py

Safe to re-run: it skips insertion if the DB already has data,
so you won't get duplicates on every run. Pass --force to wipe
existing Violation rows and reseed.
"""

import random
import sys
from datetime import date, timedelta

from app import app, db, Violation, generate_qr_for_violation, VIOLATION_TYPES

random.seed(42)  # reproducible output

# ----------------------------------------------------------------------
# Tamil Nadu RTO codes (district office codes) used to build plates like
# TN09AB1234. A handful of real, well-known TN RTO codes are used here.
# ----------------------------------------------------------------------
TN_RTO_CODES = {
    "01": "Chennai Central",
    "02": "Chennai North",
    "07": "Chennai South",
    "09": "Chennai (Ambattur)",
    "10": "Chennai (Koyambedu)",
    "11": "Chennai (Sholinganallur)",
    "20": "Vellore",
    "22": "Salem",
    "23": "Namakkal",
    "28": "Coimbatore (North)",
    "37": "Coimbatore (South)",
    "38": "Tiruppur",
    "45": "Madurai (North)",
    "58": "Madurai (South)",
    "48": "Trichy",
    "49": "Perambalur",
    "67": "Thanjavur",
    "72": "Tirunelveli",
    "75": "Kanyakumari",
    "31": "Erode",
    "33": "Dindigul",
}

LOCATIONS = [
    "Anna Salai, Chennai",
    "OMR IT Corridor, Chennai",
    "Koyambedu Junction, Chennai",
    "Avinashi Road, Coimbatore",
    "Race Course, Coimbatore",
    "Bypass Road, Madurai",
    "Anna Nagar, Madurai",
    "Trichy Central Bus Stand",
    "Salem New Bus Stand",
    "Vellore Fort Junction",
    "Erode Bharathi Park",
    "Thanjavur Big Temple Road",
    "Tirunelveli Junction",
    "Dindigul Rock Fort Road",
    "Tiruppur Railway Station Road",
    "Nagercoil Bypass",
    "ECR Road, Kanyakumari",
]

FINE_BY_TYPE = {
    "No Helmet": 500,
    "Overspeeding": 1000,
    "Signal Jump": 1000,
    "No Seatbelt": 500,
    "Wrong Parking": 300,
    "Drunk Driving": 5000,
    "No License": 2000,
    "Triple Riding": 700,
    "Using Phone While Driving": 1000,
    "Other": 400,
}


def random_plate(rto_code):
    letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
    number = random.randint(1, 9999)
    return f"TN{rto_code}{letters}{number:04d}"


def build_sample_rows(count=25):
    rto_codes = list(TN_RTO_CODES.keys())
    rows = []
    used_plates = set()

    # First, create a handful of REPEAT vehicles (2 violations each) so
    # the "Check Vehicle" lookup has something interesting to show.
    repeat_plate_count = 5
    for _ in range(repeat_plate_count):
        rto = random.choice(rto_codes)
        plate = random_plate(rto)
        while plate in used_plates:
            plate = random_plate(rto)
        used_plates.add(plate)
        for _ in range(2):
            rows.append(make_row(plate))

    # Fill the rest with unique single-violation vehicles.
    while len(rows) < count:
        rto = random.choice(rto_codes)
        plate = random_plate(rto)
        while plate in used_plates:
            plate = random_plate(rto)
        used_plates.add(plate)
        rows.append(make_row(plate))

    return rows[:count]


def make_row(plate):
    vtype = random.choice(VIOLATION_TYPES)
    base_fine = FINE_BY_TYPE.get(vtype, 500)
    fine = base_fine + random.choice([0, 0, 100, -100])
    days_ago = random.randint(0, 120)
    vdate = date.today() - timedelta(days=days_ago)
    status = random.choice(["Unpaid", "Unpaid", "Paid"])  # more unpaid than paid
    location = random.choice(LOCATIONS)
    return {
        "vehicle_number": plate,
        "violation_type": vtype,
        "location": location,
        "violation_date": vdate,
        "fine_amount": float(fine),
        "status": status,
    }


def main():
    force = "--force" in sys.argv

    with app.test_request_context(base_url="http://127.0.0.1:5000"):
        db.create_all()

        existing = Violation.query.count()
        if existing and not force:
            print(f"traffic.db already has {existing} violation(s). "
                  f"Run 'python seed_data.py --force' to wipe and reseed.")
            return

        if force and existing:
            Violation.query.delete()
            db.session.commit()
            print(f"Cleared {existing} existing violation(s).")

        rows = build_sample_rows(count=25)

        created = []
        for row in rows:
            v = Violation(**row)
            db.session.add(v)
            db.session.flush()  # assign v.id / default challan_id before QR gen
            generate_qr_for_violation(v)
            created.append(v)

        db.session.commit()

        print(f"Seeded {len(created)} sample violations with Tamil Nadu plates:\n")
        for v in created:
            print(f"  {v.vehicle_number:<14} {v.violation_type:<26} "
                  f"₹{v.fine_amount:<8.2f} {v.status:<7} {v.violation_date}")

        unique_plates = len({v.vehicle_number for v in created})
        print(f"\nTotal records: {len(created)}  |  Unique vehicle numbers: {unique_plates}")
        print("Try searching one of the repeated plates above on the homepage "
              "'Check Vehicle' box to see multiple violations for one vehicle.")


if __name__ == "__main__":
    main()