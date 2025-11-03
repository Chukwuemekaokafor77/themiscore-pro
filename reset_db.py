import os
from app import app, db
from models import User

def reset_database():
    with app.app_context():
        # Drop all tables
        print("Dropping all tables...")
        db.drop_all()
        
        # Create all tables
        print("Creating all tables...")
        db.create_all()
        
        # Create default admin user
        print("Creating default admin user...")
        admin = User(
            email='admin@lawfirm.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        
        print("\nDatabase has been reset successfully!")
        print(f"Admin user created with email: {admin.email}")
        print("Password: admin123")

if __name__ == '__main__':
    print("Resetting database...")
    reset_database()
