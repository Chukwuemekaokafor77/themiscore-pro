import random
from datetime import datetime, timedelta

from app import app, db
from models import Client, Case, User

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

        existing = Client.query.count()
        if existing >= 30:
            print(f"Clients already seeded ({existing}). Skipping.")
            return

        # Create 30 clients with unique emails
        clients = []
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

        # Create a few sample cases for the first 5 clients
        for i in range(5):
            case = Case(
                title=CASE_TITLES[i % len(CASE_TITLES)],
                description=CASE_DESCRIPTIONS[i % len(CASE_DESCRIPTIONS)],
                case_type=CASE_TYPES[i % len(CASE_TYPES)],
                status='open',
                priority=random.choice(['high', 'medium', 'low']),
                client_id=clients[i].id,
                created_by_id=admin.id,
            )
            db.session.add(case)

        db.session.commit()
        print("Seed complete: 30 clients and 5 sample cases created.")


if __name__ == '__main__':
    seed()
