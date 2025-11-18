import random
from datetime import datetime, timedelta

from app import app, db
from models import Client, Case, User, ClientUser, Invoice, TimeEntry, Expense, Deadline, CalendarEvent, CaseType

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]

STREETS = [
    "Main St", "Oak Ave", "Pine Rd", "Maple Dr", "Cedar Ln", "Elm St", "Walnut St", "Sunset Blvd",
    "River Rd", "Highland Ave", "2nd St", "3rd St", "4th St"
]
CITIES = ["Springfield", "Fairview", "Riverton", "Franklin", "Greenville", "Bristol", "Georgetown"]
STATES = ["NY", "CA", "TX", "FL", "WA", "IL", "GA", "NC", "OH", "PA"]

CASE_TITLES = [
    "Slip and Fall at Grocery Store",
    "Rear-end Collision on Highway",
    "Employment Discrimination Claim",
    "Surgical Complication Follow-up",
    "Landlord-Tenant Lease Dispute",
]
CASE_DESCRIPTIONS = [
    "Client reports slipping on wet floor near produce section without warning signs.",
    "Client was rear-ended at an intersection; vehicle sustained heavy damage and neck pain reported.",
    "Client believes termination was due to age; negative review after new manager arrived.",
    "Post-op complications after gallbladder surgery; retained sponge suspected.",
    "Dispute over unpaid rent and lease terms with landlord.",
]
CASE_TYPES = [
    "Personal Injury - Premises Liability",
    "Car Accident / Auto Collision",
    "Employment Law - Age Discrimination",
    "Medical Malpractice",
    "Civil / Real Estate",
]

# Structured taxonomy for CaseType model (used by AI classification and automations)
CASE_TYPE_TAXONOMY = [
    {
        "key": "pi_slip_fall",
        "label": "Slip and Fall",
        "category": "Personal Injury",
        "subcategory": "Slip & Fall",
        "jurisdiction": "ON",
        "court_level_default": "Superior Court of Justice",
        "description": "Personal injury claim arising from a slip, trip, or fall incident.",
    },
    {
        "key": "pi_motor_vehicle",
        "label": "Motor Vehicle Accident",
        "category": "Personal Injury",
        "subcategory": "Car Accident",
        "jurisdiction": "ON",
        "court_level_default": "Superior Court of Justice",
        "description": "Personal injury claim arising from a motor vehicle collision.",
    },
    {
        "key": "employment_wrongful_dismissal",
        "label": "Wrongful Dismissal",
        "category": "Employment",
        "subcategory": "Termination",
        "jurisdiction": "ON",
        "court_level_default": "Superior Court of Justice",
        "description": "Employment dispute relating to alleged wrongful dismissal or constructive dismissal.",
    },
    {
        "key": "employment_discrimination",
        "label": "Employment Discrimination",
        "category": "Employment",
        "subcategory": "Human Rights",
        "jurisdiction": "ON",
        "court_level_default": "Human Rights Tribunal of Ontario",
        "description": "Workplace discrimination, harassment, or reprisal based on a protected ground.",
    },
    {
        "key": "med_mal_general",
        "label": "Medical Malpractice",
        "category": "Medical Malpractice",
        "subcategory": "General",
        "jurisdiction": "ON",
        "court_level_default": "Superior Court of Justice",
        "description": "Negligence claim against healthcare providers for substandard medical care.",
    },
]


def random_phone():
    return f"({random.randint(200, 989)}) {random.randint(200, 989)}-{random.randint(1000, 9999)}"


def random_address():
    num = random.randint(10, 9999)
    street = random.choice(STREETS)
    city = random.choice(CITIES)
    state = random.choice(STATES)
    zipc = random.randint(10010, 99999)
    return f"{num} {street}, {city}, {state} {zipc}"


def seed():
    with app.app_context():
        db.create_all()

        # Ensure a default admin user exists for created_by_id
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                role='admin',
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.flush()

        # Seed CaseType taxonomy (idempotent)
        for data in CASE_TYPE_TAXONOMY:
            key = data["key"]
            ct = CaseType.query.filter_by(key=key).first()
            if not ct:
                ct = CaseType(key=key)
                db.session.add(ct)
            ct.label = data.get("label", ct.label)
            ct.category = data.get("category", ct.category)
            ct.subcategory = data.get("subcategory", ct.subcategory)
            ct.jurisdiction = data.get("jurisdiction", ct.jurisdiction)
            ct.court_level_default = data.get("court_level_default", ct.court_level_default)
            ct.description = data.get("description", ct.description)
            if ct.active is None:
                ct.active = True

        existing = Client.query.count()
        clients = []
        if existing >= 30:
            # Reuse existing clients, do not return so we can seed portal/billing demo
            clients = Client.query.order_by(Client.id.asc()).limit(30).all()
            print(f"Clients already present ({existing}). Reusing first 30.")
        else:
            # Create 30 clients with unique emails
            for i in range(30):
                fn = FIRST_NAMES[i % len(FIRST_NAMES)]
                ln = LAST_NAMES[i % len(LAST_NAMES)]
                email = f"{fn.lower()}.{ln.lower()}{i+1}@example.com"
                c = Client(
                    first_name=fn,
                    last_name=ln,
                    email=email,
                    phone=random_phone(),
                    address=random_address(),
                )
                db.session.add(c)
                clients.append(c)
            db.session.flush()

        # clients list is populated above, either reused or newly created

        # Ensure there are sample cases for first 5 clients
        sample_cases = []
        for i in range(5):
            cl = clients[i]
            existing_case = Case.query.filter_by(client_id=cl.id).first()
            if existing_case:
                sample_cases.append((cl, existing_case))
            else:
                case = Case(
                    title=CASE_TITLES[i % len(CASE_TITLES)],
                    description=CASE_DESCRIPTIONS[i % len(CASE_DESCRIPTIONS)],
                    case_type=CASE_TYPES[i % len(CASE_TYPES)],
                    status='open',
                    priority=random.choice(['high', 'medium', 'low']),
                    client_id=cl.id,
                    created_by_id=admin.id,
                )
                db.session.add(case)
                sample_cases.append((cl, case))
        db.session.flush()

        # Create a ClientUser for the first client if not exists
        first_client = clients[0]
        if not ClientUser.query.filter_by(client_id=first_client.id).first():
            cu = ClientUser(
                client_id=first_client.id,
                email=f"{first_client.first_name.lower()}.{first_client.last_name.lower()}@portal.example.com",
                portal_access=True,
                email_verified=True,
            )
            cu.set_password('ClientPass!123')
            db.session.add(cu)

        # Create a demo Invoice with one TimeEntry and one Expense for the first case
        first_case = sample_cases[0][1]
        inv_num = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-001"
        invoice = Invoice.query.filter_by(invoice_number=inv_num).first()
        if not invoice:
            invoice = Invoice(
                invoice_number=inv_num,
                case_id=first_case.id,
                client_id=first_case.client_id,
                issue_date=datetime.utcnow().date(),
                due_date=(datetime.utcnow() + timedelta(days=30)).date(),
                total_amount=0.0
            )
            db.session.add(invoice)
            db.session.flush()

        # Time entry: 1.5 hours @ $200/hr
        existing_te = TimeEntry.query.filter_by(invoice_id=invoice.id).first()
        if not existing_te:
            te = TimeEntry(
                case_id=first_case.id,
                user_id=admin.id,
                date=datetime.utcnow().date(),
                duration_minutes=90,
                hourly_rate=200.0,
                amount=0.0,
                description='Initial consultation and file setup',
                activity_type='consultation',
                billable=True,
                invoice_id=invoice.id
            )
            te.calculate_amount()
            db.session.add(te)

        # Expense: $35 filing fee
        existing_ex = Expense.query.filter_by(invoice_id=invoice.id).first()
        if not existing_ex:
            ex = Expense(
                case_id=first_case.id,
                user_id=admin.id,
                date=datetime.utcnow().date(),
                description='Filing fee',
                category='filing_fees',
                amount=35.0,
                billable_to_client=True,
                invoice_id=invoice.id
            )
            db.session.add(ex)

        # Seed sample Deadlines for demo cases (idempotent)
        for (_cl, cse) in sample_cases:
            base = datetime.utcnow()
            demo_deadlines = [
                ("Evidence retention deadline", base + timedelta(days=7), 'evidence_retention', 'Preserve CCTV and incident reports'),
                ("Follow-up with adjuster", base + timedelta(days=14), 'adjuster_followup', 'Call insurance adjuster for status'),
                ("Statute check", base + timedelta(days=45), 'statute_check', 'Confirm applicable statute of limitations'),
            ]
            for name, due, source, notes in demo_deadlines:
                if not Deadline.query.filter_by(case_id=cse.id, name=name).first():
                    dl = Deadline(case_id=cse.id, name=name, due_date=due, source=source, notes=notes)
                    db.session.add(dl)

        # Calculate totals
        invoice.calculate_totals()

        # Seed CalendarEvent from existing Deadlines
        deadlines = Deadline.query.all()
        created_events = 0
        for dl in deadlines:
            exists = CalendarEvent.query.filter_by(title=dl.name, case_id=dl.case_id, start_at=dl.due_date).first()
            if not exists:
                ev = CalendarEvent(
                    title=dl.name,
                    description=dl.notes,
                    start_at=dl.due_date,
                    end_at=None,
                    all_day=True,
                    case_id=dl.case_id,
                    client_id=Case.query.get(dl.case_id).client_id if dl.case_id else None,
                    created_by_id=admin.id,
                    reminder_minutes_before=60,
                    status='scheduled'
                )
                db.session.add(ev)
                created_events += 1

        db.session.commit()
        print("Seed complete: clients ensured, sample cases ensured, portal user and billing demo ensured. Calendar events created:", created_events)


if __name__ == '__main__':
    seed()
