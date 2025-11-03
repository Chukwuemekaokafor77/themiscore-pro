from app import app, db
from models import User, Client, Case, Action, Document, CaseNote

def verify_database():
    with app.app_context():
        # Check if tables exist
        print("\n=== Database Tables ===")
        print("\nTables in the database:")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        print(inspector.get_table_names())
        
        # Check admin user
        print("\n=== Admin User ===")
        admin = User.query.filter_by(email='admin@lawfirm.com').first()
        if admin:
            print(f"Admin user found: {admin.email}")
            print(f"Name: {admin.first_name} {admin.last_name}")
            print(f"Role: {admin.role}")
            print(f"Active: {admin.is_active}")
        else:
            print("Admin user not found!")
        
        # Count records in each table
        print("\n=== Record Counts ===")
        print(f"Users: {User.query.count()}")
        print(f"Clients: {Client.query.count()}")
        print(f"Cases: {Case.query.count()}")
        print(f"Actions: {Action.query.count()}")
        print(f"Documents: {Document.query.count()}")
        print(f"Case Notes: {CaseNote.query.count()}")
        
        # Display first few records from each table (if any)
        print("\n=== Sample Data ===")
        
        print("\nUsers:")
        for user in User.query.limit(3).all():
            print(f"- {user.email} ({user.role})")
            
        print("\nClients:")
        for client in Client.query.limit(3).all():
            print(f"- {client.first_name} {client.last_name}")
            
        print("\nCases:")
        for case in Case.query.limit(3).all():
            print(f"- {case.title} ({case.status})")

if __name__ == '__main__':
    print("Verifying database...")
    verify_database()
    print("\nVerification complete!")
