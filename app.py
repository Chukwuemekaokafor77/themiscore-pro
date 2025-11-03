import os
from flask import Flask, render_template, request, jsonify, url_for, redirect, flash, session, send_from_directory, send_file, abort, Response
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import re
import os
from dotenv import load_dotenv
from flask_migrate import Migrate
import mimetypes
import base64

# Import database models
from models import db, User, Client, Case, Action, Document, CaseNote, case_actions

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure database URI
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///legalintake.db'

# Authentication configuration
AUTH_USERNAME = 'demo'
AUTH_PASSWORD = 'themiscore123'  # Change this to a strong password

# Basic Auth decorator
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == AUTH_USERNAME and auth.password == AUTH_PASSWORD):
            return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

# Load configuration from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///legalintake.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # Session expires after 1 hour

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'gif'}

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Import models for Flask-Migrate to detect
from models import User, Client, Case, Action, Document, CaseNote

# Login manager setup
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create database tables
with app.app_context():
    db.create_all()
    # Create default admin user if not exists
    if not User.query.filter_by(email='admin@lawfirm.com').first():
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

# Case categories and their details
CASE_CATEGORIES = {
    'slip_and_fall': {
        'name': 'Slip and Fall',
        'department': 'Personal Injury',
        'priority': 'High',
        'actions': [
            'Send evidence preservation letter',
            'Request staff information',
            'Obtain security footage',
            'Collect medical records'
        ]
    },
    'car_accident': {
        'name': 'Car Accident',
        'department': 'Auto Accident',
        'priority': 'High',
        'actions': [
            'Request police report',
            'Contact insurance companies',
            'Document vehicle damage',
            'Schedule medical evaluation'
        ]
    },
    'employment': {
        'name': 'Employment Law',
        'department': 'Employment Law',
        'priority': 'Medium-High',
        'actions': [
            'Send evidence preservation letter',
            'Document employment history',
            'Prepare EEOC filing',
            'Gather witness statements'
        ]
    },
    'medical_malpractice': {
        'name': 'Medical Malpractice',
        'department': 'Medical Malpractice',
        'priority': 'High',
        'actions': [
            'Request complete medical records',
            'Preserve all evidence',
            'Retain medical expert witness',
            'Calculate statute of limitations'
        ]
    }
}

def analyze_case_description(description):
    """Analyze the case description using rule-based matching to determine the case type."""
    description = description.lower()
    
    # Define keywords for each case type
    case_keywords = {
        'slip_and_fall': [
            'slip', 'trip', 'fall', 'slipped', 'tripped', 'fell',
            'wet floor', 'uneven surface', 'sidewalk', 'store', 'supermarket',
            'walmart', 'target', 'grocery', 'puddle', 'ice', 'snow', 'water',
            'hazard', 'premises', 'injury', 'injured'
        ],
        'car_accident': [
            'car', 'vehicle', 'auto', 'accident', 'crash', 'collision',
            'hit', 'rear-end', 't-bone', 'intersection', 'highway',
            'speeding', 'ran red light', 'ran stop sign', 'drunk', 'dui',
            'police report', 'insurance', 'statefarm', 'geico', 'allstate'
        ],
        'employment': [
            'employer', 'boss', 'manager', 'supervisor', 'harassment',
            'discrimination', 'wrongful termination', 'fired', 'laid off',
            'retaliation', 'hostile work environment', 'wage', 'overtime',
            'unpaid wages', 'overtime', 'overtime pay', 'fmla', 'family leave',
            'disability', 'ada', 'age', 'race', 'gender', 'pregnancy',
            'whistleblower', 'retaliate', 'hr', 'human resources'
        ],
        'medical_malpractice': [
            'doctor', 'hospital', 'nurse', 'surgeon', 'surgery', 'operation',
            'misdiagnosis', 'wrong diagnosis', 'surgical error', 'anesthesia',
            'infection', 'birth injury', 'er', 'emergency room', 'prescription',
            'medication error', 'malpractice', 'negligence', 'medical mistake',
            'left sponge', 'wrong site', 'wrong patient', 'surgical instrument'
        ]
    }
    
    # Count keyword matches for each case type
    scores = {case: 0 for case in case_keywords}
    
    for case, keywords in case_keywords.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', description):
                scores[case] += 1
    
    # Get the case type with the highest score
    best_match = max(scores, key=scores.get)
    
    # Only return the best match if it has at least 2 keyword matches
    return best_match if scores[best_match] >= 2 else 'other'

# Helper functions
def save_uploaded_file(file):
    """Save an uploaded file and return its path."""
    if not file:
        return None
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Ensure unique filename
    counter = 1
    name, ext = os.path.splitext(filename)
    while os.path.exists(filepath):
        filename = f"{name}_{counter}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        counter += 1
    
    file.save(filepath)
    return filepath

# Routes
@app.route('/')
@requires_auth
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@requires_auth
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
@requires_auth
def dashboard():
    # Get current user
    user = User.query.get(session['user_id'])
    
    # Get stats
    stats = {
        'active_cases': Case.query.filter_by(status='open').count(),
        'active_clients': Client.query.count(),
        'pending_actions': Action.query.filter_by(status='pending').count(),
        'documents_count': Document.query.count(),
        'last_updated': datetime.now().strftime('%b %d, %Y')
    }
    
    # Get recent cases
    recent_cases = Case.query.order_by(Case.created_at.desc()).limit(5).all()
    
    # Get upcoming actions
    upcoming_actions = Action.query.filter(
        Action.due_date >= datetime.now()
    ).order_by(Action.due_date.asc()).limit(5).all()
    
    return render_template(
        'dashboard.html',
        current_user=user,
        stats=stats,
        recent_cases=recent_cases,
        upcoming_actions=upcoming_actions
    )

# Clients routes
@app.route('/clients')
@login_required
@requires_auth
def clients():
    # Get all clients with their case counts
    clients = Client.query.outerjoin(Case).group_by(Client.id).all()
    return render_template('clients.html', clients=clients)

@app.route('/clients/<int:client_id>')
@login_required
def view_client(client_id):
    client = Client.query.get_or_404(client_id)
    cases = Case.query.filter_by(client_id=client_id).all()
    return render_template('view_client.html', client=client, cases=cases)

# Cases routes
@app.route('/cases')
@login_required
@requires_auth
def cases():
    # Get all cases with client information
    cases = Case.query.join(Client).all()
    return render_template('cases.html', cases=cases)

@app.route('/cases/<int:case_id>')
@login_required
def view_case(case_id):
    case = Case.query.get_or_404(case_id)
    actions = case.actions
    documents = Document.query.filter_by(case_id=case_id).all()
    return render_template('view_case.html', case=case, actions=actions, documents=documents)

# Actions routes
@app.route('/actions')
@login_required
@requires_auth
def actions():
    # Get all actions with related case information
    actions = db.session.query(Action, Case).join(Case, Action.case_id == Case.id).all()
    return render_template('actions.html', actions=actions)

@app.route('/actions/<int:action_id>')
@login_required
def view_action(action_id):
    action = Action.query.get_or_404(action_id)
    return render_template('view_action.html', action=action)

# Documents routes
@app.route('/documents')
@login_required
@requires_auth
def documents():
    # Get all documents with case and user information
    documents = db.session.query(
        Document,
        Case,
        User
    ).outerjoin(
        Case, Document.case_id == Case.id
    ).join(
        User, Document.uploaded_by == User.id
    ).all()
    
    # Convert to a list of dictionaries for easier template handling
    document_list = []
    for doc, case, user in documents:
        doc_dict = doc.__dict__.copy()
        doc_dict['case'] = case
        doc_dict['uploaded_by'] = user
        document_list.append(doc_dict)
    
    return render_template('documents.html', documents=document_list)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/documents/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part in the request', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # Create a unique filename to prevent overwriting
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                filename = f"{base}_{i}{ext}"
                i += 1
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get file size in bytes
            file_size = os.path.getsize(filepath)
            
            # Create document record
            document = Document(
                name=request.form.get('name', filename),  # Use custom name or filename
                file_path=filepath,
                file_type=file.content_type,
                file_size=file_size,
                document_type=request.form.get('document_type', 'other'),
                description=request.form.get('description'),
                case_id=request.form.get('case_id') or None,
                uploaded_by=session['user_id']
            )
            
            db.session.add(document)
            db.session.commit()
            
            flash('Document uploaded successfully!', 'success')
            return redirect(url_for('documents'))
        else:
            flash('File type not allowed. Allowed file types are: ' + ', '.join(ALLOWED_EXTENSIONS), 'danger')
    
    # For GET request, show upload form
    cases = Case.query.all()
    return render_template('upload_document.html', cases=cases)

@app.route('/documents/<int:document_id>')
@login_required
def view_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        flash('File not found on server', 'danger')
        return redirect(url_for('documents'))
    
    # Get file extension and set appropriate MIME type
    mime_type, _ = mimetypes.guess_type(document.file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    
    return send_file(
        document.file_path,
        mimetype=mime_type,
        as_attachment=False,
        download_name=document.name
    )

@app.route('/documents/download/<int:document_id>')
@login_required
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        flash('File not found on server', 'danger')
        return redirect(url_for('documents'))
    
    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.name
    )

@app.route('/documents/delete/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if the current user is authorized to delete this document
    if document.uploaded_by != session['user_id'] and not current_user.is_admin:
        flash('You are not authorized to delete this document', 'danger')
        return redirect(url_for('documents'))
    
    try:
        # Delete the file from the filesystem
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete the document record from the database
        db.session.delete(document)
        db.session.commit()
        
        flash('Document deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting document: {str(e)}')
        flash('Error deleting document', 'danger')
    
    return redirect(url_for('documents'))

@app.route('/api/cases', methods=['POST'])
def create_case():
    """Create a new case from the intake form."""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['client_first_name', 'client_last_name', 'case_title', 'case_description']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Create or find client
        client = Client.query.filter_by(
            first_name=data['client_first_name'],
            last_name=data['client_last_name'],
            email=data.get('client_email')
        ).first()
        
        if not client:
            client = Client(
                first_name=data['client_first_name'],
                last_name=data['client_last_name'],
                email=data.get('client_email'),
                phone=data.get('client_phone'),
                address=data.get('client_address')
            )
            db.session.add(client)
            db.session.flush()  # Get the client ID
        
        # Create case
        new_case = Case(
            title=data['case_title'],
            description=data['case_description'],
            case_type=data.get('case_type', 'other'),
            status='open',
            priority=data.get('priority', 'medium'),
            client_id=client.id,
            created_by_id=1,  # In a real app, this would be the logged-in user
            assigned_to_id=data.get('assigned_to')
        )
        db.session.add(new_case)
        db.session.flush()  # Get the case ID
        
        # Add default actions based on case type
        case_actions = CASE_CATEGORIES.get(data.get('case_type', 'other'), {}).get('actions', [])
        for action_text in case_actions:
            action = Action.query.filter_by(title=action_text).first()
            if not action:
                action = Action(title=action_text, action_type='default')
                db.session.add(action)
                db.session.flush()
            
            # Add action to case with default assignment
            db.session.execute(
                case_actions.insert().values(
                    case_id=new_case.id,
                    action_id=action.id,
                    status='pending',
                    assigned_to=1  # Default to admin
                )
            )
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Case created successfully',
            'case_id': new_case.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/cases/<int:case_id>', methods=['GET'])
def get_case(case_id):
    """Get case details by ID."""
    case = Case.query.get_or_404(case_id)
    return jsonify(case.to_dict())

@app.route('/api/cases/<int:case_id>', methods=['PUT'])
def update_case(case_id):
    """Update case details."""
    case = Case.query.get_or_404(case_id)
    data = request.get_json()
    
    try:
        # Update case fields
        for field in ['title', 'description', 'status', 'priority', 'assigned_to_id']:
            if field in data:
                setattr(case, field, data[field])
        
        case.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Case updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/clients/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        try:
            client = Client(
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                address=request.form.get('address')
            )
            db.session.add(client)
            db.session.commit()
            flash('Client added successfully!', 'success')
            return redirect(url_for('clients'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding client: {str(e)}', 'danger')
    
    return render_template('add_client.html')        

# Add more API endpoints for clients, actions, and other resources...

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'An internal error occurred'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
