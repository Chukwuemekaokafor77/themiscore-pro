from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Create all database tables
        print("Creating database tables...")
        db.create_all()
        
        # Create a default admin user if it doesn't exist
        if not User.query.filter_by(email='admin@lawfirm.com').first():
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
            print("Default admin user created with email 'admin@lawfirm.com' and password 'admin123'")
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    init_db()
    print("Database initialization complete!")
