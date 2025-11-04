import os
import time
import requests
import sys
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
from models import db, User, Client, Case, Action, Document, CaseNote, CaseAction

# Import utility functions
from utils import get_pagination, apply_case_filters, get_sort_params

# Import custom filters
from filters import time_ago, format_date, format_currency, pluralize

# Load environment variables
load_dotenv()

# AssemblyAI Configuration
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
ASSEMBLYAI_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIPTION_URL = "https://api.assemblyai.com/v2/transcript"
ASSEMBLYAI_HEADERS = {
    'authorization': ASSEMBLYAI_API_KEY,
    'content-type': 'application/json'
}

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
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # Session expires after 1 hour

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'gif'}

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Register template filters
app.jinja_env.filters['time_ago'] = time_ago
app.jinja_env.filters['format_date'] = format_date
app.jinja_env.filters['format_currency'] = format_currency
app.jinja_env.filters['pluralize'] = pluralize

# Import models for Flask-Migrate to detect
from models import User, Client, Case, Action, Document, CaseNote

# Login manager setup
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

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
    """
    Enhanced case analysis with improved entity extraction and case type detection.
    Returns a dictionary with case type, confidence, entities, and suggested actions.
    """
    if not description:
        return {
            'case_type': 'other',
            'confidence': 0,
            'entities': {},
            'suggested_actions': [],
            'priority': 'medium',
            'estimated_duration': '1-3 months',
            'required_documents': []
        }
        
    description = description.lower()
    
    # Enhanced case type patterns with weights
    case_patterns = {
        'personal_injury': {
            'patterns': [
                (r'car\s+accident|car\s+crash|motor\s+vehicle', 2),
                (r'slip\s+and\s+fall|trip\s+and\s+fall', 2),
                (r'medical\s+malpractice|wrongful\s+death', 3),
                (r'personal\s+injury|negligence', 1.5),
                (r'brain\s+injur|spinal\s+cord\s+injur', 3),
                (r'dog\s+bite|animal\s+attack', 2),
                (r'premises\s+liability', 2),
                (r'product\s+liability|defective\s+product', 2.5)
            ],
            'suggested_actions': [
                'Gather medical records and bills',
                'Obtain police/accident reports',
                'Document injuries with photos',
                'Collect witness statements',
                'Contact insurance companies',
                'Calculate damages and losses',
                'Schedule medical evaluation',
                'Preserve evidence (photos, clothing, etc.)'
            ],
            'required_documents': [
                'Medical Records',
                'Police Reports',
                'Insurance Information',
                'Witness Statements',
                'Photographic Evidence',
                'Proof of Lost Wages',
                'Medical Bills',
                'Property Damage Estimates'
            ],
            'priority_factors': {
                'severe_injury': 3,
                'statute_limitations': 2,
                'insurance_involved': 1
            },
            'estimated_duration': '3-18 months',
            'success_rate': '70-80%',
            'average_settlement': '$30,000 - $1,000,000+',
            'key_considerations': [
                'Statute of limitations',
                'Insurance policy limits',
                'Comparative negligence',
                'Pre-existing conditions',
                'Future medical needs'
            ]
        },
        # Additional case types with similar detailed structures...
    }
    
    # Initialize scores and results
    case_type_scores = {case_type: 0 for case_type in case_patterns}
    entities = {
        'names': set(),
        'dates': set(),
        'amounts': set(),
        'locations': set(),
        'injuries': set(),
        'vehicles': set(),
        'insurance_companies': set()
    }
    
    # Enhanced entity extraction
    entities['names'].update(re.findall(r'\b(?:mr\.?|mrs\.?|ms\.?|dr\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', description, re.IGNORECASE))
    entities['dates'].update(re.findall(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b', description, re.IGNORECASE))
    entities['amounts'].update(re.findall(r'\$\d+(?:\.\d{2})?|\d+\s*(?:dollars|USD)', description, re.IGNORECASE))
    entities['locations'].update(re.findall(r'\b(?:at|in|near|on|by|from)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)', description))
    
    # Injury-specific entity extraction
    injury_keywords = ['fracture', 'broken', 'laceration', 'concussion', 'whiplash', 'sprain', 'strain', 'tear', 'injury']
    entities['injuries'].update([word for word in injury_keywords if word in description])
    
    # Score each case type
    for case_type, case_data in case_patterns.items():
        for pattern, weight in case_data['patterns']:
            if re.search(pattern, description, re.IGNORECASE):
                case_type_scores[case_type] += weight
    
    # Determine priority based on content
    priority_factors = {
        'urgent_keywords': ['emergency', 'immediate', 'right away', 'asap', 'statute expir', 'deadline'],
        'high_priority': ['lawsuit', 'sue', 'suing', 'court date', 'trial', 'hearing'],
        'medium_priority': ['consultation', 'advice', 'review', 'document'],
        'low_priority': ['general question', 'information', 'potential case']
    }
    
    priority_score = 0
    for level, keywords in priority_factors.items():
        for keyword in keywords:
            if keyword in description:
                if 'urgent' in level:
                    priority_score += 3
                elif 'high' in level:
                    priority_score += 2
                elif 'medium' in level:
                    priority_score += 1
    
    if priority_score >= 3:
        priority = 'high'
    elif priority_score >= 1:
        priority = 'medium'
    else:
        priority = 'low'
    
    # Get the highest scoring case type
    if max(case_type_scores.values()) > 0:
        predicted_case_type = max(case_type_scores, key=case_type_scores.get)
        confidence = case_type_scores[predicted_case_type] / (sum(case_type_scores.values()) or 1)
    else:
        predicted_case_type = 'other'
        confidence = 0
    
    # Get case type specific data
    case_data = case_patterns.get(predicted_case_type, {})
    
    # Clean up entities (remove empty matches and convert to list)
    for key in entities:
        entities[key] = [e for e in entities[key] if e.strip()]
    
    return {
        'case_type': predicted_case_type,
        'case_type_display': ' '.join(word.capitalize() for word in predicted_case_type.split('_')),
        'confidence': round(confidence, 2),
        'entities': entities,
        'suggested_actions': case_data.get('suggested_actions', []),
        'required_documents': case_data.get('required_documents', []),
        'priority': priority,
        'estimated_duration': case_data.get('estimated_duration', '1-3 months'),
        'success_rate': case_data.get('success_rate', 'Varies'),
        'average_settlement': case_data.get('average_settlement', 'Varies'),
        'key_considerations': case_data.get('key_considerations', []),
        'analysis_timestamp': datetime.utcnow().isoformat()
    }

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
    user = db.session.get(User, session['user_id'])
    
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
    from models import Case, Client  # Import here to avoid circular imports
    
    try:
        # Get pagination parameters
        pagination = get_pagination(request.args.get('page'), request.args.get('per_page', 10))
        
        # Base query with client relationship
        query = Case.query.options(db.joinedload(Case.client))
        
        # Apply filters from query parameters
        query = apply_case_filters(query, request.args)
        
        # Get sort parameters
        sort_column, sort_order = get_sort_params(request.args)
        
        # Apply sorting
        if sort_column is not None:
            if sort_order == 'desc':
                query = query.order_by(db.desc(sort_column))
            else:
                query = query.order_by(sort_column)
        else:
            # Default sorting if none specified
            query = query.order_by(Case.created_at.desc())
        
        # Paginate the results
        paginated_cases = query.paginate(
            page=pagination['page'],
            per_page=pagination['per_page'],
            error_out=False
        )
        
        # Get all clients for filters and forms
        clients = Client.query.order_by(Client.last_name, Client.first_name).all()
        
        # Get filter values for the template
        current_filters = {
            'client_id': request.args.get('client_id', ''),
            'status': request.args.get('status', ''),
            'priority': request.args.get('priority', ''),
            'search': request.args.get('search', '')
        }
        
        return render_template(
            'cases.html',
            cases=paginated_cases.items,
            pagination=paginated_cases,
            clients=clients,
            filters=current_filters,
            sort=request.args.get('sort', '-created_at')
        )
        
    except Exception as e:
        app.logger.error(f"Error in cases route: {str(e)}")
        flash('An error occurred while loading cases. Please try again later.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/cases/<int:case_id>')
@login_required
def view_case(case_id):
    case = db.session.get(Case, case_id)
    if case is None:
        abort(404, description="Case not found")
    documents = db.session.query(Document).filter_by(case_id=case_id).all()
    return render_template('view_case.html', case=case, documents=documents)

# Actions routes
@app.route('/actions')
@login_required
@requires_auth
def actions():
    # Get all actions with their related cases through the many-to-many relationship
    actions = db.session.query(Action).options(
        db.joinedload(Action.case_actions).joinedload(CaseAction.case),
        db.joinedload(Action.assigned_to)
    ).all()
    return render_template('actions.html', actions=actions)

@app.route('/actions/add', methods=['GET', 'POST'])
@login_required
def add_action():
    # Get all cases and users for the form dropdowns
    cases = db.session.query(Case).all()
    users = db.session.query(User).all()
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.form.get('title')
            description = request.form.get('description', '')
            action_type = request.form.get('action_type')
            status = request.form.get('status', 'pending')
            priority = request.form.get('priority', 'medium')
            due_date_str = request.form.get('due_date')
            assigned_to_id = request.form.get('assigned_to_id')
            case_id = request.form.get('case_id')
            
            # Convert date string to datetime
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
            
            # Create new action
            new_action = Action(
                title=title,
                description=description,
                action_type=action_type,
                status=status,
                priority=priority,
                due_date=due_date,
                assigned_to_id=assigned_to_id,
                created_by_id=current_user.id
            )
            
            db.session.add(new_action)
            db.session.flush()  # Get the new action's ID
            
            # If case_id is provided, create the case_action association
            if case_id and case_id != 'None':
                case_action = CaseAction(
                    case_id=case_id,
                    action_id=new_action.id,
                    assigned_to_id=assigned_to_id,
                    status=status
                )
                db.session.add(case_action)
            
            db.session.commit()
            flash('Action created successfully!', 'success')
            return redirect(url_for('view_action', action_id=new_action.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating action: {str(e)}")
            flash('An error occurred while creating the action. Please try again.', 'danger')
    
    # For GET request, show the form
    return render_template('add_action.html', cases=cases, users=users)

@app.route('/actions/<int:action_id>')
@login_required
def view_action(action_id):
    action = db.session.get(Action, action_id)
    if action is None:
        abort(404, description="Action not found")
    return render_template('view_action.html', action=action)

# Documents routes
@app.route('/documents')
@login_required
@requires_auth
def documents():
    # Get all documents with case and user information using proper relationship loading
    documents = db.session.query(Document).options(
        db.joinedload(Document.case),
        db.joinedload(Document.uploaded_by)
    ).all()
    
    return render_template('documents.html', documents=documents)

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
    cases = db.session.query(Case).all()
    return render_template('upload_document.html', cases=cases)

@app.route('/documents/<int:document_id>')
@login_required
def view_document(document_id):
    document = db.session.get(Document, document_id)
    if document is None:
        abort(404, description="Document not found")
    
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
    document = db.session.get(Document, document_id)
    if document is None:
        abort(404, description="Document not found")
    return send_from_directory(
        os.path.dirname(document.file_path),
        os.path.basename(document.file_path),
        as_attachment=True
    )

@app.route('/documents/delete/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    document = db.session.get(Document, document_id)
    if document is None:
        abort(404, description="Document not found")
    
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
        client = db.session.get(Client, (data['client_first_name'], data['client_last_name'], data.get('client_email')))
        if client is None:
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
            action = db.session.get(Action, action_text)
            if action is None:
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
    case = db.session.get(Case, case_id)
    if case is None:
        abort(404, description="Case not found")
    return jsonify(case.to_dict())

@app.route('/api/cases/<int:case_id>', methods=['PUT'])
def update_case(case_id):
    """Update case details."""
    case = db.session.get(Case, case_id)
    if case is None:
        abort(404, description="Case not found")
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

# Transcription routes
@app.route('/transcribe', methods=['GET', 'POST'])
@login_required
def transcribe():
    if not ASSEMBLYAI_API_KEY:
        return jsonify({'error': 'AssemblyAI API key is not configured'}), 500
        
    if request.method == 'POST':
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Validate file type
        allowed_extensions = {'wav', 'mp3', 'm4a', 'webm'}
        file_ext = audio_file.filename.rsplit('.', 1)[1].lower() if '.' in audio_file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Unsupported file type. Allowed types: {allowed_extensions}'}), 400
            
        temp_path = None
        try:
            # Save the file temporarily with proper extension
            temp_filename = f'temp_audio_{int(time.time())}.{file_ext}'
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
            audio_file.save(temp_path)
            
            # Upload to AssemblyAI
            def read_file(filename, chunk_size=5242880):
                with open(filename, 'rb') as _file:
                    while True:
                        data = _file.read(chunk_size)
                        if not data:
                            break
                        yield data
            
            # Upload the audio file
            upload_response = requests.post(
                ASSEMBLYAI_UPLOAD_URL,
                headers={'authorization': ASSEMBLYAI_API_KEY},
                data=read_file(temp_path)
            )
            
            if upload_response.status_code != 200:
                error_msg = upload_response.json().get('error', 'Failed to upload audio')
                return jsonify({'error': f'Upload failed: {error_msg}'}), 500
            
            audio_url = upload_response.json()['upload_url']
            
            # Start transcription with additional parameters for better accuracy
            transcription_response = requests.post(
                ASSEMBLYAI_TRANSCRIPTION_URL,
                headers=ASSEMBLYAI_HEADERS,
                json={
                    'audio_url': audio_url,
                    'speaker_labels': True,
                    'language_code': 'en_us',
                    'punctuate': True,
                    'format_text': True,
                    'dual_channel': True,
                    'speech_model': 'best'
                }
            )
            
            if transcription_response.status_code != 200:
                error_msg = transcription_response.json().get('error', 'Failed to start transcription')
                return jsonify({'error': f'Transcription failed to start: {error_msg}'}), 500
            
            transcript_id = transcription_response.json()['id']
            max_attempts = 60  # 5 minutes max wait time (5 seconds * 60 attempts)
            attempts = 0
            
            # Poll for transcription completion with timeout
            while attempts < max_attempts:
                attempts += 1
                status_response = requests.get(
                    f"{ASSEMBLYAI_TRANSCRIPTION_URL}/{transcript_id}",
                    headers=ASSEMBLYAI_HEADERS
                )
                
                if status_response.status_code != 200:
                    time.sleep(5)  # Wait 5 seconds before retrying
                    continue
                
                status = status_response.json().get('status')
                
                if status == 'completed':
                    transcription = status_response.json()
                    
                    # Clean up
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                    return jsonify({
                        'text': transcription['text'],
                        'speakers': transcription.get('utterances', []),
                        'confidence': transcription.get('confidence', 0),
                        'words': transcription.get('words', [])
                    })
                    
                elif status in ['failed', 'error']:
                    error_msg = status_response.json().get('error', 'Transcription failed')
                    return jsonify({'error': f'Transcription failed: {error_msg}'}), 500
                
                time.sleep(5)  # Check every 5 seconds
            
            return jsonify({'error': 'Transcription timed out'}), 504
            
        except requests.exceptions.RequestException as e:
            app.logger.error(f'API request failed: {str(e)}')
            return jsonify({'error': 'Failed to connect to transcription service'}), 503
            
        except Exception as e:
            app.logger.error(f'Transcription error: {str(e)}')
            return jsonify({'error': f'An error occurred during transcription: {str(e)}'}), 500
            
        finally:
            # Ensure temp file is always cleaned up
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    app.logger.error(f'Failed to clean up temp file: {str(e)}')
    
    # For GET requests, show the transcription interface
    return render_template('transcribe.html')

@app.route('/transcribe/status/<transcript_id>', methods=['GET'])
@login_required
def transcription_status(transcript_id):
    response = requests.get(
        f"{ASSEMBLYAI_TRANSCRIPTION_URL}/{transcript_id}",
        headers=ASSEMBLYAI_HEADERS
    )
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
