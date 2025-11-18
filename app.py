from __future__ import annotations
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
try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover
    BackgroundScheduler = None
import smtplib
import ssl
try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None

# Support both package and script imports
try:
    # Package-relative imports (when FLASK_APP=law_firm_intake.app)
    from .models import db, User, Client, Case, Action, Document, CaseNote, CaseAction, AIInsight, Transcript, Deadline, EmailDraft, EmailQueue, ClientUser, ClientDocumentAccess, ClientMessage, TimeEntry, Expense, Invoice, Payment, TrustAccount, CalendarEvent, NotificationPreference, Intent, IntentRule, ActionTemplate, EmailTemplate, AnalyzerLog, CaseStatusAudit
    from .utils import get_pagination, apply_case_filters, get_sort_params, analyze_case, analyze_intake_text_scenarios
    from .services.analyzer_assemblyai import analyze_with_aai
    from .filters import time_ago, format_date, format_currency, pluralize
    from .services.stt import STTService
    from .services.letter_templates import LetterTemplateService
except ImportError:  # pragma: no cover
    # Fallback for running as a script (python app.py)
    from models import db, User, Client, Case, Action, Document, CaseNote, CaseAction, AIInsight, Transcript, Deadline, EmailDraft, EmailQueue, ClientUser, ClientDocumentAccess, ClientMessage, TimeEntry, Expense, Invoice, Payment, TrustAccount, CalendarEvent, NotificationPreference, Intent, IntentRule, ActionTemplate, EmailTemplate, AnalyzerLog, CaseStatusAudit
    from utils import get_pagination, apply_case_filters, get_sort_params, analyze_case, analyze_intake_text_scenarios
    from services.analyzer_assemblyai import analyze_with_aai
    from filters import time_ago, format_date, format_currency, pluralize
    from services.stt import STTService
    from services.letter_templates import LetterTemplateService

# Load environment variables
load_dotenv()

# AssemblyAI Configuration
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
USE_AAI_ANALYZER = (os.getenv('USE_AAI_ANALYZER', 'false').strip().lower() == 'true')
LOG_ANALYZER_METRICS = (os.getenv('LOG_ANALYZER_METRICS', 'false').strip().lower() == 'true')
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
# Use environment variables so production/staging can override defaults safely
AUTH_USERNAME = os.getenv('FLASK_BASIC_USER', 'demo')
AUTH_PASSWORD = os.getenv('FLASK_BASIC_PASS', 'themiscore123')  # Change this in production

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

# Resolve current user id for API writes. Falls back to first user when no session.
def _current_user_id():
    try:
        uid = session.get('user_id')
    except Exception:
        uid = None
    if uid:
        return uid
    try:
        u = User.query.first()
        return u.id if u else None
    except Exception:
        return None


def apply_ai_classification_to_case(case, ai_data: dict) -> None:
    """Apply AI classification JSON to a Case, including CaseType linkage.

    Expected ai_data["classification"] subset:
        {
            "case_type_key": "civil_tort_premises_liability",
            "primary_category": "civil",
            "subcategory": "...",
            "matter_type": "...",
            "urgency": "high",
            "confidence": 0.9,
            "issue_tags": [...]
        }
    """
    classification = ai_data.get("classification") or {}

    # High-level category on Case
    primary_category = classification.get("primary_category")
    if primary_category:
        case.category = primary_category

    # Structured case type taxonomy linkage
    case_type_key = classification.get("case_type_key")
    if case_type_key:
        try:
            ct = CaseType.query.filter_by(key=case_type_key, active=True).first()
        except Exception:
            ct = None
        if ct:
            case.case_type_id = ct.id
            # Optional: keep legacy string field in sync for now
            if not case.case_type:
                case.case_type = ct.label

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
ALLOWED_AUDIO_EXTENSIONS = {'webm', 'wav', 'mp3', 'm4a', 'mp4', 'ogg'}

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
if stripe and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# ---------------- Email sending (SMTP with mock fallback) ---------------- #
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
SMTP_FROM = os.getenv('SMTP_FROM') or os.getenv('SMTP_USER')

def _send_email(to_email: str, subject: str, body: str):
    if SMTP_HOST and SMTP_FROM:
        try:
            msg = f"From: {SMTP_FROM}\r\nTo: {to_email}\r\nSubject: {subject}\r\n\r\n{body}"
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.ehlo()
                try:
                    server.starttls(context=context)
                    server.ehlo()
                except Exception:
                    pass
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM, [to_email] if to_email else [SMTP_FROM], msg)
            current_app.logger.info(f"[SMTP EMAIL] To={to_email or 'n/a'} | Subject={subject}")
            return
        except Exception as e:
            current_app.logger.error(f"SMTP send failed: {str(e)}; falling back to mock.")
    current_app.logger.info(f"[MOCK EMAIL] To={to_email or 'n/a'} | Subject={subject} | Body={body}")

def _check_calendar_reminders():
    with app.app_context():
        now = datetime.utcnow()
        window = now + timedelta(minutes=1)
        # Upcoming events; we'll compute per-event reminder window and skip already-notified
        events = db.session.query(CalendarEvent).filter(
            CalendarEvent.reminder_minutes_before > 0,
            CalendarEvent.start_at != None
        ).all()
        for ev in events:
            try:
                if not ev.start_at:
                    continue
                # Preferences override minutes_before if present (by client)
                pref = None
                if ev.client_id:
                    pref = NotificationPreference.query.filter_by(client_id=ev.client_id).first()
                minutes_before = pref.minutes_before if pref and pref.minutes_before is not None else ev.reminder_minutes_before
                email_enabled = pref.email_enabled if pref is not None else True
                if not email_enabled:
                    continue
                remind_at = ev.start_at - timedelta(minutes=minutes_before)
                if remind_at <= window and remind_at >= now:
                    # Skip if already notified recently for this window
                    if ev.last_notified_at and ev.last_notified_at >= remind_at:
                        continue
                    # Derive recipient: client's email if available
                    to_email = ev.client.email if getattr(ev, 'client', None) and ev.client and ev.client.email else None
                    subject = f"Reminder: {ev.title} at {ev.start_at.strftime('%Y-%m-%d %H:%M')}"
                    body = f"Event: {ev.title}\nCase: {ev.case.title if ev.case else '-'}\nLocation: {ev.location or '-'}"
                    _send_email(to_email, subject, body)
                    ev.last_notified_at = now
                    db.session.add(ev)
                    db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Reminder job error for event {getattr(ev, 'id', '?')}: {str(e)}")

_scheduler = None
def _process_email_queue():
    """Background job to process pending EmailQueue items."""
    with app.app_context():
        now = datetime.utcnow()
        try:
            items = (
                db.session.query(EmailQueue)
                .filter(EmailQueue.status == 'pending')
                .filter(EmailQueue.send_after <= now)
                .order_by(EmailQueue.created_at.asc())
                .limit(25)
                .all()
            )
            for item in items:
                try:
                    _send_email(item.to, item.subject, item.body)
                    item.status = 'sent'
                    item.attempts = (item.attempts or 0) + 1
                    item.last_error = None
                    item.updated_at = now
                    db.session.add(item)
                    db.session.commit()
                except Exception as e:
                    item.status = 'failed'
                    item.attempts = (item.attempts or 0) + 1
                    item.last_error = str(e)
                    item.updated_at = now
                    db.session.add(item)
                    db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Email queue processor error: {str(e)}")

def _start_scheduler_once():
    global _scheduler
    if _scheduler is not None:
        return
    if BackgroundScheduler is None:
        app.logger.warning('APScheduler not installed; reminder job disabled.')
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_check_calendar_reminders, 'interval', minutes=1, id='calendar_reminders')
    _scheduler.add_job(_process_email_queue, 'interval', minutes=1, id='email_queue_processor')
    _scheduler.start()

# Start scheduler only on the reloader main process
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    try:
        _start_scheduler_once()
        if BackgroundScheduler:
            app.logger.info('APScheduler started for calendar reminders.')
    except Exception as e:
        app.logger.error(f'Failed to start scheduler: {str(e)}')

# Register template filters
app.jinja_env.filters['time_ago'] = time_ago
app.jinja_env.filters['format_date'] = format_date
app.jinja_env.filters['format_currency'] = format_currency
app.jinja_env.filters['pluralize'] = pluralize

# Import models for Flask-Migrate to detect (already imported above)

NEXT_BASE_URL = os.getenv('NEXT_BASE_URL')  # e.g. https://your-next.app
# Redirect legacy HTML pages to Next.js (only when NEXT_BASE_URL is configured)
@app.before_request
def _redirect_legacy_to_next():
    try:
        if not NEXT_BASE_URL:
            return None
        if request.method != 'GET':
            return None
        path = request.path.rstrip('/') or '/'
        # Do not redirect auth endpoints or the site root
        if path in ('/', '/login', '/logout', '/portal/login'):
            return None
        base = NEXT_BASE_URL.rstrip('/')
        mapping = {
            '/dashboard': f'{base}/dashboard',
            '/cases': f'{base}/cases',
            '/clients': f'{base}/clients',
            '/actions': f'{base}/actions',
            '/documents': f'{base}/documents',
            '/calendar': f'{base}/calendar',
            '/billing': f'{base}/billing',
            '/portal/invoices': f'{base}/portal/invoices',
            '/portal/payments': f'{base}/portal/payments',
            '/portal/documents': f'{base}/portal/documents',
        }
        target = mapping.get(path)
        if target:
            return redirect(target, code=302)
    except Exception:
        return None
    return None

# Login manager setup
from flask_login import LoginManager, login_required, current_user

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

# -------- Client Portal auth helpers (must be defined before portal routes) -------- #
def portal_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'client_user_id' not in session:
            abort(403)
        return f(*args, **kwargs)
    return decorated

def _get_portal_client_id():
    cu_id = session.get('client_user_id')
    if not cu_id:
        return None
    cu = db.session.get(ClientUser, cu_id)
    return cu.client_id if cu else None

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

def _is_allowed_audio(filename: str, content_type: str) -> bool:
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if ext in ALLOWED_AUDIO_EXTENSIONS:
        return True
    if content_type and content_type.startswith(('audio/', 'video/')):
        return True
    return False

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
    # Decommissioned Flask login UI: delegate to Next.js staff console login
    base = os.getenv('NEXT_BASE_URL')
    if base:
        return redirect(base.rstrip('/') + '/login', code=302)
    # Fallback for local dev
    return redirect('http://localhost:3000/login', code=302)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    # Redirect to Next.js staff console login
    base = os.getenv('NEXT_BASE_URL')
    if base:
        return redirect(base.rstrip('/') + '/login', code=302)
    return redirect('http://localhost:3000/login', code=302)

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
    # Redirect to Next.js client detail page
    return redirect(f"http://localhost:3000/clients/{client_id}", code=301)

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

# ---- Billing Routes ----
@app.route('/billing/invoices')
@login_required
@requires_auth
def billing_invoices():
    return redirect(url_for('billing'))

@app.route('/billing/time-entries')
@login_required
@requires_auth
def billing_time_entries():
    return redirect(url_for('billing'))

@app.route('/billing/expenses')
@login_required
@requires_auth
def billing_expenses():
    return redirect(url_for('billing'))

@app.route('/billing')
@login_required
@requires_auth
def billing():
    invoices = Invoice.query.options(db.joinedload(Invoice.client), db.joinedload(Invoice.case)).order_by(Invoice.created_at.desc()).all()
    entries = TimeEntry.query.options(db.joinedload(TimeEntry.user), db.joinedload(TimeEntry.case), db.joinedload(TimeEntry.invoice)).order_by(TimeEntry.created_at.desc()).all()
    expenses = Expense.query.options(db.joinedload(Expense.user), db.joinedload(Expense.case), db.joinedload(Expense.invoice)).order_by(Expense.created_at.desc()).all()
    return render_template('billing.html', invoices=invoices, entries=entries, expenses=expenses)

# ---- Client Portal (read-only demo) ----
@app.route('/portal/invoices')
@portal_login_required
def portal_invoices():
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    invoices = Invoice.query.options(db.joinedload(Invoice.client), db.joinedload(Invoice.case)).filter(Invoice.client_id==client_id).order_by(Invoice.created_at.desc()).all()
    return render_template('portal_invoices.html', invoices=invoices)

@app.route('/portal/payments')
@portal_login_required
def portal_payments():
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    payments = Payment.query.join(Invoice, Payment.invoice_id==Invoice.id).filter(Invoice.client_id==client_id).options(db.joinedload(Payment.invoice)).order_by(Payment.payment_date.desc()).all()
    return render_template('portal_payments.html', payments=payments)

@app.route('/portal/documents')
@portal_login_required
def portal_documents():
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    accesses = ClientDocumentAccess.query.filter_by(client_id=client_id).options(db.joinedload(ClientDocumentAccess.document), db.joinedload(ClientDocumentAccess.client)).order_by(ClientDocumentAccess.granted_at.desc()).all()
    return render_template('portal_documents.html', accesses=accesses)

# ---- Client Portal JSON APIs ----
@app.route('/api/portal/invoices', methods=['GET'])
@portal_login_required
def api_portal_invoices():
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    invoices = (
        Invoice.query
        .options(db.joinedload(Invoice.client), db.joinedload(Invoice.case))
        .filter(Invoice.client_id == client_id)
        .order_by(Invoice.created_at.desc())
        .all()
    )
    def inv_to_dict(inv: Invoice):
        return {
            'id': inv.id,
            'invoice_number': getattr(inv, 'invoice_number', None),
            'status': getattr(inv, 'status', None),
            'total_amount': float(getattr(inv, 'total_amount', 0) or 0),
            'balance_due': float(getattr(inv, 'balance_due', 0) or 0),
            'created_at': inv.created_at.isoformat() if getattr(inv, 'created_at', None) else None,
            'case': {
                'id': inv.case.id if getattr(inv, 'case', None) else None,
                'title': getattr(inv.case, 'title', None) if getattr(inv, 'case', None) else None,
            },
        }
    return jsonify([inv_to_dict(i) for i in invoices])

@app.route('/api/portal/payments', methods=['GET'])
@portal_login_required
def api_portal_payments():
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    payments = (
        Payment.query
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.client_id == client_id)
        .options(db.joinedload(Payment.invoice))
        .order_by(Payment.payment_date.desc())
        .all()
    )
    def pay_to_dict(p: Payment):
        return {
            'id': p.id,
            'amount': float(getattr(p, 'amount', 0) or 0),
            'payment_date': p.payment_date.isoformat() if getattr(p, 'payment_date', None) else None,
            'payment_method': getattr(p, 'payment_method', None),
            'status': getattr(p, 'status', None),
            'reference_number': getattr(p, 'reference_number', None),
            'invoice': {
                'id': p.invoice.id if getattr(p, 'invoice', None) else None,
                'invoice_number': getattr(p.invoice, 'invoice_number', None) if getattr(p, 'invoice', None) else None,
            },
        }
    return jsonify([pay_to_dict(p) for p in payments])

@app.route('/api/portal/documents', methods=['GET'])
@portal_login_required
def api_portal_documents():
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    case_id = request.args.get('case_id', type=int)
    q = (
        ClientDocumentAccess.query
        .filter_by(client_id=client_id)
        .options(db.joinedload(ClientDocumentAccess.document), db.joinedload(ClientDocumentAccess.client))
        .order_by(ClientDocumentAccess.granted_at.desc())
    )
    if case_id:
        q = q.join(Document, ClientDocumentAccess.document_id == Document.id).filter(Document.case_id == case_id)
    accesses = q.all()
    def acc_to_dict(a: ClientDocumentAccess):
        doc = getattr(a, 'document', None)
        return {
            'id': a.id,
            'granted_at': a.granted_at.isoformat() if getattr(a, 'granted_at', None) else None,
            'document': {
                'id': doc.id if doc else None,
                'name': getattr(doc, 'name', None) if doc else None,
                'file_type': getattr(doc, 'file_type', None) if doc else None,
                'uploaded_by_id': getattr(doc, 'uploaded_by_id', None) if doc else None,
                'created_at': doc.created_at.isoformat() if (doc and getattr(doc, 'created_at', None)) else None,
            }
        }
    return jsonify([acc_to_dict(a) for a in accesses])

@app.route('/api/portal/cases', methods=['GET'])
@portal_login_required
def api_portal_cases():
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    cases = Case.query.filter_by(client_id=client_id).order_by(Case.created_at.desc()).all()
    return jsonify([
        {
            'id': c.id,
            'title': c.title,
            'status': c.status,
            'created_at': c.created_at.isoformat() if getattr(c, 'created_at', None) else None,
        }
        for c in cases
    ])

@app.route('/api/portal/cases/<int:case_id>', methods=['GET'])
@portal_login_required
def api_portal_case_detail(case_id: int):
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    c = db.session.get(Case, case_id)
    if not c or c.client_id != client_id:
        abort(404)
    # Deadlines for case
    deadlines = (Deadline.query
                 .filter_by(case_id=case_id)
                 .order_by(Deadline.due_date.asc())
                 .limit(50)
                 .all())
    # Documents accessible to this client for this case
    doc_accesses = (ClientDocumentAccess.query
                    .join(Document, ClientDocumentAccess.document_id == Document.id)
                    .filter(ClientDocumentAccess.client_id == client_id, Document.case_id == case_id)
                    .options(db.joinedload(ClientDocumentAccess.document))
                    .order_by(ClientDocumentAccess.granted_at.desc())
                    .limit(50)
                    .all())
    # Messages for this case
    messages = (ClientMessage.query
                .filter_by(client_id=client_id, case_id=case_id)
                .order_by(ClientMessage.created_at.desc())
                .limit(100)
                .all())
    return jsonify({
        'id': c.id,
        'title': c.title,
        'status': c.status,
        'created_at': c.created_at.isoformat() if getattr(c, 'created_at', None) else None,
        'deadlines': [
            {
                'id': d.id,
                'name': d.name,
                'due_date': d.due_date.isoformat() if getattr(d, 'due_date', None) else None,
                'source': getattr(d, 'source', None),
                'notes': getattr(d, 'notes', None),
            } for d in deadlines
        ],
        'documents': [
            {
                'id': a.id,
                'granted_at': a.granted_at.isoformat() if getattr(a, 'granted_at', None) else None,
                'document': {
                    'id': a.document.id if getattr(a, 'document', None) else None,
                    'name': getattr(a.document, 'name', None) if getattr(a, 'document', None) else None,
                    'file_type': getattr(a.document, 'file_type', None) if getattr(a, 'document', None) else None,
                    'created_at': a.document.created_at.isoformat() if (getattr(a, 'document', None) and getattr(a.document, 'created_at', None)) else None,
                }
            } for a in doc_accesses
        ],
        'messages': [
            {
                'id': m.id,
                'from_client': m.from_client,
                'subject': m.subject,
                'message': m.message,
                'created_at': m.created_at.isoformat() if m.created_at else None,
            } for m in messages
        ]
    })

@app.route('/api/portal/timeline', methods=['GET'])
@portal_login_required
def api_portal_timeline():
    try:
        client_id = _get_portal_client_id()
        if not client_id:
            abort(403)
        # Optional query: case_id, pagination
        case_id = request.args.get('case_id', type=int)
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=25, type=int)
        per_page = max(1, min(per_page, 200))
        items = []
        # Status changes
        q_status = (CaseStatusAudit.query
                    .join(Case, CaseStatusAudit.case_id == Case.id)
                    .filter(Case.client_id == client_id)
                    .order_by(CaseStatusAudit.created_at.desc()))
        if case_id:
            q_status = q_status.filter(CaseStatusAudit.case_id == case_id)
        for a in q_status.all():
            items.append({
                'type': 'status_change',
                'case_id': a.case_id,
                'at': a.created_at.isoformat() if a.created_at else None,
                'data': {
                    'from': a.from_status,
                    'to': a.to_status,
                }
            })
        # Messages
        q_msgs = ClientMessage.query.filter(ClientMessage.client_id == client_id).order_by(ClientMessage.created_at.desc())
        if case_id:
            q_msgs = q_msgs.filter(ClientMessage.case_id == case_id)
        for m in q_msgs.all():
            items.append({
                'type': 'message',
                'case_id': m.case_id,
                'at': m.created_at.isoformat() if m.created_at else None,
                'data': {
                    'from_client': m.from_client,
                    'subject': m.subject,
                    'message': m.message,
                }
            })
        # Document access grants
        q_docs = (ClientDocumentAccess.query
                  .join(Document, ClientDocumentAccess.document_id == Document.id)
                  .filter(ClientDocumentAccess.client_id == client_id)
                  .order_by(ClientDocumentAccess.granted_at.desc()))
        if case_id:
            q_docs = q_docs.join(Case, Document.case_id == Case.id).filter(Case.id == case_id)
        for acc in q_docs.all():
            items.append({
                'type': 'document',
                'case_id': acc.document.case_id if getattr(acc, 'document', None) else None,
                'at': acc.granted_at.isoformat() if acc.granted_at else None,
                'data': {
                    'name': getattr(acc.document, 'name', None) if getattr(acc, 'document', None) else None,
                }
            })
        # Invoices and payments
        q_invoices = Invoice.query.filter(Invoice.client_id == client_id).order_by(Invoice.created_at.desc())
        if case_id:
            q_invoices = q_invoices.filter(Invoice.case_id == case_id)
        for inv in q_invoices.all():
            items.append({
                'type': 'invoice',
                'case_id': inv.case_id,
                'at': inv.created_at.isoformat() if getattr(inv, 'created_at', None) else None,
                'data': {
                    'invoice_number': getattr(inv, 'invoice_number', None),
                    'status': getattr(inv, 'status', None),
                    'total_amount': float(getattr(inv, 'total_amount', 0) or 0),
                }
            })
        q_pay = (Payment.query
                 .join(Invoice, Payment.invoice_id == Invoice.id)
                 .filter(Invoice.client_id == client_id)
                 .order_by(Payment.payment_date.desc()))
        if case_id:
            q_pay = q_pay.filter(Invoice.case_id == case_id)
        for p in q_pay.all():
            items.append({
                'type': 'payment',
                'case_id': getattr(p.invoice, 'case_id', None) if getattr(p, 'invoice', None) else None,
                'at': p.payment_date.isoformat() if getattr(p, 'payment_date', None) else None,
                'data': {
                    'amount': float(getattr(p, 'amount', 0) or 0),
                    'status': getattr(p, 'status', None),
                }
            })
        # Sort merged items by datetime desc
        def sort_key(it):
            return it.get('at') or ''
        items.sort(key=sort_key, reverse=True)
        total = len(items)
        start = max(0, (page - 1) * per_page)
        end = min(total, start + per_page)
        slice_items = items[start:end]
        return jsonify({
            'items': slice_items,
            'page': page,
            'per_page': per_page,
            'total': total,
            'has_more': end < total
        })
    except Exception as e:
        app.logger.error(f"Error in api_portal_timeline: {str(e)}")
        return jsonify({'error': 'failed'}), 500
@app.route('/api/portal/messages', methods=['GET'])
@portal_login_required
def api_portal_messages_list():
    try:
        client_id = _get_portal_client_id()
        if not client_id:
            abort(403)
        case_id = request.args.get('case_id', type=int)
        limit = request.args.get('limit', type=int) or 100
        q = (ClientMessage.query
             .filter(ClientMessage.client_id == client_id)
             .order_by(ClientMessage.created_at.desc()))
        if case_id:
            q = q.filter(ClientMessage.case_id == case_id)
        msgs = q.limit(min(limit, 500)).all()

        def to_dict(m: ClientMessage):
            return {
                'id': m.id,
                'case_id': m.case_id,
                'from_client': m.from_client,
                'subject': m.subject,
                'message': m.message,
                'read': m.read,
                'created_at': m.created_at.isoformat() if m.created_at else None,
            }

        return jsonify([to_dict(m) for m in msgs])
    except Exception as e:
        app.logger.error(f"Error in api_portal_messages_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500


@app.route('/api/portal/intake/save', methods=['POST'])
@portal_login_required
def api_portal_intake_save():
    try:
        client_id = _get_portal_client_id()
        if not client_id:
            abort(403)
        data = request.get_json(silent=True) or {}
        transcript_text = (data.get('transcript') or '').strip()
        analysis = data.get('analysis') or {}
        title = (data.get('title') or 'Client Voice Intake').strip()
        # Create a new case for this client
        creator_id = _current_user_id()
        case = Case(
            title=title or 'Client Voice Intake',
            description='Created from client portal intake',
            status='open',
            priority=str(analysis.get('urgency') or 'medium'),
            category=analysis.get('category'),
            client_id=client_id,
            created_by_id=creator_id or None,
        )
        db.session.add(case)
        db.session.flush()

        # Apply taxonomy-aware classification mapping (if present)
        try:
            classification = {
                "primary_category": analysis.get("category"),
                "case_type_key": analysis.get("case_type_key"),
                "urgency": analysis.get("urgency"),
                "confidence": analysis.get("confidence"),
            }
            apply_ai_classification_to_case(case, {"classification": classification})
        except Exception:
            # Do not break intake flow if AI mapping fails
            pass
        # Save transcript if provided
        try:
            if transcript_text:
                t = Transcript(case_id=case.id, text=transcript_text)
                db.session.add(t)
        except Exception:
            pass
        # Save a concise insight record
        try:
            summary = {
                'category': analysis.get('category'),
                'urgency': analysis.get('urgency'),
                'key_facts': analysis.get('key_facts'),
                'dates': analysis.get('dates'),
                'parties': analysis.get('parties'),
            }
            ai = AIInsight(case_id=case.id, insight_text=str(summary), category='intake', confidence=None)
            db.session.add(ai)
        except Exception:
            pass
        # Optional: materialize deadlines from analysis.dates (best-effort)
        try:
            dates = analysis.get('dates') or []
            for d in dates:
                name = str(d.get('label') or 'Key date')
                value = d.get('value')
                dt = None
                try:
                    # Accept YYYY-MM-DD or ISO
                    dt = datetime.fromisoformat(value)
                except Exception:
                    dt = None
                if dt:
                    dl = Deadline(case_id=case.id, name=name, due_date=dt, source='intake_analysis')
                    db.session.add(dl)
        except Exception:
            pass
        db.session.commit()
        return jsonify({'ok': True, 'case_id': case.id})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_portal_intake_save: {str(e)}")
        return jsonify({'error': 'failed'}), 500


def _slip_fall_build_preview(case: Case, analysis: dict | None = None):
    # Basic defaults; can be extended with templates later
    today = datetime.utcnow().date()
    tasks = [
        {'title': 'Send evidence preservation letter', 'priority': 'high'},
        {'title': 'Request incident report and staff info', 'priority': 'high'},
        {'title': 'Obtain security footage', 'priority': 'high'},
        {'title': 'Collect medical records', 'priority': 'high'},
    ]
    emails = [
        {
            'subject': f"Notice to Preserve Evidence - Case #{case.id}",
            'body': f"Please preserve all evidence related to the incident for client {case.client.first_name if case.client else ''} {case.client.last_name if case.client else ''}.",
        }
    ]
    deadlines = [
        {'name': 'Follow-up with premises owner', 'due_in_days': 7},
        {'name': 'Request medical records', 'due_in_days': 14},
    ]
    events = [
        {'title': 'Site inspection scheduling', 'due_in_days': 3},
    ]
    return {
        'case_id': case.id,
        'tasks': tasks,
        'emails': emails,
        'deadlines': deadlines,
        'events': events,
    }


@app.route('/api/automations/slip_fall/preview', methods=['POST'])
@requires_auth
def api_automations_slip_fall_preview():
    try:
        data = request.get_json(silent=True) or {}
        case_id = data.get('case_id')
        if not case_id:
            return jsonify({'error': 'case_id required'}), 400
        case = db.session.get(Case, int(case_id))
        if not case:
            return abort(404)
        preview = _slip_fall_build_preview(case, data.get('analysis'))
        return jsonify(preview)
    except Exception as e:
        app.logger.error(f"Error in api_automations_slip_fall_preview: {str(e)}")
        return jsonify({'error': 'failed'}), 500


@app.route('/api/automations/slip_fall/apply', methods=['POST'])
@requires_auth
def api_automations_slip_fall_apply():
    try:
        data = request.get_json(silent=True) or {}
        case_id = data.get('case_id')
        if not case_id:
            return jsonify({'error': 'case_id required'}), 400
        case = db.session.get(Case, int(case_id))
        if not case:
            return abort(404)
        # Use client-provided preview if present; otherwise compute
        preview = data.get('preview') or _slip_fall_build_preview(case, data.get('analysis'))
        created = {'tasks': 0, 'emails': 0, 'deadlines': 0}
        now = datetime.utcnow()
        # Create tasks (Actions) and associate to case via CaseAction
        for t in preview.get('tasks', []):
            try:
                a = Action(
                    title=t.get('title') or 'Task',
                    description=t.get('description'),
                    action_type='task',
                    status='pending',
                    priority=t.get('priority') or 'medium',
                    created_by_id=_current_user_id()
                )
                db.session.add(a)
                db.session.flush()
                ca = CaseAction(case_id=case.id, action_id=a.id, status='pending')
                db.session.add(ca)
                created['tasks'] += 1
            except Exception:
                db.session.rollback()
        # Create email drafts
        for em in preview.get('emails', []):
            try:
                draft = EmailDraft(
                    case_id=case.id,
                    to=None,
                    subject=em.get('subject') or 'Notice',
                    body=em.get('body') or '',
                    status='draft'
                )
                db.session.add(draft)
                created['emails'] += 1
            except Exception:
                db.session.rollback()
        # Create deadlines
        for dl in preview.get('deadlines', []):
            try:
                due_in = int(dl.get('due_in_days') or 7)
                due_date = now + timedelta(days=due_in)
                d = Deadline(case_id=case.id, name=dl.get('name') or 'Deadline', due_date=due_date, source='slip_fall_automation')
                db.session.add(d)
                created['deadlines'] += 1
            except Exception:
                db.session.rollback()
        db.session.commit()
        return jsonify({'ok': True, 'created': created})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_automations_slip_fall_apply: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/portal/messages', methods=['POST'])
@portal_login_required
def api_portal_messages_create():
    try:
        client_id = _get_portal_client_id()
        if not client_id:
            abort(403)
        data = request.get_json() or {}
        case_id = data.get('case_id')
        subject = (data.get('subject') or '').strip()
        message = (data.get('message') or '').strip()
        if not case_id or not message:
            return jsonify({'error': 'case_id and message required'}), 400

        c = db.session.get(Case, int(case_id))
        if not c or c.client_id != client_id:
            return jsonify({'error': 'forbidden'}), 403

        m = ClientMessage(
            case_id=c.id,
            from_client=True,
            client_id=client_id,
            subject=subject or None,
            message=message,
            read=False,
        )
        db.session.add(m)
        db.session.commit()
        return jsonify({'ok': True, 'id': m.id})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_portal_messages_create: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# ---- Staff JSON APIs ----
@app.route('/api/session', methods=['GET'])
def api_session_probe():
    if session.get('user_id'):
        return ('', 204)
    return ('', 401)

@app.route('/api/messages', methods=['POST'])
@requires_auth
def api_staff_message_create():
    try:
        data = request.get_json() or {}
        case_id = data.get('case_id')
        message = (data.get('message') or '').strip()
        subject = (data.get('subject') or '').strip() or None
        if not case_id or not message:
            return jsonify({'error': 'case_id and message required'}), 400
        c = db.session.get(Case, int(case_id))
        if not c:
            abort(404)
        m = ClientMessage(
            case_id=c.id,
            from_client=False,
            client_id=c.client_id,
            subject=subject,
            message=message,
            read=False,
        )
        db.session.add(m)
        db.session.commit()
        try:
            # Notify client via email (best-effort)
            to_email = c.client.email if getattr(c, 'client', None) and c.client and c.client.email else None
            if to_email:
                _send_email(to_email, subject or f"New message on case #{c.id}", message)
        except Exception:
            pass
        return jsonify({'ok': True, 'id': m.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_staff_message_create: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/intake/analyze', methods=['POST'])
@requires_auth
def api_intake_analyze():
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get('text', '')).strip()
        if not text:
            return jsonify({'error': 'Missing text'}), 400
        result = None
        # Prefer AssemblyAI analyzer if enabled
        if USE_AAI_ANALYZER and ASSEMBLYAI_API_KEY:
            try:
                result = analyze_with_aai(text)
            except Exception as e:
                app.logger.error(f"analyze_with_aai failed: {str(e)}; falling back")
        if result is None:
            try:
                result = analyze_intake_text_scenarios(text)
            except Exception as e:
                app.logger.error(f"analyze_intake_text_scenarios failed: {str(e)}")
                return jsonify({'error': 'Analyzer unavailable'}), 501
        # Normalize response structure
        payload = {
            'category': result.get('category'),
            'case_type_key': result.get('case_type_key'),
            'urgency': result.get('urgency'),
            'key_facts': result.get('key_facts', {}),
            'dates': result.get('dates', {}),
            'parties': result.get('parties', {}),
            'suggested_actions': result.get('suggested_actions', []),
            'checklists': result.get('checklists', {}),
            'department': result.get('department'),
            'confidence': result.get('confidence'),
        }
        return jsonify(payload)
    except Exception as e:
        app.logger.error(f"/api/intake/analyze error: {str(e)}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/api/dashboard', methods=['GET'])
@requires_auth
def api_dashboard():
    try:
        uid = _current_user_id()
        user = db.session.get(User, uid) if uid else None
        stats = {
            'active_cases': Case.query.filter_by(status='open').count(),
            'active_clients': Client.query.count(),
            'pending_actions': Action.query.filter_by(status='pending').count(),
            'documents_count': Document.query.count(),
            'last_updated': datetime.now().isoformat()
        }
        recent_cases = [
            {
                'id': c.id,
                'title': c.title,
                'created_at': c.created_at.isoformat() if getattr(c, 'created_at', None) else None,
                'client': {
                    'id': c.client.id if getattr(c, 'client', None) else None,
                    'name': f"{getattr(c.client, 'first_name', '')} {getattr(c.client, 'last_name', '')}".strip() if getattr(c, 'client', None) else None,
                }
            }
            for c in Case.query.order_by(Case.created_at.desc()).limit(5).all()
        ]
        now = datetime.now()
        upcoming_actions = [
            {
                'id': a.id,
                'title': a.title,
                'due_date': a.due_date.isoformat() if getattr(a, 'due_date', None) else None,
                'status': a.status,
            }
            for a in Action.query.filter(Action.due_date >= now).order_by(Action.due_date.asc()).limit(5).all()
        ]
        upcoming_deadlines = [
            {
                'id': d.id,
                'name': d.name,
                'due_date': d.due_date.isoformat() if getattr(d, 'due_date', None) else None,
            }
            for d in Deadline.query.filter(Deadline.due_date >= now, Deadline.due_date <= now + timedelta(days=30)).order_by(Deadline.due_date.asc()).limit(5).all()
        ]
        return jsonify({
            'current_user': {'id': user.id, 'email': user.email} if user else None,
            'stats': stats,
            'recent_cases': recent_cases,
            'upcoming_actions': upcoming_actions,
            'upcoming_deadlines': upcoming_deadlines,
        })
    except Exception as e:
        app.logger.error(f"Error in api_dashboard: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/time_entries/running', methods=['GET'])
@requires_auth
def api_time_entries_running():
    try:
        user_id = _current_user_id()
        if not user_id:
            return jsonify({'error': 'unauthorized'}), 401
        case_id = request.args.get('case_id', type=int)
        q = TimeEntry.query.filter(TimeEntry.user_id == user_id, TimeEntry.end_time == None)
        if case_id:
            q = q.filter(TimeEntry.case_id == case_id)
        te = q.order_by(TimeEntry.created_at.desc()).first()
        if not te:
            return jsonify({'running': False})
        # compute elapsed seconds
        start_dt = datetime.combine(te.date, te.start_time) if te.start_time else datetime.utcnow()
        elapsed_s = max(0, int((datetime.utcnow() - start_dt).total_seconds()))
        return jsonify({'running': True, 'entry': te.to_dict(), 'elapsed_seconds': elapsed_s})
    except Exception as e:
        app.logger.error(f"Error in api_time_entries_running: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/time_entries/start', methods=['POST'])
@requires_auth
def api_time_entries_start():
    try:
        user_id = _current_user_id()
        if not user_id:
            return jsonify({'error': 'unauthorized'}), 401
        data = request.get_json() or {}
        case_id = data.get('case_id')
        if not case_id:
            return jsonify({'error': 'case_id required'}), 400
        c = db.session.get(Case, int(case_id))
        if not c:
            return abort(404)
        # prevent multiple running timers per user
        existing = TimeEntry.query.filter(TimeEntry.user_id==user_id, TimeEntry.end_time==None).first()
        if existing:
            return jsonify({'error': 'timer already running', 'entry': existing.to_dict()}), 409
        now = datetime.utcnow()
        hourly_rate = float(data.get('hourly_rate') or 200)
        desc = (data.get('description') or 'Timer started').strip()
        activity_type = data.get('activity_type')
        te = TimeEntry(
            case_id=c.id,
            user_id=user_id,
            date=now.date(),
            start_time=now.time(),
            end_time=None,
            duration_minutes=0,
            hourly_rate=hourly_rate,
            amount=0.0,
            billable=True,
            billed=False,
            description=desc or 'Timer started',
            activity_type=activity_type
        )
        db.session.add(te)
        db.session.commit()
        return jsonify({'ok': True, 'entry': te.to_dict()})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_time_entries_start: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/time_entries/stop', methods=['POST'])
@requires_auth
def api_time_entries_stop():
    try:
        user_id = _current_user_id()
        if not user_id:
            return jsonify({'error': 'unauthorized'}), 401
        data = request.get_json(silent=True) or {}
        case_id = data.get('case_id')
        q = TimeEntry.query.filter(TimeEntry.user_id==user_id, TimeEntry.end_time==None)
        if case_id:
            q = q.filter(TimeEntry.case_id==int(case_id))
        te = q.order_by(TimeEntry.created_at.desc()).first()
        if not te:
            return jsonify({'error': 'no running timer'}), 404
        now = datetime.utcnow()
        te.end_time = now.time()
        start_dt = datetime.combine(te.date, te.start_time) if te.start_time else now
        duration_minutes = max(1, int(round((now - start_dt).total_seconds() / 60.0)))
        te.duration_minutes = duration_minutes
        te.calculate_amount()
        db.session.add(te)
        db.session.commit()
        return jsonify({'ok': True, 'entry': te.to_dict()})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_time_entries_stop: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/admin/seed_portal_user', methods=['POST'])
@requires_auth
def api_admin_seed_portal_user():
    try:
        if os.getenv('ENABLE_ADMIN_SEED', 'false').strip().lower() != 'true':
            return jsonify({'error': 'admin seeding disabled'}), 403
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or os.getenv('DEMO_PORTAL_EMAIL') or 'client@example.com').strip().lower()
        password = data.get('password') or os.getenv('DEMO_PORTAL_PASSWORD') or 'client123'
        first_name = data.get('first_name') or os.getenv('DEMO_PORTAL_FIRST_NAME') or 'Demo'
        last_name = data.get('last_name') or os.getenv('DEMO_PORTAL_LAST_NAME') or 'Client'
        if '@' not in email:
            return jsonify({'error': 'invalid email'}), 400
        # Ensure client exists
        client = Client.query.filter(db.func.lower(Client.email) == email).first()
        if not client:
            client = Client(first_name=first_name, last_name=last_name, email=email)
            db.session.add(client)
            db.session.flush()
        # Ensure portal user exists
        cu = ClientUser.query.filter(db.func.lower(ClientUser.email) == email).first()
        if not cu:
            cu = ClientUser(client_id=client.id, email=email)
            cu.set_password(password)
            db.session.add(cu)
        else:
            cu.set_password(password)
        db.session.commit()
        return jsonify({'ok': True, 'client_id': client.id, 'client_user_id': cu.id, 'email': email, 'password': password})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_admin_seed_portal_user: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/admin/seed_intents', methods=['POST'])
@requires_auth
def api_admin_seed_intents():
    try:
        if os.getenv('ENABLE_ADMIN_SEED', 'false').strip().lower() != 'true':
            return jsonify({'error': 'admin seeding disabled'}), 403
        seeds = [
            {
                'key': 'personal_injury_premises',
                'name': 'Personal Injury - Premises Liability',
                'department': 'Personal Injury',
                'actions': [
                    {'title': 'Send preservation letter to store', 'description': 'Preserve CCTV and incident logs', 'default_status': 'pending', 'default_priority': 'high', 'due_in_days': 1},
                    {'title': 'Request staff list and cleaning logs', 'description': 'Day of incident', 'default_status': 'pending', 'default_priority': 'medium', 'due_in_days': 2},
                ],
                'emails': [
                    {'filename': 'preservation_letter.docx', 'subject': 'Evidence Preservation Request', 'body': 'Please preserve all CCTV and incident records for the date...'},
                ],
            },
            {
                'key': 'auto_accident',
                'name': 'Auto Accident',
                'department': 'Auto',
                'actions': [
                    {'title': 'Request police report', 'description': 'Obtain incident report number and documents', 'default_status': 'pending', 'default_priority': 'high', 'due_in_days': 2},
                    {'title': 'Contact insurance companies', 'description': 'Notify carrier and obtain claim number', 'default_status': 'pending', 'default_priority': 'medium', 'due_in_days': 3},
                ],
                'emails': [
                    {'filename': 'insurance_notice.docx', 'subject': 'Notice of Representation', 'body': 'We represent the insured in the matter of the accident on ...'},
                ],
            },
            {
                'key': 'employment_dispute',
                'name': 'Employment Law - Wrongful Termination',
                'department': 'Employment',
                'actions': [
                    {'title': 'Collect employment records', 'description': 'Offer letters, paystubs, reviews', 'default_status': 'pending', 'default_priority': 'medium', 'due_in_days': 5},
                    {'title': 'Evaluate EEOC filing', 'description': 'Assess deadlines and grounds', 'default_status': 'pending', 'default_priority': 'high', 'due_in_days': 7},
                ],
                'emails': [
                    {'filename': 'document_request.docx', 'subject': 'Request for Employment Records', 'body': 'Please provide employment records and policies...'},
                ],
            },
        ]
        created = []
        for s in seeds:
            existing = Intent.query.filter_by(key=s['key']).first()
            if existing:
                continue
            i = Intent(key=s['key'], name=s['name'], department=s.get('department'), active=True)
            db.session.add(i)
            db.session.flush()
            for a in s.get('actions', []):
                at = ActionTemplate(
                    intent_id=i.id,
                    title=a['title'],
                    description=a.get('description'),
                    default_status=a.get('default_status', 'pending'),
                    default_priority=a.get('default_priority', 'medium'),
                    due_in_days=a.get('due_in_days'),
                )
                db.session.add(at)
            for e in s.get('emails', []):
                et = EmailTemplate(
                    intent_id=i.id,
                    filename=e['filename'],
                    subject=e['subject'],
                    body=e['body'],
                )
                db.session.add(et)
            created.append(i.key)
        db.session.commit()
        return jsonify({'ok': True, 'created': created})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_admin_seed_intents: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/cases/<int:case_id>/notes', methods=['POST'])
@requires_auth
def api_case_add_note(case_id):
    try:
        c = db.session.get(Case, case_id)
        if c is None:
            abort(404)
        data = request.get_json() or {}
        content = (data.get('note') or '').strip()
        if not content:
            return jsonify({'error': 'note required'}), 400
        note = CaseNote(
            content=content,
            is_private=False,
            case_id=c.id,
            created_by_id=_current_user_id()
        )
        db.session.add(note)
        db.session.commit()
        return jsonify({'ok': True, 'id': note.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_case_add_note: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/cases/<int:case_id>', methods=['GET'])
@requires_auth
def api_case_detail(case_id):
    try:
        c = db.session.get(Case, case_id)
        if c is None:
            abort(404)
        result = {
            'id': c.id,
            'title': c.title,
            'description': getattr(c, 'description', None),
            'status': c.status,
            'priority': getattr(c, 'priority', None),
            'created_at': c.created_at.isoformat() if getattr(c, 'created_at', None) else None,
            'client': {
                'id': c.client.id if getattr(c, 'client', None) else None,
                'first_name': getattr(c.client, 'first_name', None) if getattr(c, 'client', None) else None,
                'last_name': getattr(c.client, 'last_name', None) if getattr(c, 'client', None) else None,
                'email': getattr(c.client, 'email', None) if getattr(c, 'client', None) else None,
            } if getattr(c, 'client', None) else None,
        }
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in api_case_detail: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/cases/<int:case_id>/status', methods=['PATCH'])
@requires_auth
def api_case_update_status(case_id):
    try:
        c = db.session.get(Case, case_id)
        if c is None:
            abort(404)
        data = request.get_json() or {}
        new_status = (data.get('status') or '').strip()
        allowed = {'open', 'in_progress', 'closed'}
        if new_status not in allowed:
            return jsonify({'error': 'invalid status'}), 400
        old_status = c.status
        if old_status == new_status:
            return jsonify({'ok': True, 'status': c.status})
        # Update and audit
        c.status = new_status
        c.updated_at = datetime.utcnow()
        audit = CaseStatusAudit(
            case_id=c.id,
            from_status=old_status,
            to_status=new_status,
            changed_by_id=_current_user_id(),
            created_at=datetime.utcnow(),
        )
        db.session.add(audit)
        db.session.add(c)
        db.session.commit()
        try:
            # Notify client of status change (best-effort)
            to_email = c.client.email if getattr(c, 'client', None) and c.client and c.client.email else None
            if to_email:
                _send_email(to_email, f"Your case status changed to {new_status}", f"Case '{c.title}' status changed from {old_status} to {new_status}.")
        except Exception:
            pass
        return jsonify({'ok': True, 'status': c.status})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_case_update_status: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# ---------------- Client Portal Checklist APIs ---------------- #
@app.route('/api/portal/cases/<int:case_id>/checklist', methods=['GET'])
@portal_login_required
def api_portal_case_checklist(case_id: int):
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    c = db.session.get(Case, case_id)
    if not c or c.client_id != client_id:
        abort(404)
    # Find actions linked to this case that are pending and appear client-required
    kw = ['upload', 'provide', 'send', 'sign', 'verify', 'complete', 'fill']
    links = (CaseAction.query
             .filter_by(case_id=case_id)
             .join(Action, CaseAction.action_id == Action.id)
             .order_by(Action.due_date.asc().nulls_last(), Action.created_at.asc())
             .all())
    items = []
    for link in links:
        a = link.action
        if not a:
            continue
        if (a.status or 'pending') != 'pending':
            continue
        title_l = (a.title or '').lower()
        is_client = (getattr(a, 'action_type', None) in ('client', 'client_task', 'document', 'signature')) or any(k in title_l for k in kw)
        if not is_client:
            continue
        items.append({
            'action_id': a.id,
            'title': a.title,
            'description': getattr(a, 'description', None),
            'due_date': a.due_date.isoformat() if getattr(a, 'due_date', None) else None,
            'status': a.status,
        })
    # Include doc-needed hints from deadlines
    deadlines = (Deadline.query.filter_by(case_id=case_id).order_by(Deadline.due_date.asc()).all())
    doc_hints = []
    for d in deadlines:
        name_l = (d.name or '').lower()
        if any(k in name_l for k in ['medical', 'records', 'police', 'report', 'personnel', 'file', 'evidence']):
            doc_hints.append({'deadline_id': d.id, 'name': d.name, 'due_date': d.due_date.isoformat() if getattr(d, 'due_date', None) else None})
    return jsonify({'items': items, 'doc_hints': doc_hints})

@app.route('/api/portal/cases/<int:case_id>/checklist/<int:action_id>/complete', methods=['POST'])
@portal_login_required
def api_portal_case_checklist_complete(case_id: int, action_id: int):
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    c = db.session.get(Case, case_id)
    if not c or c.client_id != client_id:
        abort(404)
    link = CaseAction.query.filter_by(case_id=case_id, action_id=action_id).join(Action, CaseAction.action_id == Action.id).first()
    if not link or not link.action:
        abort(404)
    a = link.action
    # Only allow completing items that are client-appropriate (same heuristic as GET)
    title_l = (a.title or '').lower()
    if not ((getattr(a, 'action_type', None) in ('client', 'client_task', 'document', 'signature')) or any(k in title_l for k in ['upload','provide','send','sign','verify','complete','fill'])):
        return jsonify({'error': 'forbidden'}), 403
    now = datetime.utcnow()
    a.status = 'completed'
    a.completed_at = now
    link.status = 'completed'
    db.session.add(a)
    db.session.add(link)
    db.session.commit()
    return jsonify({'ok': True})

# ---------------- Client Portal Transcription & Intake ---------------- #
@app.route('/api/portal/transcribe', methods=['POST'])
@portal_login_required
def api_portal_transcribe_start():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['audio_file']
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not _is_allowed_audio(file.filename, getattr(file, 'mimetype', '')):
        return jsonify({'error': 'Unsupported audio type'}), 415
    filename = secure_filename(file.filename or f"recording_{datetime.utcnow().timestamp()}.webm")
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_path)
    try:
        service = STTService()
        transcript_id = service.start_transcription(temp_path)
        # Persist Transcript row (link to client)
        t = Transcript(
            provider='assemblyai',
            external_id=transcript_id,
            status='processing',
            client_id=_get_portal_client_id()
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({'status': 'processing', 'transcript_id': transcript_id})
    except Exception as e:
        app.logger.error(f"api_portal_transcribe_start error: {str(e)}")
        return jsonify({'error': 'Failed to start transcription'}), 500
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

@app.route('/api/portal/transcripts/<string:external_id>', methods=['GET'])
@portal_login_required
def api_portal_transcript_status(external_id: str):
    t = Transcript.query.filter_by(external_id=external_id).first()
    if not t:
        t = Transcript(provider='assemblyai', external_id=external_id, status='processing', client_id=_get_portal_client_id())
        db.session.add(t)
        db.session.commit()
    if t.status != 'completed':
        try:
            service = STTService()
            data = service.get_transcription_status(external_id)
            new_status = data.get('status') or t.status
            t.status = new_status
            if new_status == 'completed' and data.get('text'):
                t.text = data.get('text')
            if new_status == 'error':
                t.text = None
            db.session.commit()
        except Exception as e:
            app.logger.error(f"portal get transcription status error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    payload = {
        'transcript_id': external_id,
        'status': t.status,
        'text': getattr(t, 'text', None),
        'error': getattr(t, 'error', None),
    }
    return jsonify(payload)

@app.route('/api/intake/auto', methods=['POST'])
@requires_auth
def api_staff_auto_intake():
    """Staff-side auto intake that creates a Case from free-text and client info.

    Expects JSON body:
        {
            "text": "...",
            "title": "...",  # optional
            "client": {"first_name", "last_name", "email", "phone", "address"}
        }
    """
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    client_payload = data.get('client') or {}
    first_name = (client_payload.get('first_name') or '').strip()
    last_name = (client_payload.get('last_name') or '').strip()
    email = (client_payload.get('email') or '').strip().lower() or None
    phone = (client_payload.get('phone') or None)
    address = (client_payload.get('address') or None)
    if not first_name or not last_name:
        return jsonify({'error': 'client.first_name and client.last_name required'}), 400

    try:
        # Ensure client exists (match by email when available)
        c = None
        if email:
            c = Client.query.filter(db.func.lower(Client.email) == email).first()
        if not c:
            c = Client(first_name=first_name, last_name=last_name, email=email, phone=phone, address=address)
            db.session.add(c)
            db.session.flush()

        # Run analyzer (AssemblyAI or scenario-based fallback via _analyze_text)
        analysis = _analyze_text(text)

        # Create case
        new_case = Case(
            title=(data.get('title') or 'Client Intake'),
            description=text,
            case_type=analysis.get('category'),
            status='open',
            priority=(analysis.get('priority') or analysis.get('urgency') or 'Medium').lower(),
            category=analysis.get('category'),
            client_id=c.id,
            created_by_id=_current_user_id(),
        )
        db.session.add(new_case)
        db.session.flush()

        # Apply taxonomy-aware classification if case_type_key is present
        try:
            classification = {
                "primary_category": analysis.get("category"),
                "case_type_key": analysis.get("case_type_key"),
                "urgency": analysis.get("urgency"),
                "confidence": analysis.get("confidence"),
            }
            apply_ai_classification_to_case(new_case, {"classification": classification})
        except Exception:
            pass

        # Persist AI insight
        insight = AIInsight(
            case_id=new_case.id,
            insight_text=f"{analysis.get('category')} | Urgency: {analysis.get('urgency')} | Dept: {analysis.get('department')}",
            category='scenario_analysis',
            confidence=analysis.get('confidence'),
        )
        db.session.add(insight)

        # Create suggested actions & link to case
        for text_action in (analysis.get('suggested_actions') or [])[:10]:
            action = Action(
                title=text_action,
                description='Auto-generated from scenario analysis',
                action_type='automation',
                status='pending',
                priority=(analysis.get('priority') or 'Medium').lower(),
                due_date=datetime.utcnow() + timedelta(days=1),
                created_by_id=_current_user_id(),
            )
            db.session.add(action)
            db.session.flush()
            db.session.add(CaseAction(case_id=new_case.id, action_id=action.id, status='pending'))

        db.session.commit()
        return jsonify({'status': 'success', 'case_id': new_case.id, 'analysis': analysis}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_staff_auto_intake: {str(e)}")
        return jsonify({'error': 'Server error'}), 500


@app.route('/api/portal/intake/auto', methods=['POST'])
@portal_login_required
def api_portal_auto_intake():
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    client_id = _get_portal_client_id()
    c = db.session.get(Client, client_id) if client_id else None
    if not c:
        abort(403)
    try:
        analysis = _analyze_text(text)
        new_case = Case(
            title=(data.get('title') or 'Client Intake'),
            description=text,
            case_type=analysis.get('category'),
            status='open',
            priority=(analysis.get('priority') or 'Medium').lower(),
            category=analysis.get('category'),
            client_id=c.id,
            created_by_id=_current_user_id(),
        )
        db.session.add(new_case)
        db.session.flush()

        # Apply taxonomy-aware classification if case_type_key is present
        try:
            classification = {
                "primary_category": analysis.get("category"),
                "case_type_key": analysis.get("case_type_key"),
                "urgency": analysis.get("urgency"),
                "confidence": analysis.get("confidence"),
            }
            apply_ai_classification_to_case(new_case, {"classification": classification})
        except Exception:
            pass

        insight = AIInsight(
            case_id=new_case.id,
            insight_text=f"{analysis.get('category')} | Urgency: {analysis.get('urgency')} | Dept: {analysis.get('department')}",
            category='scenario_analysis',
            confidence=None,
        )
        db.session.add(insight)
        for text_action in (analysis.get('suggested_actions') or [])[:10]:
            action = Action(
                title=text_action,
                description='Auto-generated from scenario analysis',
                action_type='automation',
                status='pending',
                priority=(analysis.get('priority') or 'Medium').lower(),
                due_date=datetime.utcnow() + timedelta(days=1),
                created_by_id=_current_user_id()
            )
            db.session.add(action)
            db.session.flush()
            db.session.add(CaseAction(case_id=new_case.id, action_id=action.id, status='pending'))
        db.session.commit()
        return jsonify({'status': 'success', 'case_id': new_case.id, 'analysis': analysis}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_portal_auto_intake: {str(e)}")
        return jsonify({'error': 'Server error'}), 500

# ---------------- Client Portal Appointments ---------------- #
@app.route('/api/portal/appointments', methods=['GET'])
@portal_login_required
def api_portal_appointments_list():
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    events = (CalendarEvent.query
              .filter_by(client_id=client_id)
              .order_by(CalendarEvent.start_at.asc())
              .all())
    return jsonify([ev.to_dict() for ev in events])

@app.route('/api/portal/appointments', methods=['POST'])
@portal_login_required
def api_portal_appointments_create():
    client_id = _get_portal_client_id()
    if not client_id:
        abort(403)
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'title required'}), 400
    start_iso = data.get('start_at')
    end_iso = data.get('end_at')
    start_at = datetime.fromisoformat(start_iso) if start_iso else None
    end_at = datetime.fromisoformat(end_iso) if end_iso else None
    ev = CalendarEvent(
        title=title,
        description=data.get('description'),
        start_at=start_at,
        end_at=end_at,
        all_day=bool(data.get('all_day')),
        location=data.get('location'),
        case_id=int(data.get('case_id')) if data.get('case_id') else None,
        client_id=client_id,
        created_by_id=_current_user_id(),
        reminder_minutes_before=int(data.get('reminder_minutes_before') or 0),
        status='scheduled'
    )
    try:
        db.session.add(ev)
        db.session.commit()
        return jsonify({'id': ev.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_portal_appointments_create: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/cases/<int:case_id>/status_audit', methods=['GET'])
@requires_auth
def api_case_status_audit(case_id):
    try:
        c = db.session.get(Case, case_id)
        if c is None:
            abort(404)
        rows = (CaseStatusAudit.query
                .filter_by(case_id=case_id)
                .order_by(CaseStatusAudit.created_at.desc())
                .all())
        return jsonify([r.to_dict() for r in rows])
    except Exception as e:
        app.logger.error(f"Error in api_case_status_audit: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/cases', methods=['GET'])
@requires_auth
def api_cases_list():
    try:
        pagination = get_pagination(request.args.get('page'), request.args.get('per_page', 10))
        query = Case.query.options(db.joinedload(Case.client))
        query = apply_case_filters(query, request.args)
        sort_column, sort_order = get_sort_params(request.args)
        if sort_column is not None:
            query = query.order_by(db.desc(sort_column) if sort_order == 'desc' else sort_column)
        else:
            query = query.order_by(Case.created_at.desc())
        paginated = query.paginate(page=pagination['page'], per_page=pagination['per_page'], error_out=False)
        items = [
            {
                'id': c.id,
                'title': c.title,
                'status': c.status,
                'priority': c.priority,
                'created_at': c.created_at.isoformat() if getattr(c, 'created_at', None) else None,
                'client': {
                    'id': c.client.id if getattr(c, 'client', None) else None,
                    'first_name': getattr(c.client, 'first_name', None) if getattr(c, 'client', None) else None,
                    'last_name': getattr(c.client, 'last_name', None) if getattr(c, 'client', None) else None,
                }
            }
            for c in paginated.items
        ]
        return jsonify({
            'items': items,
            'page': paginated.page,
            'per_page': paginated.per_page,
            'total': paginated.total,
            'pages': paginated.pages
        })
    except Exception as e:
        app.logger.error(f"Error in api_cases_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/clients', methods=['GET'])
@requires_auth
def api_clients_list():
    try:
        query = Client.query
        # Optional search by name/email/phone
        search = (request.args.get('search') or '').strip()
        if search:
            like = f"%{search}%"
            query = query.filter(
                db.or_(
                    Client.first_name.ilike(like),
                    Client.last_name.ilike(like),
                    Client.email.ilike(like),
                    Client.phone.ilike(like),
                )
            )
        clients = query.order_by(Client.last_name, Client.first_name).all()
        items = [
            {
                'id': cl.id,
                'first_name': getattr(cl, 'first_name', None),
                'last_name': getattr(cl, 'last_name', None),
                'email': getattr(cl, 'email', None),
                'phone': getattr(cl, 'phone', None),
            }
            for cl in clients
        ]
        return jsonify(items)
    except Exception as e:
        app.logger.error(f"Error in api_clients_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/clients/<int:client_id>', methods=['GET'])
@requires_auth
def api_client_detail(client_id):
    try:
        cl = db.session.get(Client, client_id)
        if cl is None:
            abort(404)
        cases = Case.query.filter_by(client_id=client_id).order_by(Case.created_at.desc()).all()
        result = {
            'id': cl.id,
            'first_name': getattr(cl, 'first_name', None),
            'last_name': getattr(cl, 'last_name', None),
            'email': getattr(cl, 'email', None),
            'phone': getattr(cl, 'phone', None),
            'address': getattr(cl, 'address', None),
            'cases': [
                {
                    'id': c.id,
                    'title': c.title,
                    'status': c.status,
                    'created_at': c.created_at.isoformat() if getattr(c, 'created_at', None) else None,
                }
                for c in cases
            ]
        }
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in api_client_detail: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/clients', methods=['POST'])
@requires_auth
def api_client_create():
    try:
        data = request.get_json() or {}
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()
        email = (data.get('email') or None)
        phone = (data.get('phone') or None)
        address = (data.get('address') or None)
        if not first_name or not last_name:
            return jsonify({'error': 'first_name and last_name required'}), 400
        cl = Client(first_name=first_name, last_name=last_name, email=email, phone=phone, address=address)
        db.session.add(cl)
        db.session.commit()
        return jsonify({'ok': True, 'id': cl.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_client_create: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/clients/<int:client_id>', methods=['PATCH'])
@requires_auth
def api_client_update(client_id):
    try:
        cl = db.session.get(Client, client_id)
        if cl is None:
            abort(404)
        data = request.get_json() or {}
        for field in ['first_name', 'last_name', 'email', 'phone', 'address']:
            if field in data:
                setattr(cl, field, data.get(field))
        cl.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_client_update: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/actions', methods=['GET'])
@requires_auth
def api_actions_list():
    try:
        client_id = request.args.get('client_id', type=int)
        q = db.session.query(Action).options(
            db.joinedload(Action.case_actions).joinedload(CaseAction.case),
            db.joinedload(Action.assigned_to)
        ).order_by(Action.created_at.desc())
        if client_id:
            q = q.join(CaseAction, CaseAction.action_id == Action.id).join(Case, Case.id == CaseAction.case_id).filter(Case.client_id == client_id)
        actions = q.all()
        def case_title_for(a: Action):
            if getattr(a, 'case_actions', None):
                for link in a.case_actions:
                    if getattr(link, 'case', None):
                        return getattr(link.case, 'title', None)
            return None
        def case_id_for(a: Action):
            if getattr(a, 'case_actions', None):
                for link in a.case_actions:
                    if getattr(link, 'case', None):
                        return getattr(link.case, 'id', None)
            return None
        items = [
            {
                'id': a.id,
                'title': a.title,
                'status': a.status,
                'priority': getattr(a, 'priority', None),
                'due_date': a.due_date.isoformat() if getattr(a, 'due_date', None) else None,
                'assigned_to_id': getattr(a, 'assigned_to_id', None),
                'case_id': case_id_for(a),
                'case_title': case_title_for(a),
            }
            for a in actions
        ]
        return jsonify(items)
    except Exception as e:
        app.logger.error(f"Error in api_actions_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/actions', methods=['POST'])
@requires_auth
def api_action_create():
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({'error': 'title required'}), 400
        description = data.get('description') or ''
        action_type = data.get('action_type')
        status = data.get('status') or 'pending'
        priority = data.get('priority') or 'medium'
        due_date = None
        if data.get('due_date'):
            try:
                due_date = datetime.fromisoformat(data['due_date'])
            except Exception:
                pass
        assigned_to_id = data.get('assigned_to_id')
        case_id = data.get('case_id')
        a = Action(
            title=title,
            description=description,
            action_type=action_type,
            status=status,
            priority=priority,
            due_date=due_date,
            assigned_to_id=assigned_to_id,
            created_by_id=_current_user_id(),
        )
        db.session.add(a)
        db.session.flush()
        if case_id:
            link = CaseAction(case_id=case_id, action_id=a.id, assigned_to_id=assigned_to_id, status=status)
            db.session.add(link)
        db.session.commit()
        return jsonify({'ok': True, 'id': a.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_action_create: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/email/drafts', methods=['GET'])
@requires_auth
def api_email_drafts_list():
    try:
        drafts = EmailDraft.query.order_by(EmailDraft.created_at.desc()).all()
        return jsonify([d.to_dict() for d in drafts])
    except Exception as e:
        app.logger.error(f"Error in api_email_drafts_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/email/drafts/<int:draft_id>', methods=['GET'])
@requires_auth
def api_email_draft_detail(draft_id):
    try:
        d = db.session.get(EmailDraft, draft_id)
        if d is None:
            abort(404)
        return jsonify(d.to_dict())
    except Exception as e:
        app.logger.error(f"Error in api_email_draft_detail: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/email/drafts/<int:draft_id>/send', methods=['POST'])
@requires_auth
def api_email_draft_send(draft_id):
    try:
        d = db.session.get(EmailDraft, draft_id)
        if d is None:
            abort(404)
        d.status = 'sent'
        d.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_email_draft_send: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/email/drafts/<int:draft_id>', methods=['DELETE'])
@requires_auth
def api_email_draft_delete(draft_id):
    try:
        d = db.session.get(EmailDraft, draft_id)
        if d is None:
            abort(404)
        db.session.delete(d)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_email_draft_delete: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# Email Queue visibility and retry
@app.route('/api/email/queue', methods=['GET'])
@requires_auth
def api_email_queue_list():
    try:
        status = (request.args.get('status') or '').strip()
        q = db.session.query(EmailQueue).options(db.joinedload(EmailQueue.case)).order_by(EmailQueue.created_at.desc())
        if status in ('pending', 'sent', 'failed'):
            q = q.filter(EmailQueue.status == status)
        items = []
        for e in q.all():
            d = e.to_dict()
            d['case_title'] = getattr(e.case, 'title', None)
            items.append(d)
        return jsonify(items)
    except Exception as e:
        app.logger.error(f"Error in api_email_queue_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/email/queue/<int:item_id>/retry', methods=['POST'])
@requires_auth
def api_email_queue_retry(item_id):
    try:
        item = db.session.get(EmailQueue, item_id)
        if item is None:
            abort(404)
        item.status = 'pending'
        item.attempts = 0
        item.last_error = None
        item.send_after = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_email_queue_retry: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/actions/<int:action_id>', methods=['GET'])
@requires_auth
def api_action_detail(action_id):
    try:
        a = db.session.get(Action, action_id)
        if a is None:
            abort(404)
        # Find first related case via CaseAction if exists
        link = CaseAction.query.filter_by(action_id=action_id).join(Case).first()
        result = {
            'id': a.id,
            'title': a.title,
            'description': getattr(a, 'description', None),
            'status': a.status,
            'priority': getattr(a, 'priority', None),
            'due_date': a.due_date.isoformat() if getattr(a, 'due_date', None) else None,
            'assigned_to_id': getattr(a, 'assigned_to_id', None),
            'case': {
                'id': getattr(link.case, 'id', None) if link and getattr(link, 'case', None) else None,
                'title': getattr(link.case, 'title', None) if link and getattr(link, 'case', None) else None,
            } if link else None,
        }
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in api_action_detail: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# Time Entries (JSON)
@app.route('/api/time_entries', methods=['GET'])
@requires_auth
def api_time_entries_list():
    try:
        case_id = request.args.get('case_id', type=int)
        q = TimeEntry.query.options(db.joinedload(TimeEntry.case), db.joinedload(TimeEntry.user)).order_by(TimeEntry.date.desc())
        if case_id:
            q = q.filter(TimeEntry.case_id == case_id)
        items = []
        for t in q.limit(100).all():
            items.append({
                'id': t.id,
                'case': {'id': t.case.id if getattr(t, 'case', None) else None, 'title': getattr(t.case, 'title', None) if getattr(t, 'case', None) else None},
                'user_id': getattr(t, 'user_id', None),
                'date': t.date.isoformat() if getattr(t, 'date', None) else None,
                'duration_minutes': getattr(t, 'duration_minutes', 0) or 0,
                'hourly_rate': getattr(t, 'hourly_rate', 0.0) or 0.0,
                'amount': getattr(t, 'amount', 0.0) or 0.0,
                'description': getattr(t, 'description', None),
                'created_at': t.created_at.isoformat() if getattr(t, 'created_at', None) else None,
            })
        return jsonify(items)
    except Exception as e:
        app.logger.error(f"Error in api_time_entries_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/time_entries', methods=['POST'])
@requires_auth
def api_time_entry_create():
    try:
        data = request.get_json() or {}
        case_id = data.get('case_id')
        hours = float(data.get('hours') or 0)
        hourly_rate = float(data.get('rate') or 0)
        description = (data.get('description') or '').strip()
        date_str = data.get('date')
        if not case_id or hours <= 0 or hourly_rate <= 0 or not description:
            return jsonify({'error': 'case_id, hours>0, rate>0, description required'}), 400
        date_val = None
        if date_str:
            try:
                date_val = datetime.fromisoformat(date_str).date()
            except Exception:
                pass
        if not date_val:
            date_val = datetime.utcnow().date()
        duration_minutes = int(round(hours * 60))
        amount = (duration_minutes / 60.0) * hourly_rate
        t = TimeEntry(
            case_id=case_id,
            user_id=_current_user_id(),
            date=date_val,
            duration_minutes=duration_minutes,
            hourly_rate=hourly_rate,
            amount=amount,
            description=description,
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({'ok': True, 'id': t.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_time_entry_create: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# Stripe checkout
@app.route('/api/payments/stripe/checkout', methods=['POST'])
@requires_auth
def api_stripe_checkout():
    try:
        if not (stripe and STRIPE_SECRET_KEY):
            return jsonify({'error': 'stripe_not_configured'}), 501
        data = request.get_json(silent=True) or {}
        invoice_id = data.get('invoice_id')
        if not invoice_id:
            return jsonify({'error': 'invoice_id required'}), 400
        inv = db.session.get(Invoice, int(invoice_id))
        if not inv:
            return jsonify({'error': 'invoice not found'}), 404
        amount_due = float(getattr(inv, 'balance_due', 0) or getattr(inv, 'total_amount', 0) or 0)
        if amount_due <= 0:
            return jsonify({'error': 'nothing_to_pay'}), 400
        cents = int(round(amount_due * 100))
        # Build line item
        name = f"Invoice #{getattr(inv, 'invoice_number', None) or inv.id}"
        currency = os.getenv('STRIPE_CURRENCY', 'usd')
        success_url = os.getenv('STRIPE_SUCCESS_URL', 'http://localhost:3000/billing?paid=1')
        cancel_url = os.getenv('STRIPE_CANCEL_URL', 'http://localhost:3000/billing?canceled=1')
        session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': { 'name': name },
                    'unit_amount': cents,
                },
                'quantity': 1,
            }],
            metadata={ 'invoice_id': str(inv.id) },
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return jsonify({'url': session.get('url')}), 200
    except Exception as e:
        app.logger.error(f"Error in api_stripe_checkout: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/payments/stripe/webhook', methods=['POST'])
def api_stripe_webhook():
    # Placeholder endpoint; accept 200 for now
    return ('', 200)

# Billing: generate invoices (stub)
@app.route('/api/billing/invoices/generate', methods=['POST'])
@requires_auth
def api_billing_generate_invoices():
    try:
        # Placeholder until auto-invoicing is implemented
        return jsonify({'error': 'generate_invoices_not_implemented'}), 501
    except Exception as e:
        app.logger.error(f"Error in api_billing_generate_invoices: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# Documents list (JSON)
@app.route('/api/documents', methods=['GET'])
@requires_auth
def api_documents_list():
    try:
        documents = db.session.query(Document).options(
            db.joinedload(Document.case),
            db.joinedload(Document.uploaded_by)
        ).order_by(Document.created_at.desc()).all()
        items = [
            {
                'id': d.id,
                'name': d.name,
                'file_type': getattr(d, 'file_type', None),
                'file_size': getattr(d, 'file_size', None),
                'created_at': d.created_at.isoformat() if getattr(d, 'created_at', None) else None,
                'case': {
                    'id': d.case.id if getattr(d, 'case', None) else None,
                    'title': getattr(d.case, 'title', None) if getattr(d, 'case', None) else None,
                }
            }
            for d in documents
        ]
        return jsonify(items)
    except Exception as e:
        app.logger.error(f"Error in api_documents_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/documents/upload', methods=['POST'])
@requires_auth
def api_documents_upload():
    try:
        # Expecting multipart/form-data with fields: file, case_id (optional), name (optional)
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        case_id = request.form.get('case_id')
        case_id = int(case_id) if case_id else None
        custom_name = request.form.get('name')

        # Save file
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = secure_filename(custom_name or (file.filename or f"upload_{datetime.utcnow().timestamp()}"))
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Persist document
        doc = Document(
            name=filename,
            file_path=file_path,
            file_type=mimetypes.guess_type(filename)[0] or 'application/octet-stream',
            file_size=os.path.getsize(file_path),
            uploaded_by_id=_current_user_id(),
            case_id=case_id,
            created_at=datetime.utcnow()
        )
        db.session.add(doc)
        db.session.commit()
        return jsonify({'id': doc.id, 'name': doc.name}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_documents_upload: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# Intents and templates (list/apply)
@app.route('/api/intents', methods=['GET'])
@requires_auth
def api_intents_list():
    try:
        intents = Intent.query.filter_by(active=True).order_by(Intent.name.asc()).all()
        return jsonify([
            {
                'id': i.id,
                'key': i.key,
                'name': i.name,
                'department': getattr(i, 'department', None),
            }
            for i in intents
        ])
    except Exception as e:
        app.logger.error(f"Error in api_intents_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/cases/<int:case_id>/apply_intent', methods=['POST'])
@requires_auth
def api_case_apply_intent(case_id):
    try:
        c = db.session.get(Case, case_id)
        if c is None:
            abort(404)
        data = request.get_json() or {}
        intent_id = data.get('intent_id')
        if not intent_id:
            return jsonify({'error': 'intent_id required'}), 400
        intent = db.session.get(Intent, int(intent_id))
        if not intent or not intent.active:
            return jsonify({'error': 'intent not found'}), 404
        created_actions = []
        created_emails = []
        now = datetime.utcnow()
        # Create actions from templates
        for t in intent.action_templates:
            a = Action(
                title=t.title,
                description=t.description,
                status=t.default_status or 'pending',
                priority=t.default_priority or 'medium',
                due_date=(now + timedelta(days=t.due_in_days)) if getattr(t, 'due_in_days', None) else None,
                assigned_to_id=None,
                created_by_id=_current_user_id(),
            )
            db.session.add(a)
            db.session.flush()
            link = CaseAction(case_id=c.id, action_id=a.id, assigned_to_id=None, status=a.status)
            db.session.add(link)
            created_actions.append(a.id)
        # Create email drafts from templates
        for et in intent.email_templates:
            d = EmailDraft(
                case_id=c.id,
                to=None,
                subject=et.subject,
                body=et.body,
                attachments=None,
                status='draft',
                created_at=now,
                updated_at=now,
            )
            db.session.add(d)
            db.session.flush()
            created_emails.append(d.id)
        db.session.commit()
        return jsonify({'ok': True, 'actions': created_actions, 'emails': created_emails})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_case_apply_intent: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# Calendar list (JSON)
@app.route('/api/calendar', methods=['GET'])
@requires_auth
def api_calendar_list():
    try:
        events = CalendarEvent.query.options(
            db.joinedload(CalendarEvent.case),
            db.joinedload(CalendarEvent.client)
        ).order_by(CalendarEvent.start_at.asc()).all()
        items = [
            {
                'id': ev.id,
                'title': ev.title,
                'description': getattr(ev, 'description', None),
                'start_at': ev.start_at.isoformat() if getattr(ev, 'start_at', None) else None,
                'end_at': ev.end_at.isoformat() if getattr(ev, 'end_at', None) else None,
                'all_day': getattr(ev, 'all_day', False),
                'location': getattr(ev, 'location', None),
                'case': {
                    'id': ev.case.id if getattr(ev, 'case', None) else None,
                    'title': getattr(ev.case, 'title', None) if getattr(ev, 'case', None) else None,
                },
                'client': {
                    'id': ev.client.id if getattr(ev, 'client', None) else None,
                    'name': (f"{getattr(ev.client, 'first_name', '')} {getattr(ev.client, 'last_name', '')}").strip() if getattr(ev, 'client', None) else None,
                }
            }
            for ev in events
        ]
        return jsonify(items)
    except Exception as e:
        app.logger.error(f"Error in api_calendar_list: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/calendar', methods=['POST'])
@requires_auth
def api_calendar_create():
    try:
        data = request.get_json() or {}
        title = data.get('title')
        if not (title and isinstance(title, str)):
            return jsonify({'error': 'title required'}), 400
        description = data.get('description')
        location = data.get('location')
        all_day = bool(data.get('all_day'))
        reminder = int(data.get('reminder_minutes_before') or 0)
        case_id = data.get('case_id')
        client_id = data.get('client_id')
        start_iso = data.get('start_at')
        end_iso = data.get('end_at')
        start_at = datetime.fromisoformat(start_iso) if start_iso else None
        end_at = datetime.fromisoformat(end_iso) if end_iso else None

        ev = CalendarEvent(
            title=title,
            description=description,
            start_at=start_at,
            end_at=end_at,
            all_day=all_day,
            location=location,
            case_id=int(case_id) if case_id else None,
            client_id=int(client_id) if client_id else None,
            created_by_id=_current_user_id(),
            reminder_minutes_before=reminder,
            status='scheduled'
        )
        db.session.add(ev)
        db.session.commit()
        return jsonify({'id': ev.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_calendar_create: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# Settings (JSON)
@app.route('/api/settings', methods=['GET'])
@requires_auth
def api_settings():
    try:
        user_id = _current_user_id()
        if not user_id:
            return jsonify({'error': 'unauthorized'}), 401
        from models import OAuthAccount
        google_acc = OAuthAccount.query.filter_by(user_id=user_id, provider='google', status='connected').first()
        ms_acc = OAuthAccount.query.filter_by(user_id=user_id, provider='microsoft', status='connected').first()
        def acc_details(acc):
            if not acc:
                return None
            return {
                'connected_at': acc.connected_at.strftime('%Y-%m-%d %H:%M') if acc.connected_at else None,
                'expires_at': acc.expires_at.strftime('%Y-%m-%d %H:%M') if acc.expires_at else None,
                'scopes': acc.scopes
            }
        user_pref = NotificationPreference.query.filter_by(user_id=user_id).first()
        providers = {
            'google': {
                'connected': bool(google_acc),
                'details': acc_details(google_acc)
            },
            'microsoft': {
                'connected': bool(ms_acc),
                'details': acc_details(ms_acc)
            }
        }
        prefs = {
            'minutes_before': getattr(user_pref, 'minutes_before', 60),
            'email_enabled': getattr(user_pref, 'email_enabled', True)
        }
        return jsonify({'providers': providers, 'preferences': prefs})
    except Exception as e:
        app.logger.error(f"Error in api_settings: {str(e)}")
        return jsonify({'error': 'failed'}), 500

@app.route('/api/settings/notifications', methods=['POST'])
@requires_auth
def api_settings_notifications():
    try:
        user_id = _current_user_id()
        if not user_id:
            return jsonify({'error': 'unauthorized'}), 401
        data = request.get_json() or {}
        minutes_before = int(data.get('minutes_before') or 60)
        email_enabled = bool(data.get('email_enabled'))
        pref = NotificationPreference.query.filter_by(user_id=user_id).first()
        if not pref:
            pref = NotificationPreference(user_id=user_id)
            db.session.add(pref)
        pref.minutes_before = minutes_before
        pref.email_enabled = email_enabled
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in api_settings_notifications: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# Billing summary (JSON)
@app.route('/api/billing', methods=['GET'])
@requires_auth
def api_billing_summary():
    try:
        invoices = Invoice.query.options(db.joinedload(Invoice.client), db.joinedload(Invoice.case)).order_by(Invoice.created_at.desc()).limit(50).all()
        entries = TimeEntry.query.options(db.joinedload(TimeEntry.user), db.joinedload(TimeEntry.case), db.joinedload(TimeEntry.invoice)).order_by(TimeEntry.created_at.desc()).limit(50).all()
        expenses = Expense.query.options(db.joinedload(Expense.user), db.joinedload(Expense.case), db.joinedload(Expense.invoice)).order_by(Expense.created_at.desc()).limit(50).all()
        inv_items = [
            {
                'id': i.id,
                'invoice_number': getattr(i, 'invoice_number', None),
                'status': getattr(i, 'status', None),
                'total_amount': float(getattr(i, 'total_amount', 0) or 0),
                'balance_due': float(getattr(i, 'balance_due', 0) or 0),
                'created_at': i.created_at.isoformat() if getattr(i, 'created_at', None) else None,
                'case': {
                    'id': i.case.id if getattr(i, 'case', None) else None,
                    'title': getattr(i.case, 'title', None) if getattr(i, 'case', None) else None,
                }
            }
            for i in invoices
        ]
        entry_items = [
            {
                'id': t.id,
                'hours': float(getattr(t, 'hours', 0) or 0),
                'rate': float(getattr(t, 'rate', 0) or 0),
                'description': getattr(t, 'description', None),
                'created_at': t.created_at.isoformat() if getattr(t, 'created_at', None) else None,
                'case': {'id': t.case.id if getattr(t, 'case', None) else None, 'title': getattr(t.case, 'title', None) if getattr(t, 'case', None) else None}
            }
            for t in entries
        ]
        expense_items = [
            {
                'id': e.id,
                'amount': float(getattr(e, 'amount', 0) or 0),
                'description': getattr(e, 'description', None),
                'created_at': e.created_at.isoformat() if getattr(e, 'created_at', None) else None,
                'case': {'id': e.case.id if getattr(e, 'case', None) else None, 'title': getattr(e.case, 'title', None) if getattr(e, 'case', None) else None}
            }
            for e in expenses
        ]
        return jsonify({'invoices': inv_items, 'time_entries': entry_items, 'expenses': expense_items})
    except Exception as e:
        app.logger.error(f"Error in api_billing_summary: {str(e)}")
        return jsonify({'error': 'failed'}), 500

# ---- Payments / Trust / Invoice Ops ----
@app.route('/billing/invoices/<int:invoice_id>/pay-mock', methods=['POST'])
@login_required
@requires_auth
def invoice_pay_mock(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None:
        abort(404)
    amount = float(request.form.get('amount') or invoice.balance_due or 0)
    if amount <= 0:
        flash('Invalid amount.', 'warning')
        return redirect(url_for('billing'))
    try:
        pay = Payment(
            invoice_id=invoice.id,
            payment_date=datetime.utcnow().date(),
            amount=amount,
            payment_method='online',
            status='completed'
        )
        db.session.add(pay)
        db.session.flush()
        invoice.add_payment(amount)
        db.session.commit()
        flash('Payment recorded (mock).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Payment failed: {str(e)}', 'danger')
    return redirect(url_for('billing'))

@app.route('/billing/invoices/<int:invoice_id>/payments', methods=['POST'])
@login_required
@requires_auth
def post_payment(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None:
        abort(404)
    try:
        amount = float(request.form.get('amount'))
        method = request.form.get('payment_method') or 'check'
        ref = request.form.get('reference_number')
        p = Payment(invoice_id=invoice.id, payment_date=datetime.utcnow().date(), amount=amount, payment_method=method, reference_number=ref, status='completed')
        db.session.add(p)
        db.session.flush()
        invoice.add_payment(amount)
        db.session.commit()
        flash('Payment posted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to post payment: {str(e)}', 'danger')
    return redirect(url_for('billing'))

@app.route('/billing/trust/transfer', methods=['POST'])
@login_required
@requires_auth
def trust_transfer():
    try:
        client_id = int(request.form.get('client_id'))
        case_id = request.form.get('case_id')
        case_id = int(case_id) if case_id else None
        amount = float(request.form.get('amount'))
        description = request.form.get('description') or 'Trust transfer'
        # Compute balance_after naive (for demo): sum deposits - withdrawals
        prev = db.session.query(db.func.coalesce(db.func.sum(TrustAccount.amount), 0)).filter_by(client_id=client_id).scalar() or 0
        balance_after = prev + amount
        ta = TrustAccount(client_id=client_id, case_id=case_id, transaction_date=datetime.utcnow().date(), transaction_type='transfer', amount=amount, balance_after=balance_after, description=description)
        db.session.add(ta)
        db.session.commit()
        flash('Trust transfer recorded.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Trust transfer failed: {str(e)}', 'danger')
    return redirect(url_for('billing'))

@app.route('/billing/invoices/<int:invoice_id>/pdf')
@login_required
@requires_auth
def invoice_pdf(invoice_id):
    # Redirect legacy HTML route to the proper API-based PDF generator
    return redirect(url_for('api_invoice_pdf', invoice_id=invoice_id), code=302)

# New: Proper PDF generation API returning application/pdf
@app.route('/api/billing/invoices/<int:invoice_id>/pdf', methods=['GET'])
@login_required
@requires_auth
def api_invoice_pdf(invoice_id):
    try:
        invoice = db.session.get(Invoice, invoice_id)
        if invoice is None:
            abort(404)
        try:
            # Prefer ReportLab if installed
            from reportlab.lib.pagesizes import LETTER
            from reportlab.pdfgen import canvas
            import io
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=LETTER)
            width, height = LETTER
            y = height - 72
            c.setFont("Helvetica-Bold", 14)
            c.drawString(72, y, f"Invoice {getattr(invoice, 'invoice_number', invoice.id)}")
            y -= 24
            c.setFont("Helvetica", 11)
            c.drawString(72, y, f"Client: {getattr(invoice.client, 'first_name', '')} {getattr(invoice.client, 'last_name', '')}")
            y -= 18
            c.drawString(72, y, f"Case: {getattr(getattr(invoice, 'case', None), 'title', '-')}")
            y -= 18
            c.drawString(72, y, f"Status: {getattr(invoice, 'status', '-')}")
            y -= 18
            c.drawString(72, y, f"Total Amount: {float(getattr(invoice, 'total_amount', 0) or 0):.2f}")
            y -= 18
            c.drawString(72, y, f"Balance Due: {float(getattr(invoice, 'balance_due', 0) or 0):.2f}")
            y -= 24
            c.drawString(72, y, f"Created: {invoice.created_at.strftime('%Y-%m-%d') if getattr(invoice, 'created_at', None) else '-'}")
            c.showPage()
            c.save()
            pdf_bytes = buf.getvalue()
            buf.close()
            return Response(pdf_bytes, mimetype='application/pdf', headers={
                'Content-Disposition': f'inline; filename="invoice_{invoice_id}.pdf"'
            })
        except Exception as e:
            # ReportLab not installed or generation failed
            current_app.logger.error(f"PDF generation failed: {str(e)}")
            return jsonify({'error': 'PDF generator not available'}), 501
    except Exception as e:
        current_app.logger.error(f"/api/billing/invoices/{invoice_id}/pdf error: {str(e)}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/billing/invoices/<int:invoice_id>/email')
@login_required
@requires_auth
def invoice_email(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None:
        abort(404)
    to_email = invoice.client.email if invoice.client and invoice.client.email else None
    subject = f"Invoice {invoice.invoice_number}"
    body = f"Dear {invoice.client.first_name if invoice.client else 'Client'},\nYour invoice total is {invoice.total_amount}."
    _send_email(to_email, subject, body)
    flash('Invoice emailed (mock/SMTP).', 'success')
    return redirect(url_for('billing'))

# ---- Calendar Routes ----
@app.route('/calendar')
@login_required
@requires_auth
def calendar():
    events = CalendarEvent.query.options(
        db.joinedload(CalendarEvent.case),
        db.joinedload(CalendarEvent.client)
    ).order_by(CalendarEvent.start_at.asc()).all()
    return render_template('calendar.html', events=events)

def _ics_escape(text: str) -> str:
    return (text or '').replace('\\', '\\\\').replace('\n', '\\n').replace(',', '\\,').replace(';', '\\;')

@app.route('/calendar/ics')
@login_required
@requires_auth
def calendar_ics():
    events = CalendarEvent.query.order_by(CalendarEvent.start_at.asc()).all()
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//LegalIntake Pro//Calendar//EN'
    ]
    for ev in events:
        dtstart = ev.start_at.strftime('%Y%m%dT%H%M%SZ') if ev.start_at else ''
        dtend = ev.end_at.strftime('%Y%m%dT%H%M%SZ') if ev.end_at else ''
        lines.extend([
            'BEGIN:VEVENT',
            f'SUMMARY:{_ics_escape(ev.title)}',
            f'DESCRIPTION:{_ics_escape(ev.description or "")}',
            f'DTSTART:{dtstart}',
            f'DTEND:{dtend}' if dtend else f'DURATION:PT60M',
            f'LOCATION:{_ics_escape(ev.location or "")}',
            'END:VEVENT'
        ])
    lines.append('END:VCALENDAR')
    ics_content = '\r\n'.join(lines)
    return Response(ics_content, mimetype='text/calendar')

@app.route('/calendar/add', methods=['GET', 'POST'])
@login_required
@requires_auth
def add_calendar_event():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            location = request.form.get('location')
            all_day = request.form.get('all_day') == 'on'
            reminder = int(request.form.get('reminder_minutes_before') or 0)
            case_id = request.form.get('case_id') or None
            client_id = request.form.get('client_id') or None

            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time') or '09:00'
            end_date = request.form.get('end_date') or start_date
            end_time = request.form.get('end_time') or ''

            # Compose datetimes
            if all_day:
                start_at = datetime.strptime(start_date, '%Y-%m-%d')
                end_at = None
            else:
                start_at = datetime.strptime(f"{start_date} {start_time}", '%Y-%m-%d %H:%M')
                end_at = datetime.strptime(f"{end_date} {end_time}", '%Y-%m-%d %H:%M') if end_time else None

            ev = CalendarEvent(
                title=title,
                description=description,
                start_at=start_at,
                end_at=end_at,
                all_day=all_day,
                location=location,
                case_id=int(case_id) if case_id else None,
                client_id=int(client_id) if client_id else None,
                created_by_id=session.get('user_id'),
                reminder_minutes_before=reminder,
                status='scheduled'
            )
            db.session.add(ev)
            db.session.commit()
            # Redirect
            if case_id:
                return redirect(url_for('view_case', case_id=case_id))
            return redirect(url_for('calendar'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating event: {str(e)}', 'danger')
    # GET
    cases = Case.query.order_by(Case.created_at.desc()).all()
    clients = Client.query.order_by(Client.last_name, Client.first_name).all()
    return render_template('add_event.html', cases=cases, clients=clients, selected_case_id=None)

@app.route('/cases/<int:case_id>/events/add', methods=['GET', 'POST'])
@login_required
@requires_auth
def add_case_event(case_id):
    if request.method == 'POST':
        return add_calendar_event()
    cases = Case.query.order_by(Case.created_at.desc()).all()
    clients = Client.query.order_by(Client.last_name, Client.first_name).all()
    return render_template('add_event.html', cases=cases, clients=clients, selected_case_id=case_id)

# ---- Settings and OAuth stubs ----
@app.route('/settings', methods=['GET'])
@login_required
@requires_auth
def settings():
    # Determine provider connection status per current user (session-based)
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    from models import OAuthAccount
    google_acc = OAuthAccount.query.filter_by(user_id=user_id, provider='google', status='connected').first()
    ms_acc = OAuthAccount.query.filter_by(user_id=user_id, provider='microsoft', status='connected').first()
    def acc_details(acc):
        if not acc:
            return None
        return {
            'connected_at': acc.connected_at.strftime('%Y-%m-%d %H:%M') if acc.connected_at else None,
            'expires_at': acc.expires_at.strftime('%Y-%m-%d %H:%M') if acc.expires_at else None,
            'scopes': acc.scopes
        }
    # Notification preferences (user-level)
    from models import NotificationPreference
    user_pref = NotificationPreference.query.filter_by(user_id=user_id).first()
    providers = {
        'google': {
            'connected': bool(google_acc),
            'redirect_url': url_for('auth_start', provider='google'),
            'details': acc_details(google_acc)
        },
        'microsoft': {
            'connected': bool(ms_acc),
            'redirect_url': url_for('auth_start', provider='microsoft'),
            'details': acc_details(ms_acc)
        }
    }
    return render_template('settings.html', providers=providers, user_pref=user_pref)

@app.route('/auth/<provider>/start')
@login_required
@requires_auth
def auth_start(provider):
    if provider not in ('google', 'microsoft'):
        abort(404)
    # Stub: immediately redirect to callback as if provider authorized
    return redirect(url_for('auth_callback', provider=provider, code='mock_code'))

@app.route('/auth/<provider>/callback')
@login_required
@requires_auth
def auth_callback(provider):
    if provider not in ('google', 'microsoft'):
        abort(404)
    from models import OAuthAccount
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    acc = OAuthAccount.query.filter_by(user_id=user_id, provider=provider).first()
    if not acc:
        acc = OAuthAccount(user_id=user_id, provider=provider)
        db.session.add(acc)
    acc.status = 'connected'
    acc.access_token = 'mock_access_token'
    acc.refresh_token = 'mock_refresh_token'
    acc.expires_at = datetime.utcnow() + timedelta(hours=1)
    acc.scopes = 'calendar.read,calendar.write'
    db.session.commit()
    flash(f'{provider.title()} connected (mock).', 'success')
    return redirect(url_for('settings'))

@app.route('/settings/notifications', methods=['POST'])
@login_required
@requires_auth
def save_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    from models import NotificationPreference
    try:
        minutes_before = int(request.form.get('minutes_before') or 60)
        email_enabled = True if request.form.get('email_enabled') == 'on' else False
        pref = NotificationPreference.query.filter_by(user_id=user_id).first()
        if not pref:
            pref = NotificationPreference(user_id=user_id)
            db.session.add(pref)
        pref.minutes_before = minutes_before
        pref.email_enabled = email_enabled
        db.session.commit()
        flash('Notification preferences saved.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to save preferences: {str(e)}', 'danger')
    return redirect(url_for('settings'))

@app.route('/auth/<provider>/disconnect', methods=['POST'])
@login_required
@requires_auth
def auth_disconnect(provider):
    if provider not in ('google', 'microsoft'):
        abort(404)
    from models import OAuthAccount
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    acc = OAuthAccount.query.filter_by(user_id=user_id, provider=provider).first()
    if acc:
        acc.status = 'revoked'
        db.session.commit()
    flash(f'{provider.title()} disconnected.', 'info')
    return redirect(url_for('settings'))

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
            # Basic server-side validation: type and size
            if not _is_allowed_audio(file.filename, getattr(file, 'mimetype', '')):
                return jsonify({'error': 'Unsupported audio type'}), 415
            try:
                clen = request.content_length or 0
                if clen and clen > app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024):
                    return jsonify({'error': 'File too large'}), 413
            except Exception:
                pass
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

# ---- Staff JSON APIs for transcription ----
@app.route('/api/transcribe', methods=['POST'])
@requires_auth
def api_transcribe_start():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['audio_file']
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    # Validate file type and size
    if not _is_allowed_audio(file.filename, getattr(file, 'mimetype', '')):
        return jsonify({'error': 'Unsupported audio type'}), 415
    try:
        clen = request.content_length or 0
        if clen and clen > app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024):
            return jsonify({'error': 'File too large'}), 413
    except Exception:
        pass
    filename = secure_filename(file.filename or f"recording_{datetime.utcnow().timestamp()}.webm")
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_path)
    try:
        service = STTService()
        transcript_id = service.start_transcription(temp_path)
        # Persist Transcript row if not exists
        t = Transcript(
            provider='assemblyai',
            external_id=transcript_id,
            status='processing',
            user_id=_current_user_id()
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({'status': 'processing', 'transcript_id': transcript_id})
    except Exception as e:
        app.logger.error(f"api_transcribe_start error: {str(e)}")
        return jsonify({'error': 'Failed to start transcription'}), 500
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

@app.route('/api/transcripts/<string:external_id>', methods=['GET'])
@requires_auth
def api_transcript_status(external_id: str):
    # Look up Transcript by external id
    t = Transcript.query.filter_by(external_id=external_id).first()
    if not t:
        # In case row not persisted earlier, return minimal status
        t = Transcript(provider='assemblyai', external_id=external_id, status='processing')
        db.session.add(t)
        db.session.commit()
    # If not completed, try to refresh from provider
    if t.status != 'completed':
        try:
            service = STTService()
            data = service.get_transcription_status(external_id)
            # Expect data like {'status': 'completed'|'processing'|'error', 'text': '...'}
            new_status = data.get('status') or t.status
            t.status = new_status
            if new_status == 'completed' and data.get('text'):
                t.text = data.get('text')
            if new_status == 'error':
                t.text = None
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Error fetching transcription status: {str(e)}")
            return jsonify({'error': str(e)}), 500
    payload = {
        'transcript_id': external_id,
        'status': t.status,
        'text': getattr(t, 'text', None),
        'error': getattr(t, 'error', None),
    }
    return jsonify(payload)

# -------- Client Portal Login/Logout -------- #
@app.route('/portal/login', methods=['GET', 'POST'])
def portal_login():
    if request.method == 'POST':
        # Support legacy form POST for compatibility
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        cu = ClientUser.query.filter(db.func.lower(ClientUser.email)==email).first()
        if cu and cu.check_password(password):
            session['client_user_id'] = cu.id
            session.permanent = True
            flash('Signed in to client portal.', 'success')
            return redirect(url_for('portal_invoices'))
        else:
            flash('Invalid portal credentials', 'danger')
            return redirect(url_for('portal_login'))
    # For GET, redirect to Next.js portal login page
    return redirect('http://localhost:3000/portal/login', code=301)

# JSON endpoint for portal login to be called from Next.js
@app.route('/api/portal/login', methods=['POST'])
def api_portal_login():
    try:
        data = request.get_json(silent=True) or {}
        email = str(data.get('email', '')).strip().lower()
        password = str(data.get('password', ''))
        if not email or not password:
            return jsonify({'ok': False, 'error': 'Missing credentials'}), 400
        cu = ClientUser.query.filter(db.func.lower(ClientUser.email)==email).first()
        if cu and cu.check_password(password):
            session['client_user_id'] = cu.id
            session.permanent = True
            return jsonify({'ok': True})
        return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        app.logger.error(f"portal login error: {str(e)}")
        return jsonify({'ok': False, 'error': 'Server error'}), 500

@app.route('/portal/logout')
def portal_logout():
    session.pop('client_user_id', None)
    flash('Signed out of client portal.', 'info')
    return redirect(url_for('portal_login'))

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

def _analyze_text(text: str) -> dict:
    """Analyze intake text using AssemblyAI if enabled, else rule-based. Returns normalized dict."""
    result = None
    if USE_AAI_ANALYZER and ASSEMBLYAI_API_KEY:
        try:
            result = analyze_with_aai(text)
        except Exception as e:
            app.logger.error(f"analyze_with_aai failed in _analyze_text: {str(e)}; falling back")
    if result is None:
        result = analyze_intake_text_scenarios(text)
    # Ensure keys exist
    out = {
        'category': result.get('category'),
        'urgency': result.get('urgency'),
        'key_facts': result.get('key_facts', {}),
        'dates': result.get('dates', {}),
        'parties': result.get('parties', {}),
        'suggested_actions': result.get('suggested_actions', []),
        'checklists': result.get('checklists', {}),
        'department': result.get('department'),
        'confidence': result.get('confidence'),
        'priority': result.get('priority'),
    }
    # Derive priority from urgency if missing
    if not out.get('priority') and out.get('urgency'):
        u = str(out['urgency']).strip().lower()
        if u == 'high':
            out['priority'] = 'high'
        elif u.startswith('med'):
            out['priority'] = 'medium'
        else:
            out['priority'] = 'low'
    return out

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

        # Analyze (AssemblyAI if enabled, else rule-based)
        analysis = _analyze_text(text)

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
                # Auto-queue preservation/notice letters to send in 1 hour
                fname_l = (fname or '').lower()
                should_queue = any(k in fname_l for k in [
                    'preservation', 'police_report_request', 'dot_camera_request', 'hospital_lit_hold', 'employment_lit_hold', 'medical_records_request'
                ])
                if should_queue:
                    subject = _extract_subject_from_letter(content) or (draft.subject or 'Legal Notice')
                    q = EmailQueue(
                        case_id=new_case.id,
                        draft_id=draft.id,
                        to=None,
                        subject=subject,
                        body=content,
                        send_after=datetime.utcnow() + timedelta(hours=1),
                        status='pending'
                    )
                    db.session.add(q)
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

@app.route('/api/intake/auto/staff', methods=['POST'])
@requires_auth
def auto_intake_staff():
    """Staff-auth version of auto_intake using Basic Auth, no session required."""
    data = request.get_json()
    text = (data or {}).get('text') or ''
    client = (data or {}).get('client') or {}
    case_title = (data or {}).get('title') or 'Client Intake'

    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400

    try:
        # Resolve a user id for created_by fields
        user_id = _current_user_id()

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

        # Analyze (AssemblyAI if enabled, else rule-based)
        analysis = _analyze_text(text)

        # Create case
        new_case = Case(
            title=case_title,
            description=text,
            case_type=analysis.get('category'),
            status='open',
            priority=(analysis.get('priority') or 'Medium').lower(),
            client_id=db_client.id,
            created_by_id=user_id,
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
                created_by_id=user_id
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

        # Create draft letters as documents (no email sent in dev)
        letters = _auto_letters(analysis.get('category') or '', analysis, client_name=f"{db_client.first_name} {db_client.last_name}")
        created_docs = []
        email_drafts_created = []
        for fname, content in letters:
            doc = _write_document(new_case.id, fname, content, uploaded_by_id=user_id)
            created_docs.append(doc.id)
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

        # Deadlines (reuse same logic by calling category-specific block)
        category = analysis.get('category', '')
        base_date = datetime.utcnow()
        dates_list = analysis.get('dates', [])
        if isinstance(dates_list, list) and dates_list:
            try:
                base_date = datetime.strptime(dates_list[0], '%Y-%m-%d')
            except Exception:
                pass

        if category.startswith('Personal Injury'):
            evidence_deadline = base_date + timedelta(days=EVIDENCE_RETENTION_DAYS)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Security Footage Retention Deadline',
                due_date=evidence_deadline,
                source='slip_fall_evidence',
                notes=f'Security footage typically deleted after {EVIDENCE_RETENTION_DAYS} days. URGENT: Send preservation letter immediately.'
            ))
            statute_deadline = base_date + timedelta(days=730)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Statute of Limitations',
                due_date=statute_deadline,
                source='statute_of_limitations',
                notes='Must file lawsuit before this date. Verify state-specific statute.'
            ))
            medical_deadline = datetime.utcnow() + timedelta(days=14)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Medical Records Collection',
                due_date=medical_deadline,
                source='medical_records',
                notes='Obtain all medical records within 14 days.'
            ))
        elif category.startswith('Car Accident'):
            police_deadline = datetime.utcnow() + timedelta(days=7)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Police Report Request',
                due_date=police_deadline,
                source='police_report',
                notes='Request police report and dash cam footage within 7 days.'
            ))
            camera_deadline = datetime.utcnow() + timedelta(days=30)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Traffic Camera Footage Deadline',
                due_date=camera_deadline,
                source='traffic_camera',
                notes='Traffic camera footage typically retained 30-90 days. Request immediately.'
            ))
            medical_eval_deadline = datetime.utcnow() + timedelta(days=2)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Medical Evaluation',
                due_date=medical_eval_deadline,
                source='medical_evaluation',
                notes='Schedule medical evaluation within 48 hours of accident.'
            ))
            statute_deadline = base_date + timedelta(days=730)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Statute of Limitations',
                due_date=statute_deadline,
                source='statute_of_limitations',
                notes='Must file lawsuit before this date. Verify state-specific statute.'
            ))
        elif category.startswith('Employment Law'):
            eeoc_deadline = base_date + timedelta(days=180)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='EEOC Filing Deadline (Federal)',
                due_date=eeoc_deadline,
                source='eeoc_filing',
                notes='Must file EEOC charge within 180 days (300 days in deferral states). CRITICAL DEADLINE.'
            ))
            evidence_deadline = datetime.utcnow() + timedelta(days=7)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Send Litigation Hold Letter',
                due_date=evidence_deadline,
                source='employment_evidence',
                notes='Send litigation hold to employer immediately. Emails may be deleted.'
            ))
            personnel_deadline = datetime.utcnow() + timedelta(days=14)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Personnel File Request',
                due_date=personnel_deadline,
                source='personnel_file',
                notes='Request complete personnel file within 14 days.'
            ))
        elif category.startswith('Medical Malpractice'):
            records_deadline = datetime.utcnow() + timedelta(days=7)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Medical Records Request (URGENT)',
                due_date=records_deadline,
                source='medical_records',
                notes='Request all medical records immediately. Include operative reports, count sheets, imaging.'
            ))
            expert_deadline = datetime.utcnow() + timedelta(days=30)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Retain Medical Expert Witness',
                due_date=expert_deadline,
                source='expert_witness',
                notes='Retain medical expert for case review and Certificate of Merit.'
            ))
            merit_deadline = datetime.utcnow() + timedelta(days=60)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Certificate of Merit',
                due_date=merit_deadline,
                source='certificate_of_merit',
                notes='Many states require Certificate of Merit within 60-90 days of filing. Verify state requirements.'
            ))
            statute_deadline = base_date + timedelta(days=730)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Statute of Limitations',
                due_date=statute_deadline,
                source='statute_of_limitations',
                notes='Medical malpractice has SHORT statute. May be 1-2 years. Verify state law and discovery rule.'
            ))
            discovery_deadline = datetime.utcnow() + timedelta(days=365)
            db.session.add(Deadline(
                case_id=new_case.id,
                name='Discovery Rule Deadline',
                due_date=discovery_deadline,
                source='discovery_rule',
                notes='Alternative statute from date of discovery. Verify which date applies in your state.'
            ))

        db.session.commit()

        # Best-effort link latest transcript for this user
        try:
            t = Transcript.query.filter_by(user_id=user_id).order_by(Transcript.created_at.desc()).first()
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
        app.logger.error(f"Error in auto_intake_staff: {str(e)}")
        return jsonify({'error': 'Server error'}), 500
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
