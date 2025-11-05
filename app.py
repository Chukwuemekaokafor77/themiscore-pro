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
from models import Case

# Import database models
from models import db, User, Client, Case, Action, Document, CaseNote, CaseAction, AIInsight, Lawyer, Referral

# Import utility functions
from utils import get_pagination, apply_case_filters, get_sort_params, analyze_case

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
        # Check if the post request has the file part
        if 'audio_file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['audio_file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file:
            # Save the file temporarily
            filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(temp_path)
            
            try:
                # Upload the file to AssemblyAI
                def read_file(file_path, chunk_size=5242880):
                    with open(file_path, 'rb') as _file:
                        while True:
                            data = _file.read(chunk_size)
                            if not data:
                                break
                            yield data
                
                # Upload the file
                upload_response = requests.post(
                    ASSEMBLYAI_UPLOAD_URL,
                    headers=ASSEMBLYAI_HEADERS,
                    data=read_file(temp_path)
                )
                upload_response.raise_for_status()
                upload_url = upload_response.json()['upload_url']
                
                # Start transcription with analysis
                transcript_request = {
                    'audio_url': upload_url,
                    'speaker_labels': True,
                    'sentiment_analysis': True,
                    'entity_detection': True,
                    'iab_categories': True,
                    'auto_highlights': True
                }
                
                transcript_response = requests.post(
                    ASSEMBLYAI_TRANSCRIPTION_URL,
                    json=transcript_request,
                    headers=ASSEMBLYAI_HEADERS
                )
                transcript_response.raise_for_status()
                
                transcript_id = transcript_response.json()['id']
                
                # Clean up the temporary file
                try:
                    os.remove(temp_path)
                except:
                    pass
                
                return jsonify({
                    'status': 'processing',
                    'transcript_id': transcript_id
                })
                
            except Exception as e:
                # Clean up the temporary file in case of error
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
                app.logger.error(f"Error processing audio file: {str(e)}")
                return jsonify({'error': str(e)}), 500
    
    return render_template('transcribe.html')

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
                    filename=filename,
                    file_path=file_path,
                    mime_type=file.mimetype,
                    file_size=os.path.getsize(file_path),
                    uploaded_by=current_user.id,
                    uploaded_at=datetime.utcnow()
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

# Add more API endpoints for clients, actions, and other resources...

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'An internal error occurred'}), 500

# Initialize AI Analyzer
from ai_services import case_analyzer

@app.route('/transcribe/status/<transcript_id>')
def transcription_status(transcript_id):
    try:
        # Get AI analysis from the transcript
        analysis = case_analyzer.analyze_audio_transcript(transcript_id)
        
        if 'error' in analysis:
            return jsonify({'error': analysis['error']}), 500
            
        # Get the transcription text from analysis
        transcription = analysis.get('text', '')
        
        # Create a new case with the transcription and analysis
        case = Case(
            title=f"Transcribed Case - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description=transcription,
            status='new',
            created_at=datetime.utcnow()
        )
        db.session.add(case)
        db.session.flush()  # Get the case ID
        
        # Save AI insights
        if 'case_analysis' in analysis:
            insight = AIInsight(
                case_id=case.id,
                analysis_type='initial',
                content=json.dumps(analysis),
                created_at=datetime.utcnow()
            )
            db.session.add(insight)
        
        db.session.commit()
        
        return jsonify({
            'status': 'completed',
            'text': transcription,
            'ai_analysis': analysis,
            'case_id': case.id
        })
            
    except Exception as e:
        app.logger.error(f"Error in transcription_status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze/text', methods=['POST'])
def analyze_text():
    """Analyze text with AI and return case insights."""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
            
        # Get AI analysis using the case_analyzer
        analysis = case_analyzer.analyze_text(text)
        
        # If there's an error in analysis, return it
        if 'error' in analysis:
            return jsonify(analysis), 400
            
        return jsonify(analysis)
        
    except Exception as e:
        app.logger.error(f"Error in analyze_text: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze/case/<int:case_id>', methods=['POST'])
def analyze_case(case_id):
    """Re-analyze a case with updated AI models."""
    try:
        case = Case.query.get_or_404(case_id)
        
        # Get the case text to analyze
        text_to_analyze = f"{case.title}. {case.description}"
        
        # Get AI analysis using the case_analyzer
        analysis = case_analyzer.analyze_text(text_to_analyze)
        
        # Save the new analysis
        insight = AIInsight(
            case_id=case.id,
            analysis_type='reanalysis',
            content=json.dumps(analysis),
            created_at=datetime.utcnow()
        )
        db.session.add(insight)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'analysis': analysis
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in analyze_case: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
