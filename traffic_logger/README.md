# Smart Traffic Violation Logger (Flask)

A Flask mini project for logging, tracking and managing traffic violations,
with QR-code enabled public challan status pages and a public vehicle-number
fine lookup. No login is required — anyone can add a violation, browse
history, or check a vehicle's status.

## Features
- Add violation records (vehicle number, type, location, date, fine)
- **Check Vehicle**: public search box — enter any vehicle number plate and
  see whether it has pending fines (and the total amount due)
- Auto-generated QR code per challan → public status page (for scanning the
  printed challan)
- Searchable / filterable violation history (vehicle, status, type, date range)
- Toggle Paid / Unpaid status
- Traffic-signal / automobile themed Bootstrap UI

## Setup

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize the database (creates traffic.db)
flask --app app init-db

# 4. Run the app
python app.py
```

The app runs at **http://127.0.0.1:5000**

## How it works

1. Go to **Add Violation** and fill in the details. Saving creates the
   record (status = Unpaid) and generates a QR code image, shown on the
   challan page.
2. The QR code points to `/status/<challan_id>` — a public page showing
   violation details and payment status for that specific challan.
3. On the **homepage**, anyone can type a vehicle number into the "Check
   Your Vehicle's Fine Status" box to see every violation on record for
   that plate, the total unpaid amount, and a Paid/Unpaid badge per entry.
4. Use **History** to filter by vehicle number, status, type, or date
   range, and to flip a record between Paid/Unpaid.

## Project structure

```
traffic_logger/
├── app.py                  # routes, models, QR generation
├── requirements.txt
├── traffic.db                # created after init-db
├── static/
│   ├── css/style.css         # traffic-signal themed styling
│   └── qrcodes/               # generated QR images
└── templates/
    ├── base.html
    ├── index.html             # home + vehicle lookup search box
    ├── check_status.html      # vehicle lookup results
    ├── add_violation.html
    ├── challan.html
    ├── history.html
    └── status.html            # per-challan public status (via QR)
```

## Notes / possible extensions
- This version has no authentication — anyone can add or edit records.
  If you need to restrict who can add violations later, reintroduce a
  login (Flask-Login) around the `/add`, `/history`, and
  `/update-status` routes only, leaving `/check` and `/status` public.
- Swap SQLite for PostgreSQL/MySQL by changing `SQLALCHEMY_DATABASE_URI`.
- Add pagination to the history table for large datasets.
- Send SMS/email notifications when a challan is created or paid.
