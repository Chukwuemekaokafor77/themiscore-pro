import os
import requests
from flask import Flask, render_template, request, jsonify, url_for, redirect, flash, session, send_from_directory, send_file, abort, Response, current_app
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from dotenv import load_dotenv
from flask_migrate import Migrate
import mimetypes

# Support both package and script imports
try:
    # Package-relative imports (when FLASK_APP=law_firm_intake.app)
    from .models import db, User, Client, Case, Action, Document, CaseNote, CaseAction, AIInsight, Lawyer, Referral, Transcript, Deadline, EmailDraft
    from .utils import get_pagination, apply_case_filters, get_sort_params, analyze_case, analyze_intake_text_scenarios
    from .filters import time_ago, format_date, format_currency, pluralize
    from .services.stt import STTService
    from .services.letter_templates import LetterTemplateService
except ImportError:  # pragma: no cover
    # Fallback for running as a script (python app.py)
    from models import db, User, Client, Case, Action, Document, CaseNote, CaseAction, AIInsight, Lawyer, Referral, Transcript, Deadline, EmailDraft
    from utils import get_pagination, apply_case_filters, get_sort_params, analyze_case, analyze_intake_text_scenarios
    from filters import time_ago, format_date, format_currency, pluralize
    from services.stt import STTService
    from services.letter_templates import LetterTemplateService

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

# Normalize SQLite path and ensure directory exists
basedir = os.path.dirname(os.path.abspath(__file__))
db_url = DATABASE_URL or 'sqlite:///legalintake.db'
if db_url.startswith('sqlite:///'):
    rel_path = db_url.replace('sqlite:///', '')
    abs_path = os.path.join(basedir, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    # Use forward slashes for SQLite URL
    abs_url_path = abs_path.replace('\\', '/')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{abs_url_path}'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url

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
LAW_FIRM_NAME = os.getenv('LAW_FIRM_NAME', 'Your Law Firm Name')
LAW_FIRM_CONTACT = os.getenv('LAW_FIRM_CONTACT', 'Address | Phone | Email')
EVIDENCE_RETENTION_DAYS = int(os.getenv('EVIDENCE_RETENTION_DAYS', 60))

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

# Import models for Flask-Migrate to detect (already imported above)

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
    # Upcoming deadlines (next 30 days)
    now = datetime.now()
    upcoming_deadlines = Deadline.query.filter(Deadline.due_date >= now, Deadline.due_date <= now + timedelta(days=30))\
        .order_by(Deadline.due_date.asc()).limit(5).all()
    
    return render_template(
        'dashboard.html',
        current_user=user,
        stats=stats,
        recent_cases=recent_cases,
        upcoming_actions=upcoming_actions,
        upcoming_deadlines=upcoming_deadlines
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

@app.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_auth
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        try:
            client.first_name = request.form.get('first_name', client.first_name)
            client.last_name = request.form.get('last_name', client.last_name)
            client.email = request.form.get('email', client.email)
            client.phone = request.form.get('phone', client.phone)
            client.address = request.form.get('address', client.address)
            client.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Client updated successfully!', 'success')
            return redirect(url_for('clients'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating client: {str(e)}', 'danger')
    return render_template('edit_client.html', client=client)

@app.route('/clients/<int:client_id>/delete')
@login_required
@requires_auth
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    try:
        db.session.delete(client)
        db.session.commit()
        flash('Client deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting client: {str(e)}', 'danger')
    return redirect(url_for('clients'))

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
    deadlines = Deadline.query.filter_by(case_id=case_id).order_by(Deadline.due_date.asc()).all()
    transcripts = Transcript.query.filter_by(case_id=case_id).order_by(Transcript.created_at.desc()).all()
    return render_template('view_case.html', case=case, documents=documents, deadlines=deadlines, transcripts=transcripts)

@app.route('/cases/<int:case_id>/notes', methods=['POST'])
@login_required
def add_case_note(case_id):
    case = db.session.get(Case, case_id)
    if case is None:
        abort(404, description="Case not found")
    content = request.form.get('note', '').strip()
    if not content:
        flash('Note cannot be empty.', 'warning')
        return redirect(url_for('view_case', case_id=case_id))
    try:
        note = CaseNote(
            content=content,
            is_private=False,
            case_id=case.id,
            created_by_id=session.get('user_id')
        )
        db.session.add(note)
        db.session.commit()
        flash('Note added.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding case note: {str(e)}")
        flash('Failed to add note.', 'danger')
    return redirect(url_for('view_case', case_id=case_id))

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
    
    # Get all cases and users for the template
    cases = Case.query.all()
    users = User.query.all()
    
    return render_template('actions.html', 
                         actions=actions, 
                         cases=cases,
                         users=users)

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

@app.route('/transcribe', methods=['GET', 'POST'])
@login_required
def transcribe():
    if request.method == 'POST':
        if 'audio_file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['audio_file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        if file:
            filename = secure_filename(file.filename or f"recording_{datetime.utcnow().timestamp()}.webm")
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(temp_path)
            try:
                service = STTService()
                transcript_id = service.start_transcription(temp_path)
                # persist transcript record (processing)
                t = Transcript(
                    provider='assemblyai',
                    external_id=transcript_id,
                    status='processing',
                    user_id=session.get('user_id')
                )
                db.session.add(t)
                db.session.commit()
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                return jsonify({'status': 'processing', 'transcript_id': transcript_id})
            except Exception as e:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                app.logger.error(f"Error processing audio file: {str(e)}")
                return jsonify({'error': str(e)}), 500
    return render_template('transcribe.html')

# ------- Scenario Automation Helpers ------- #
def _write_document(case_id, filename, content, uploaded_by_id):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    safe_name = secure_filename(filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    doc = Document(
        name=safe_name,
        file_path=file_path,
        file_type='text/plain',
        file_size=os.path.getsize(file_path),
        uploaded_by_id=uploaded_by_id,
        case_id=case_id,
        created_at=datetime.utcnow()
    )
    db.session.add(doc)
    return doc

def _auto_letters(category, analysis, client_name='[CLIENT]'):
    """Generate comprehensive letters using LetterTemplateService"""
    # Extract dates from analysis
    dates_info = analysis.get('dates', [])
    incident_date = datetime.utcnow().strftime('%Y-%m-%d')
    incident_time = '[TIME]'
    
    # Try to extract date and time from dates list
    if isinstance(dates_info, list) and dates_info:
        # Use first date found
        incident_date = dates_info[0] if dates_info[0] else incident_date
    
    # Extract key facts
    key_facts = analysis.get('key_facts', {})
    
    # Determine scenario type and generate letters
    if category.startswith('Personal Injury'):
        return LetterTemplateService.generate_all_letters_for_scenario(
            'slip_fall',
            client_name=client_name,
            incident_date=incident_date,
            incident_time=incident_time,
            analysis_summary=analysis.get('summary', '')
        )
    elif category.startswith('Car Accident'):
        insurance = key_facts.get('other_insurance', '[INSURANCE COMPANY]')
        location = key_facts.get('location', '[LOCATION]')
        return LetterTemplateService.generate_all_letters_for_scenario(
            'car_accident',
            client_name=client_name,
            accident_date=incident_date,
            location=location,
            insurance_company=insurance
        )
    elif category.startswith('Employment Law'):
        employer = key_facts.get('employer', '[EMPLOYER NAME]')
        return LetterTemplateService.generate_all_letters_for_scenario(
            'employment',
            client_name=client_name,
            employer_name=employer
        )
    elif category.startswith('Medical Malpractice'):
        hospital = key_facts.get('hospital', '[HOSPITAL NAME]')
        surgeon = key_facts.get('surgeon', '[SURGEON NAME]')
        procedure = key_facts.get('procedure', '[PROCEDURE TYPE]')
        return LetterTemplateService.generate_all_letters_for_scenario(
            'medical_malpractice',
            client_name=client_name,
            hospital_name=hospital,
            procedure_date=incident_date,
            surgeon_name=surgeon,
            procedure_type=procedure
        )
    return []

@app.route('/api/intake/auto', methods=['POST'])
@login_required
def auto_intake():
    """Create case, actions, and draft documents from raw intake text using scenario analyzer."""
    data = request.get_json()
    text = (data or {}).get('text') or ''
    client = (data or {}).get('client') or {}
    case_title = (data or {}).get('title') or 'Client Intake'

    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400

    try:
        # Find or create client (by email, then phone)
        db_client = None
        if client.get('email'):
            db_client = Client.query.filter_by(email=client['email']).first()
        if db_client is None and client.get('phone'):
            db_client = Client.query.filter_by(phone=client['phone']).first()
        if db_client is None:
            db_client = Client(
                first_name=client.get('first_name') or 'Client',
                last_name=client.get('last_name') or 'Unknown',
                email=client.get('email'),
                phone=client.get('phone'),
                address=client.get('address')
            )
            db.session.add(db_client)
            db.session.flush()

        # Analyze
        analysis = analyze_intake_text_scenarios(text)

        # Create case
        new_case = Case(
            title=case_title,
            description=text,
            case_type=analysis.get('category'),
            status='open',
            priority=(analysis.get('priority') or 'Medium').lower(),
            client_id=db_client.id,
            created_by_id=current_user.id,
            assigned_to_id=None,
        )
        db.session.add(new_case)
        db.session.flush()

        # Save AI insight
        insight = AIInsight(
            case_id=new_case.id,
            insight_text=f"{analysis.get('category')} | Urgency: {analysis.get('urgency')} | Dept: {analysis.get('department')}",
            category='scenario_analysis',
            confidence=None,
        )
        db.session.add(insight)

        # Create actions from suggested actions
        created_actions = []
        for text_action in (analysis.get('suggested_actions') or [])[:10]:
            action = Action(
                title=text_action,
                description='Auto-generated from scenario analysis',
                action_type='automation',
                status='pending',
                priority=(analysis.get('priority') or 'Medium').lower(),
                due_date=datetime.utcnow() + timedelta(days=1),
                assigned_to_id=None,
                created_by_id=current_user.id
            )
            db.session.add(action)
            db.session.flush()
            link = CaseAction(
                case_id=new_case.id,
                action_id=action.id,
                status='pending',
                assigned_to_id=None
            )
            db.session.add(link)
            created_actions.append(action.id)

        # Slip/Fall specific tasks
        if (analysis.get('category') or '').startswith('Personal Injury'):
            date_hint = analysis.get('dates', {}).get('incident_date') if isinstance(analysis.get('dates'), dict) else None
            time_hint = analysis.get('dates', {}).get('incident_time') if isinstance(analysis.get('dates'), dict) else None
            # Staff info request
            sf1 = Action(
                title=f"Request complete list of employees working on {date_hint or '[DATE]'} during {time_hint or '[TIME]'}",
                description='Ask for names of all staff on duty; who was responsible for cleaning/mopping; manager on duty and contact.',
                action_type='request',
                status='pending',
                priority='high',
                due_date=datetime.utcnow() + timedelta(days=1),
                assigned_to_id=None,
                created_by_id=current_user.id
            )
            db.session.add(sf1); db.session.flush()
            db.session.add(CaseAction(case_id=new_case.id, action_id=sf1.id, status='pending'))
            created_actions.append(sf1.id)

            # Security footage
            sf2 = Action(
                title='Obtain security footage (Produce, Entrance, Registers)',
                description='Request footage for 2 hours before and after incident; include camera identifiers if available.',
                action_type='evidence',
                status='pending',
                priority='high',
                due_date=datetime.utcnow() + timedelta(days=1),
                assigned_to_id=None,
                created_by_id=current_user.id
            )
            db.session.add(sf2); db.session.flush()
            db.session.add(CaseAction(case_id=new_case.id, action_id=sf2.id, status='pending'))
            created_actions.append(sf2.id)

            # Medical records checklist task
            sf3 = Action(
                title='Obtain medical records (see checklist)',
                description='Use the generated medical checklist document to collect required records.',
                action_type='records',
                status='pending',
                priority='medium',
                due_date=datetime.utcnow() + timedelta(days=2),
                assigned_to_id=None,
                created_by_id=current_user.id
            )
            db.session.add(sf3); db.session.flush()
            db.session.add(CaseAction(case_id=new_case.id, action_id=sf3.id, status='pending'))
            created_actions.append(sf3.id)

        # Create draft letters as documents (no email sent in dev)
        letters = _auto_letters(analysis.get('category') or '', analysis, client_name=f"{db_client.first_name} {db_client.last_name}")
        created_docs = []
        email_drafts_created = []
        for fname, content in letters:
            doc = _write_document(new_case.id, fname, content, uploaded_by_id=current_user.id)
            created_docs.append(doc.id)
            # Create a draft email per document (dev-only)
            try:
                draft = EmailDraft(
                    case_id=new_case.id,
                    to=None,
                    subject=f"Draft: {fname.replace('_', ' ').title()}",
                    body=f"Please review attached draft document: {fname}",
                    attachments=str(doc.id),
                    status='draft'
                )
                db.session.add(draft)
                db.session.flush()
                email_drafts_created.append(draft.id)
            except Exception:
                db.session.rollback()

        # Comprehensive Deadline Creation
        category = analysis.get('category', '')
        base_date = datetime.utcnow()
        
        # Try to extract incident date from analysis
        dates_list = analysis.get('dates', [])
        if isinstance(dates_list, list) and dates_list:
            try:
                # Try to parse first date
                base_date = datetime.strptime(dates_list[0], '%Y-%m-%d')
            except:
                pass
        
        # Personal Injury / Slip and Fall Deadlines
        if category.startswith('Personal Injury'):
            # Evidence preservation - URGENT
            evidence_deadline = base_date + timedelta(days=EVIDENCE_RETENTION_DAYS)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Security Footage Retention Deadline',
                due_date=evidence_deadline,
                source='slip_fall_evidence',
                notes=f'Security footage typically deleted after {EVIDENCE_RETENTION_DAYS} days. URGENT: Send preservation letter immediately.'
            ))
            
            # Statute of limitations (typically 2-3 years, using 2 years)
            statute_deadline = base_date + timedelta(days=730)  # 2 years
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Statute of Limitations',
                due_date=statute_deadline,
                source='statute_of_limitations',
                notes='Must file lawsuit before this date. Verify state-specific statute.'
            ))
            
            # Medical records collection
            medical_deadline = datetime.utcnow() + timedelta(days=14)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Medical Records Collection',
                due_date=medical_deadline,
                source='medical_records',
                notes='Obtain all medical records within 14 days.'
            ))
        
        # Car Accident Deadlines
        elif category.startswith('Car Accident'):
            # Police report request
            police_deadline = datetime.utcnow() + timedelta(days=7)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Police Report Request',
                due_date=police_deadline,
                source='police_report',
                notes='Request police report and dash cam footage within 7 days.'
            ))
            
            # Traffic camera footage
            camera_deadline = datetime.utcnow() + timedelta(days=30)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Traffic Camera Footage Deadline',
                due_date=camera_deadline,
                source='traffic_camera',
                notes='Traffic camera footage typically retained 30-90 days. Request immediately.'
            ))
            
            # Medical evaluation
            medical_eval_deadline = datetime.utcnow() + timedelta(days=2)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Medical Evaluation',
                due_date=medical_eval_deadline,
                source='medical_evaluation',
                notes='Schedule medical evaluation within 48 hours of accident.'
            ))
            
            # Statute of limitations
            statute_deadline = base_date + timedelta(days=730)  # 2 years typical
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Statute of Limitations',
                due_date=statute_deadline,
                source='statute_of_limitations',
                notes='Must file lawsuit before this date. Verify state-specific statute.'
            ))
        
        # Employment Law Deadlines
        elif category.startswith('Employment Law'):
            # EEOC filing deadline (180 days federal, 300 days in deferral states)
            eeoc_deadline = base_date + timedelta(days=180)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='EEOC Filing Deadline (Federal)',
                due_date=eeoc_deadline,
                source='eeoc_filing',
                notes='Must file EEOC charge within 180 days (300 days in deferral states). CRITICAL DEADLINE.'
            ))
            
            # Evidence preservation
            evidence_deadline = datetime.utcnow() + timedelta(days=7)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Send Litigation Hold Letter',
                due_date=evidence_deadline,
                source='employment_evidence',
                notes='Send litigation hold to employer immediately. Emails may be deleted.'
            ))
            
            # Personnel file request
            personnel_deadline = datetime.utcnow() + timedelta(days=14)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Personnel File Request',
                due_date=personnel_deadline,
                source='personnel_file',
                notes='Request complete personnel file within 14 days.'
            ))
        
        # Medical Malpractice Deadlines
        elif category.startswith('Medical Malpractice'):
            # Medical records - URGENT
            records_deadline = datetime.utcnow() + timedelta(days=7)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Medical Records Request (URGENT)',
                due_date=records_deadline,
                source='medical_records',
                notes='Request all medical records immediately. Include operative reports, count sheets, imaging.'
            ))
            
            # Expert witness retention
            expert_deadline = datetime.utcnow() + timedelta(days=30)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Retain Medical Expert Witness',
                due_date=expert_deadline,
                source='expert_witness',
                notes='Retain medical expert for case review and Certificate of Merit.'
            ))
            
            # Certificate of Merit (typically 60-90 days after filing)
            merit_deadline = datetime.utcnow() + timedelta(days=60)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Certificate of Merit',
                due_date=merit_deadline,
                source='certificate_of_merit',
                notes='Many states require Certificate of Merit within 60-90 days of filing. Verify state requirements.'
            ))
            
            # Statute of limitations (typically 1-2 years for med mal, using 2 years)
            statute_deadline = base_date + timedelta(days=730)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Statute of Limitations',
                due_date=statute_deadline,
                source='statute_of_limitations',
                notes='Medical malpractice has SHORT statute. May be 1-2 years. Verify state law and discovery rule.'
            ))
            
            # Discovery rule alternative (from date sponge was discovered)
            discovery_deadline = datetime.utcnow() + timedelta(days=365)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Discovery Rule Deadline',
                due_date=discovery_deadline,
                source='discovery_rule',
                notes='Alternative statute from date of discovery. Verify which date applies in your state.'
            ))

        db.session.commit()

        # Link latest transcript for this user to the new case/client (best effort)
        try:
            t = Transcript.query.filter_by(user_id=current_user.id).order_by(Transcript.created_at.desc()).first()
            if t and (t.case_id is None):
                t.case_id = new_case.id
                t.client_id = db_client.id
                db.session.commit()
        except Exception:
            db.session.rollback()

        return jsonify({
            'status': 'success',
            'case_id': new_case.id,
            'actions_created': created_actions,
            'documents_created': created_docs,
            'email_drafts_created': email_drafts_created,
            'analysis': analysis
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in auto_intake: {str(e)}")

@app.route('/documents/<int:document_id>')
@login_required
def view_document(document_id):
    document = db.session.get(Document, document_id)
    if document is None:
        abort(404, description="Document not found")
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        flash('File not found on server', 'error')
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

@app.route('/documents/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'document' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['document']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            try:
                # Create uploads directory if it doesn't exist
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                # Save the file
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Create document record
                document = Document(
                    name=filename,
                    file_path=file_path,
                    file_type=file.mimetype,
                    file_size=os.path.getsize(file_path),
                    uploaded_by_id=current_user.id,
                    created_at=datetime.utcnow()
                )
                
                # If case_id is provided in the form, associate the document with the case
                case_id = request.form.get('case_id')
                if case_id:
                    document.case_id = case_id
                
                db.session.add(document)
                db.session.commit()
                
                flash('Document uploaded successfully!', 'success')
                return redirect(request.referrer or url_for('documents'))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Error uploading document: {str(e)}')
                flash('Error uploading document', 'error')
                return redirect(request.url)
    
    # If GET request, show the upload form
    return redirect(url_for('documents'))

@app.route('/documents/delete/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    document = db.session.get(Document, document_id)
    if document is None:
        abort(404, description="Document not found")
    
    # Check if the current user is authorized to delete this document
    if document.uploaded_by != current_user.id and not current_user.is_admin:
        flash('You are not authorized to delete this document', 'error')
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
        flash('Error deleting document', 'error')
    
    return redirect(url_for('documents'))

@app.route('/api/cases', methods=['POST'])
@login_required
def create_case():
    """Create a new case from the intake form with rule-based analysis."""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['client_first_name', 'client_last_name', 'case_title', 'case_description']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Create or find client (prefer by email if provided)
        client = None
        if data.get('client_email'):
            client = Client.query.filter_by(email=data['client_email']).first()
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
        
        # Analyze the case using rule-based approach
        case_description = data['case_description']
        analysis = analyze_case(case_description)
        
        # Create case with analysis insights
        new_case = Case(
            title=data['case_title'],
            description=case_description,
            case_type=analysis.get('category', 'other'),
            status='open',
            priority=data.get('priority', 'high' if analysis.get('risk_level') == 'high' else 'medium'),
            client_id=client.id,
            created_by_id=current_user.id,
            assigned_to_id=data.get('assigned_to')
        )
        db.session.add(new_case)
        db.session.flush()
        
        # Save analysis to the database
        insight = AIInsight(
            case_id=new_case.id,
            insight_text=analysis.get('summary', 'No analysis available'),
            category=analysis.get('category', 'other'),
            confidence=analysis.get('confidence', 0.0),
            metadata={
                'risk_level': analysis.get('risk_level'),
                'entities': analysis.get('entities', {})
            }
        )
        db.session.add(insight)
        
        # Add suggested actions
        for action_text in analysis.get('suggested_actions', [])[:5]:
            action = Action.query.filter_by(title=action_text).first()
            if not action:
                action = Action(
                    title=action_text,
                    action_type='suggested',
                    description='Suggested action based on case analysis',
                    created_by_id=current_user.id
                )
                db.session.add(action)
                db.session.flush()
            
            case_action = CaseAction(
                case_id=new_case.id,
                action_id=action.id,
                status='pending',
                assigned_to_id=current_user.id,
                notes='Automatically added by case analysis'
            )
            db.session.add(case_action)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Case created successfully with analysis',
            'case_id': new_case.id,
            'analysis': {
                'category': analysis.get('category'),
                'risk_level': analysis.get('risk_level'),
                'summary': analysis.get('summary'),
                'suggested_actions': analysis.get('suggested_actions', [])
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating case: {str(e)}")
        return jsonify({'error': f'Failed to create case: {str(e)}'}), 500

# Poll AssemblyAI for transcription status/text
@app.route('/transcribe/status/<transcript_id>', methods=['GET'])
@login_required
def transcription_status(transcript_id):
    try:
        service = STTService()
        data = service.get_transcription_status(transcript_id)
        # Update transcript persistence
        t = Transcript.query.filter_by(external_id=transcript_id).first()
        if t is None:
            t = Transcript(provider='assemblyai', external_id=transcript_id)
            db.session.add(t)
        t.status = data.get('status') or t.status
        if data.get('status') == 'completed':
            t.text = data.get('text') or ''
        if data.get('status') == 'error':
            # store error state
            t.status = 'error'
        db.session.commit()
        # Shape response
        resp = {
            'status': data.get('status'),
            'id': data.get('id'),
        }
        if data.get('status') == 'completed':
            resp['text'] = data.get('text', '')
            resp['entities'] = data.get('entities')
            resp['sentiment_analysis'] = data.get('sentiment_analysis')
            resp['auto_highlights'] = data.get('auto_highlights')
            resp['iab_categories'] = data.get('iab_categories')
        elif data.get('status') == 'error':
            resp['error'] = data.get('error')
        return jsonify(resp)
    except Exception as e:
        app.logger.error(f"Error fetching transcription status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cases/<int:case_id>', methods=['GET'])
def get_case(case_id):
    """Get case details by ID."""
    case = db.session.get(Case, case_id)
    if case is None:
        abort(404, description="Case not found")
    return jsonify(case.to_dict())

@app.route('/cases/<int:case_id>/ai-insights')
@login_required
def case_ai_insights(case_id):
    """Display AI insights for a case."""
    case = db.session.get(Case, case_id)
    if case is None:
        abort(404, description="Case not found")
    
    # Get all AI insights for this case, ordered by creation date (newest first)
    insights = AIInsight.query.filter_by(case_id=case_id)\
                            .order_by(AIInsight.created_at.desc())\
                            .all()
    
    # Convert insights to dict and add any additional processing
    insights_data = []
    for insight in insights:
        insight_dict = insight.to_dict()
        # Parse the insight text to extract structured data if needed
        # This is a simplified example - you might need to adjust based on your data structure
        insight_dict['suggested_actions'] = getattr(insight, 'suggested_actions', [])
        insight_dict['entities'] = getattr(insight, 'entities', [])
        insights_data.append(insight_dict)
    
    return render_template('ai_insights.html', 
                         case=case, 
                         insights=insights_data)

@app.route('/api/cases/<int:case_id>/analyze', methods=['POST'])
@login_required
def analyze_case_endpoint(case_id):
    """Analyze a case using rule-based analysis and return insights."""
    case = db.session.get(Case, case_id)
    if case is None:
        return jsonify({'error': 'Case not found'}), 404
    
    try:
        # Get the case description
        description = case.description or ''
        
        # Analyze the case
        analysis = analyze_case(description)
        
        # Save the insight to the database
        insight = AIInsight(
            case_id=case.id,
            insight_text=analysis.get('summary', 'No analysis available'),
            category=analysis.get('category', 'other'),
            confidence=analysis.get('confidence', 0.0),
            metadata={
                'risk_level': analysis.get('risk_level'),
                'entities': analysis.get('entities', {})
            }
        )
        db.session.add(insight)
        
        # Update the case category if not already set
        if not case.category and analysis.get('category'):
            case.category = analysis['category']
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Case analyzed successfully',
            'analysis': analysis
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error analyzing case: {str(e)}")
        return jsonify({'error': f'Failed to analyze case: {str(e)}'}), 500

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
            flash(f'Error adding client: {str(e)}', 'error')
    
    return render_template('add_client.html')

# Email Drafts Routes
@app.route('/email/drafts')
@login_required
@requires_auth
def email_drafts():
    """View all email drafts"""
    drafts = EmailDraft.query.order_by(EmailDraft.created_at.desc()).all()
    return render_template('email_drafts.html', drafts=drafts)

@app.route('/email/drafts/<int:draft_id>')
@login_required
@requires_auth
def view_email_draft(draft_id):
    """View a specific email draft"""
    draft = db.session.get(EmailDraft, draft_id)
    if draft is None:
        abort(404, description="Email draft not found")
    return render_template('email_draft_detail.html', draft=draft)

@app.route('/email/drafts/<int:draft_id>/send', methods=['POST'])
@login_required
@requires_auth
def send_email_draft(draft_id):
    """Mark an email draft as sent (actual sending would require SMTP configuration)"""
    draft = db.session.get(EmailDraft, draft_id)
    if draft is None:
        abort(404, description="Email draft not found")
    
    try:
        # In production, this would actually send the email via SMTP/SendGrid
        # For now, we just mark it as sent
        draft.status = 'sent'
        draft.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Email marked as sent. (Note: Actual email sending requires SMTP configuration)', 'success')
        return redirect(url_for('email_drafts'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error sending email draft: {str(e)}')
        flash('Error sending email', 'error')
        return redirect(url_for('view_email_draft', draft_id=draft_id))

@app.route('/email/drafts/<int:draft_id>/delete', methods=['POST'])
@login_required
@requires_auth
def delete_email_draft(draft_id):
    """Delete an email draft"""
    draft = db.session.get(EmailDraft, draft_id)
    if draft is None:
        abort(404, description="Email draft not found")
    
    try:
        db.session.delete(draft)
        db.session.commit()
        flash('Email draft deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting email draft: {str(e)}')
        flash('Error deleting email draft', 'error')
    
    return redirect(url_for('email_drafts'))

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
