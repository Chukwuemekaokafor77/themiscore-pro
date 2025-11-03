from app import app, db
from models import User, Client, Case, Action, Document, CaseNote
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def create_sample_data():
    with app.app_context():
        # Clear existing data (except admin user)
        print("Clearing existing data...")
        CaseNote.query.delete()
        Document.query.delete()
        Action.query.delete()
        Case.query.delete()
        Client.query.delete()
        # Keep admin user
        User.query.filter(User.email != 'admin@lawfirm.com').delete()
        db.session.commit()
        
        # Create sample users
        print("Creating sample users...")
        users = [
            User(
                email='attorney1@lawfirm.com',
                first_name='Sarah',
                last_name='Johnson',
                role='attorney',
                is_active=True
            ),
            User(
                email='paralegal1@lawfirm.com',
                first_name='Michael',
                last_name='Chen',
                role='paralegal',
                is_active=True
            ),
            User(
                email='staff1@lawfirm.com',
                first_name='Emily',
                last_name='Rodriguez',
                role='staff',
                is_active=True
            )
        ]
        
        # Set passwords
        for user in users:
            user.set_password('password123')
            db.session.add(user)
        
        db.session.commit()
        
        # Create sample clients
        print("Creating sample clients...")
        clients = [
            Client(
                first_name='John',
                last_name='Smith',
                email='john.smith@example.com',
                phone='(555) 123-4567',
                address='123 Main St, Anytown, USA',
                date_of_birth=datetime(1980, 5, 15)
            ),
            Client(
                first_name='Maria',
                last_name='Garcia',
                email='maria.garcia@example.com',
                phone='(555) 234-5678',
                address='456 Oak Ave, Somewhere, USA',
                date_of_birth=datetime(1975, 9, 23)
            ),
            Client(
                first_name='James',
                last_name='Wilson',
                email='james.wilson@example.com',
                phone='(555) 345-6789',
                address='789 Pine Rd, Nowhere, USA',
                date_of_birth=datetime(1990, 2, 10)
            )
        ]
        
        for client in clients:
            db.session.add(client)
        
        db.session.commit()
        
        # Get the admin user and other users
        admin = User.query.filter_by(email='admin@lawfirm.com').first()
        attorney = User.query.filter_by(email='attorney1@lawfirm.com').first()
        paralegal = User.query.filter_by(email='paralegal1@lawfirm.com').first()
        staff = User.query.filter_by(email='staff1@lawfirm.com').first()
        
        # Create sample cases
        print("Creating sample cases...")
        cases = [
            Case(
                title='Slip and Fall - Smith',
                description='Client slipped on a wet floor at a grocery store.',
                case_type='personal_injury',
                status='open',
                priority='high',
                client_id=clients[0].id,
                assigned_to_id=attorney.id,
                created_by_id=admin.id
            ),
            Case(
                title='Divorce - Garcia',
                description='Contested divorce with child custody issues.',
                case_type='family_law',
                status='in_progress',
                priority='medium',
                client_id=clients[1].id,
                assigned_to_id=attorney.id,
                created_by_id=admin.id
            ),
            Case(
                title='Contract Dispute - Wilson',
                description='Breach of contract by vendor.',
                case_type='business_law',
                status='open',
                priority='low',
                client_id=clients[2].id,
                assigned_to_id=paralegal.id,
                created_by_id=attorney.id
            )
        ]
        
        for case in cases:
            db.session.add(case)
        
        db.session.commit()
        
        # Create sample actions
        print("Creating sample actions...")
        actions = [
            Action(
                title='Initial client consultation',
                description='Meet with client to discuss case details.',
                action_type='meeting',
                status='completed',
                priority='high',
                due_date=datetime.now() - timedelta(days=5),
                completed_at=datetime.now() - timedelta(days=4),
                created_by_id=admin.id,
                assigned_to_id=attorney.id
            ),
            Action(
                title='Draft demand letter',
                description='Prepare demand letter to opposing party.',
                action_type='document_preparation',
                status='in_progress',
                priority='high',
                due_date=datetime.now() + timedelta(days=3),
                created_by_id=attorney.id,
                assigned_to_id=paralegal.id
            ),
            Action(
                title='File court documents',
                description='File initial pleadings with the court.',
                action_type='court_filing',
                status='pending',
                priority='medium',
                due_date=datetime.now() + timedelta(days=7),
                created_by_id=attorney.id,
                assigned_to_id=staff.id
            )
        ]
        
        for action in actions:
            db.session.add(action)
        
        db.session.commit()
        
        # Associate actions with cases
        cases[0].actions.append(actions[0])
        cases[0].actions.append(actions[1])
        cases[1].actions.append(actions[2])
        db.session.commit()
        
        # Create sample documents
        print("Creating sample documents...")
        documents = [
            Document(
                name='Retainer Agreement - Smith.pdf',
                file_path='/documents/retainer_smith.pdf',
                file_type='application/pdf',
                file_size=102400,  # 100 KB
                description='Signed retainer agreement',
                case_id=cases[0].id,
                uploaded_by_id=staff.id
            ),
            Document(
                name='Incident Report - Smith.pdf',
                file_path='/documents/incident_report_smith.pdf',
                file_type='application/pdf',
                file_size=204800,  # 200 KB
                description='Incident report from the grocery store',
                case_id=cases[0].id,
                uploaded_by_id=attorney.id,
                action_id=actions[0].id
            ),
            Document(
                name='Divorce Petition - Garcia.docx',
                file_path='/documents/divorce_petition_garcia.docx',
                file_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                file_size=51200,  # 50 KB
                description='Initial divorce petition',
                case_id=cases[1].id,
                uploaded_by_id=paralegal.id
            )
        ]
        
        for doc in documents:
            db.session.add(doc)
        
        db.session.commit()
        
        # Create sample case notes
        print("Creating sample case notes...")
        case_notes = [
            CaseNote(
                content='Client called to report that the store manager has been uncooperative.',
                is_private=False,
                case_id=cases[0].id,
                created_by_id=staff.id
            ),
            CaseNote(
                content='Spoke with witness who confirmed the floor was wet without proper signage.',
                is_private=True,
                case_id=cases[0].id,
                created_by_id=attorney.id
            ),
            CaseNote(
                content='Client provided additional medical records showing extent of injuries.',
                is_private=False,
                case_id=cases[0].id,
                created_by_id=paralegal.id
            )
        ]
        
        for note in case_notes:
            db.session.add(note)
        
        db.session.commit()
        
        print("\nSample data has been created successfully!")
        print("\nSample users created:")
        print(f"- {admin.email} (admin)")
        print(f"- {attorney.email} (attorney)")
        print(f"- {paralegal.email} (paralegal)")
        print(f"- {staff.email} (staff)")
        print("\nAll users have been created with password: password123")

if __name__ == '__main__':
    print("Creating sample data...")
    create_sample_data()
