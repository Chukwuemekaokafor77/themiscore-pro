from datetime import datetime, timedelta
import secrets
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='staff')  # 'admin', 'attorney', 'staff', 'paralegal'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_cases = db.relationship('Case', foreign_keys='Case.assigned_to_id', back_populates='assigned_user')
    created_cases = db.relationship('Case', foreign_keys='Case.created_by_id', back_populates='creator')
    created_actions = db.relationship('Action', foreign_keys='Action.created_by_id', back_populates='created_by')
    assigned_actions = db.relationship('Action', foreign_keys='Action.assigned_to_id', back_populates='assigned_to')
    uploaded_documents = db.relationship('Document', foreign_keys='Document.uploaded_by_id', back_populates='uploaded_by')
    case_notes = db.relationship('CaseNote', foreign_keys='CaseNote.created_by_id', back_populates='created_by')
    case_actions_assigned = db.relationship('CaseAction', foreign_keys='CaseAction.assigned_to_id', back_populates='assigned_to')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'is_active': self.is_active
        }


class CaseStatusAudit(db.Model):
    """Audit trail for case status changes"""
    __tablename__ = 'case_status_audit'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    from_status = db.Column(db.String(50), nullable=True)
    to_status = db.Column(db.String(50), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case = db.relationship('Case', backref=db.backref('status_audit', lazy=True, cascade='all, delete-orphan'))
    changed_by = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'from_status': self.from_status,
            'to_status': self.to_status,
            'changed_by_id': self.changed_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Intent(db.Model):
    """Configurable intent representing a high-level case category."""
    __tablename__ = 'intent'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)  # e.g., 'personal_injury_premises'
    name = db.Column(db.String(200), nullable=False)  # e.g., 'Personal Injury - Premises Liability'
    department = db.Column(db.String(100), nullable=True)
    priority_default = db.Column(db.String(20), default='medium')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    action_templates = db.relationship('ActionTemplate', back_populates='intent', cascade='all, delete-orphan')
    email_templates = db.relationship('EmailTemplate', back_populates='intent', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'name': self.name,
            'department': self.department,
            'priority_default': self.priority_default,
            'active': self.active,
        }


class IntentRule(db.Model):
    """Optional matching rule for an intent (simple pattern or JSON rule)."""
    __tablename__ = 'intent_rule'

    id = db.Column(db.Integer, primary_key=True)
    intent_id = db.Column(db.Integer, db.ForeignKey('intent.id'), nullable=False)
    pattern = db.Column(db.Text, nullable=False)  # free-form string or JSON describing match
    weight = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    intent = db.relationship('Intent', backref=db.backref('rules', lazy=True, cascade='all, delete-orphan'))


class ActionTemplate(db.Model):
    """Template for actions to generate for an intent."""
    __tablename__ = 'action_template'

    id = db.Column(db.Integer, primary_key=True)
    intent_id = db.Column(db.Integer, db.ForeignKey('intent.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    default_status = db.Column(db.String(50), default='pending')
    default_priority = db.Column(db.String(20), default='medium')
    due_in_days = db.Column(db.Integer, nullable=True)  # relative due date

    intent = db.relationship('Intent', back_populates='action_templates')


class EmailTemplate(db.Model):
    """Template for emails/letters to generate for an intent."""
    __tablename__ = 'email_template'

    id = db.Column(db.Integer, primary_key=True)
    intent_id = db.Column(db.Integer, db.ForeignKey('intent.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)

    intent = db.relationship('Intent', back_populates='email_templates')


class AnalyzerLog(db.Model):
    """Metrics/logs for analyzer calls (AAI or rule-based)."""
    __tablename__ = 'analyzer_log'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)  # 'aai' | 'rules'
    model = db.Column(db.String(100), nullable=True)
    latency_ms = db.Column(db.Integer, nullable=True)
    input_tokens = db.Column(db.Integer, nullable=True)
    output_tokens = db.Column(db.Integer, nullable=True)
    succeeded = db.Column(db.Boolean, default=True)
    error = db.Column(db.Text, nullable=True)
    text_chars = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=True)


class EmailQueue(db.Model):
    """Queue for scheduled outbound emails (e.g., preservation letters)."""
    __tablename__ = 'email_queue'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=True)
    draft_id = db.Column(db.Integer, db.ForeignKey('email_draft.id'), nullable=True)
    to = db.Column(db.String(255), nullable=True)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    send_after = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending|sent|failed
    attempts = db.Column(db.Integer, default=0)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case = db.relationship('Case', backref=db.backref('email_queue', lazy=True))
    draft = db.relationship('EmailDraft', backref=db.backref('queue_item', uselist=False))

    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'draft_id': self.draft_id,
            'to': self.to,
            'subject': self.subject,
            'send_after': self.send_after.isoformat() if self.send_after else None,
            'status': self.status,
            'attempts': self.attempts,
            'last_error': self.last_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

class NotificationPreference(db.Model):
    """Reminder/notification preferences per user or client."""
    __tablename__ = 'notification_preference'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    email_enabled = db.Column(db.Boolean, default=True)
    minutes_before = db.Column(db.Integer, default=60)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='notification_prefs')
    client = db.relationship('Client', backref='notification_prefs')


class EmailDraft(db.Model):
    """Draft emails stored for review/sending (dev-only)."""
    __tablename__ = 'email_draft'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=True)
    to = db.Column(db.String(255), nullable=True)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    attachments = db.Column(db.Text, nullable=True)  # comma-separated document IDs or paths
    status = db.Column(db.String(20), default='draft')  # draft|sent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case = db.relationship('Case', backref=db.backref('email_drafts', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'to': self.to,
            'subject': self.subject,
            'body': self.body,
            'attachments': self.attachments,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Deadline(db.Model):
    """Deadline tracking for cases (e.g., statutes, evidence retention, EEOC)."""
    __tablename__ = 'deadline'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    source = db.Column(db.String(100), nullable=True)  # e.g., 'slip_fall_evidence', 'eeoc', 'statute'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case = db.relationship('Case', backref=db.backref('deadlines', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'name': self.name,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'source': self.source,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Client(db.Model):
    """Client information model"""
    __tablename__ = 'client'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cases = db.relationship('Case', back_populates='client', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'case_count': len(self.cases)
        }


class Case(db.Model):
    """Case information model"""
    __tablename__ = 'case'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    case_type = db.Column(db.String(100))
    
    # AI Classification field
    category = db.Column(db.String(50), nullable=True)  # e.g., "family", "housing", etc.
    
    status = db.Column(db.String(50), default='open')
    priority = db.Column(db.String(20), default='medium')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    client = db.relationship('Client', back_populates='cases')
    assigned_user = db.relationship('User', foreign_keys=[assigned_to_id], back_populates='assigned_cases')
    creator = db.relationship('User', foreign_keys=[created_by_id], back_populates='created_cases')
    documents = db.relationship('Document', back_populates='case', cascade='all, delete-orphan')
    notes = db.relationship('CaseNote', back_populates='case', cascade='all, delete-orphan')
    case_actions = db.relationship('CaseAction', back_populates='case', cascade='all, delete-orphan')
    actions = db.relationship('Action', secondary='case_action', viewonly=True,
                            primaryjoin='Case.id == CaseAction.case_id',
                            secondaryjoin='Action.id == CaseAction.action_id',
                            back_populates='cases')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'case_type': self.case_type,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'client': self.client.to_dict() if self.client else None,
            'assigned_to': self.assigned_user.to_dict() if self.assigned_user else None,
            'document_count': len(self.documents),
            'note_count': len(self.notes),
            'actions': [ca.action.to_dict() for ca in self.case_actions],
            'category': self.category,
            'insights': [insight.to_dict() for insight in self.insights],
            'referrals': [referral.to_dict() for referral in self.referrals]
        }


class Action(db.Model):
    """Action items model"""
    __tablename__ = 'action'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    action_type = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.String(20), default='medium')
    due_date = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], back_populates='created_actions')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], back_populates='assigned_actions')
    documents = db.relationship('Document', back_populates='action', cascade='all, delete-orphan')
    case_actions = db.relationship('CaseAction', back_populates='action', cascade='all, delete-orphan')
    cases = db.relationship('Case', secondary='case_action', viewonly=True, 
                          primaryjoin='Action.id == CaseAction.action_id',
                          secondaryjoin='Case.id == CaseAction.case_id',
                          back_populates='actions')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'action_type': self.action_type,
            'status': self.status,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by.to_dict() if self.created_by else None,
            'assigned_to': self.assigned_to.to_dict() if self.assigned_to else None,
            'document_count': len(self.documents)
        }


class CaseAction(db.Model):
    """Association object for actions assigned to cases with metadata"""
    __tablename__ = 'case_action'

    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), primary_key=True)
    action_id = db.Column(db.Integer, db.ForeignKey('action.id'), primary_key=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='pending')
    notes = db.Column(db.Text, nullable=True)

    case = db.relationship('Case', back_populates='case_actions')
    action = db.relationship('Action', back_populates='case_actions')
    assigned_to = db.relationship('User', back_populates='case_actions_assigned')


class Lawyer(db.Model):
    """Lawyer information for referrals"""
    __tablename__ = 'lawyer'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    organization = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    
    # Must match Case.category values
    specialization = db.Column(db.String(50), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    referrals = db.relationship('Referral', back_populates='lawyer')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'organization': self.organization,
            'phone': self.phone,
            'email': self.email,
            'specialization': self.specialization,
            'referral_count': len(self.referrals)
        }


class Referral(db.Model):
    """Case referral to external lawyers"""
    __tablename__ = 'referral'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    lawyer_id = db.Column(db.Integer, db.ForeignKey('lawyer.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, sent, accepted, declined
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    case = db.relationship('Case', backref=db.backref('referrals', lazy=True))
    lawyer = db.relationship('Lawyer', back_populates='referrals')

    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'lawyer': self.lawyer.to_dict() if self.lawyer else None,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AIInsight(db.Model):
    """AI-generated insights for cases"""
    __tablename__ = 'ai_insight'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    insight_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)  # e.g., 'case_strategy', 'document_analysis', etc.
    confidence = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    case = db.relationship('Case', backref=db.backref('insights', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'insight_text': self.insight_text,
            'category': self.category,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Document(db.Model):
    """Document model for case-related files"""
    __tablename__ = 'document'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_id = db.Column(db.Integer, db.ForeignKey('action.id'), nullable=True)

    # Relationships
    case = db.relationship('Case', back_populates='documents')
    uploaded_by = db.relationship('User', back_populates='uploaded_documents')
    action = db.relationship('Action', back_populates='documents')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'uploaded_by': self.uploaded_by.to_dict() if self.uploaded_by else None,
            'action': self.action.to_dict() if self.action else None
        }


class CaseNote(db.Model):
    """Notes for a case"""
    __tablename__ = 'case_note'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    case = db.relationship('Case', back_populates='notes')
    created_by = db.relationship('User', back_populates='case_notes')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'is_private': self.is_private,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by.to_dict() if self.created_by else None
        }


class Transcript(db.Model):
    """Stored transcripts from STT providers"""
    __tablename__ = 'transcript'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)  # e.g., 'assemblyai'
    external_id = db.Column(db.String(128), nullable=False, index=True)  # provider transcript id
    status = db.Column(db.String(50), nullable=False, default='processing')
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationships
    client = db.relationship('Client', backref=db.backref('transcripts', lazy=True))
    case = db.relationship('Case', backref=db.backref('transcripts', lazy=True))
    user = db.relationship('User', backref=db.backref('transcripts', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider,
            'external_id': self.external_id,
            'status': self.status,
            'text': self.text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'client_id': self.client_id,
            'case_id': self.case_id,
            'user_id': self.user_id,
        }

# ==================== CLIENT PORTAL & BILLING MODELS ====================

class ClientUser(db.Model):
    """Separate authentication for client portal access"""
    __tablename__ = 'client_user'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Portal settings
    portal_access = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expires = db.Column(db.DateTime)
    
    # Activity tracking
    last_login = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    
    # Security
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = db.relationship('Client', backref=db.backref('portal_user', uselist=False))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_verification_token(self):
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token
    
    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
        return self.reset_token
    
    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def record_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def record_successful_login(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.utcnow()
        self.login_count += 1
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'portal_access': self.portal_access,
            'email_verified': self.email_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class ClientMessage(db.Model):
    """Secure messaging between client and attorney"""
    __tablename__ = 'client_message'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    
    # Sender/Receiver
    from_client = db.Column(db.Boolean, default=True)  # True if from client, False if from attorney
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    attorney_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Message content
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    
    # Status
    read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Threading
    parent_id = db.Column(db.Integer, db.ForeignKey('client_message.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    case = db.relationship('Case', backref='client_messages')
    client = db.relationship('Client', backref='messages_sent', foreign_keys=[client_id])
    attorney = db.relationship('User', backref='client_messages', foreign_keys=[attorney_id])
    replies = db.relationship('ClientMessage', backref=db.backref('parent', remote_side=[id]))
    
    def mark_as_read(self):
        self.read = True
        self.read_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'from_client': self.from_client,
            'subject': self.subject,
            'message': self.message,
            'read': self.read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ClientDocumentAccess(db.Model):
    """Track which documents clients can access"""
    __tablename__ = 'client_document_access'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    
    # Access control
    can_view = db.Column(db.Boolean, default=True)
    can_download = db.Column(db.Boolean, default=True)
    requires_signature = db.Column(db.Boolean, default=False)
    signed = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime)
    
    # Notifications
    client_notified = db.Column(db.Boolean, default=False)
    notification_sent_at = db.Column(db.DateTime)
    
    # Tracking
    view_count = db.Column(db.Integer, default=0)
    last_viewed = db.Column(db.DateTime)
    download_count = db.Column(db.Integer, default=0)
    last_downloaded = db.Column(db.DateTime)
    
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    granted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    document = db.relationship('Document', backref='client_access')
    client = db.relationship('Client', backref='document_access')
    granted_by = db.relationship('User', backref='granted_access')
    
    def record_view(self):
        self.view_count += 1
        self.last_viewed = datetime.utcnow()
    
    def record_download(self):
        self.download_count += 1
        self.last_downloaded = datetime.utcnow()


# ==================== BILLING MODELS ====================

class TimeEntry(db.Model):
    """Track billable time for cases"""
    __tablename__ = 'time_entry'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Time details
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    duration_minutes = db.Column(db.Integer, nullable=False)
    
    # Billing
    hourly_rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Calculated: (duration_minutes / 60) * hourly_rate
    billable = db.Column(db.Boolean, default=True)
    
    # Description
    description = db.Column(db.Text, nullable=False)
    activity_type = db.Column(db.String(50))  # research, court, phone, email, drafting, etc.
    
    # Status
    billed = db.Column(db.Boolean, default=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = db.relationship('Case', backref='time_entries')
    user = db.relationship('User', backref='time_entries')
    
    def calculate_amount(self):
        """Calculate the amount based on duration and hourly rate"""
        self.amount = (self.duration_minutes / 60.0) * self.hourly_rate
        return self.amount
    
    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'date': self.date.isoformat() if self.date else None,
            'duration_minutes': self.duration_minutes,
            'hourly_rate': self.hourly_rate,
            'amount': self.amount,
            'description': self.description,
            'activity_type': self.activity_type,
            'billable': self.billable,
            'billed': self.billed
        }


class Expense(db.Model):
    """Track case-related expenses"""
    __tablename__ = 'expense'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Expense details
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))  # filing_fees, travel, copies, expert_witness, etc.
    amount = db.Column(db.Float, nullable=False)
    
    # Reimbursement
    billable_to_client = db.Column(db.Boolean, default=True)
    reimbursable_to_attorney = db.Column(db.Boolean, default=False)
    
    # Status
    billed = db.Column(db.Boolean, default=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    reimbursed = db.Column(db.Boolean, default=False)
    
    # Documentation
    receipt_path = db.Column(db.String(500))
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    case = db.relationship('Case', backref='expenses')
    user = db.relationship('User', backref='expenses')
    
    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'category': self.category,
            'amount': self.amount,
            'billable_to_client': self.billable_to_client
        }


class Invoice(db.Model):
    """Client invoices"""
    __tablename__ = 'invoice'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    
    # Invoice details
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    
    # Amounts
    subtotal_time = db.Column(db.Float, default=0.0)
    subtotal_expenses = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0)
    tax_rate = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Payment tracking
    amount_paid = db.Column(db.Float, default=0.0)
    balance_due = db.Column(db.Float)
    
    # Status
    status = db.Column(db.String(50), default='draft')  # draft, sent, paid, partially_paid, overdue, cancelled
    
    # Notes
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    
    # PDF generation
    pdf_generated = db.Column(db.Boolean, default=False)
    pdf_path = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    
    # Relationships
    case = db.relationship('Case', backref='invoices')
    client = db.relationship('Client', backref='invoices')
    time_entries = db.relationship('TimeEntry', backref='invoice')
    expenses = db.relationship('Expense', backref='invoice')
    payments = db.relationship('Payment', back_populates='invoice')
    
    def calculate_totals(self):
        """Calculate invoice totals from time entries and expenses"""
        self.subtotal_time = sum(te.amount for te in self.time_entries if te.billable)
        self.subtotal_expenses = sum(e.amount for e in self.expenses if e.billable_to_client)
        self.subtotal = self.subtotal_time + self.subtotal_expenses
        self.tax_amount = self.subtotal * self.tax_rate
        self.total_amount = self.subtotal + self.tax_amount
        self.balance_due = self.total_amount - self.amount_paid
    
    def add_payment(self, amount):
        """Record a payment and update status"""
        self.amount_paid += amount
        self.balance_due = self.total_amount - self.amount_paid
        
        if self.balance_due <= 0:
            self.status = 'paid'
        elif self.amount_paid > 0:
            self.status = 'partially_paid'
    
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.status in ['paid', 'cancelled']:
            return False
        if self.due_date < datetime.utcnow().date():
            return True
        return False
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'case_id': self.case_id,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'total_amount': self.total_amount,
            'amount_paid': self.amount_paid,
            'balance_due': self.balance_due,
            'status': self.status,
            'is_overdue': self.is_overdue()
        }


class Payment(db.Model):
    """Payment records"""
    __tablename__ = 'payment'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    
    # Payment details
    payment_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))  # check, credit_card, bank_transfer, cash, online
    
    # Transaction info
    transaction_id = db.Column(db.String(100))
    reference_number = db.Column(db.String(100))
    
    # Card info (last 4 digits only)
    card_last_four = db.Column(db.String(4))
    
    # Status
    status = db.Column(db.String(50), default='completed')  # pending, completed, failed, refunded
    
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    invoice = db.relationship('Invoice', back_populates='payments')
    created_by = db.relationship('User', backref='recorded_payments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'status': self.status
        }


class TrustAccount(db.Model):
    """Client trust account transactions (IOLTA compliance)"""
    __tablename__ = 'trust_account'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'))
    
    # Transaction details
    transaction_date = db.Column(db.Date, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # deposit, withdrawal, transfer
    amount = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    
    # Description
    description = db.Column(db.Text, nullable=False)
    reference_number = db.Column(db.String(100))
    
    # Related invoice (if withdrawal is for payment)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    client = db.relationship('Client', backref='trust_transactions')
    case = db.relationship('Case', backref='trust_transactions')
    created_by = db.relationship('User', backref='trust_transactions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'balance_after': self.balance_after,
            'description': self.description
        }


class BillingRate(db.Model):
    """Hourly billing rates for different attorneys and case types"""
    __tablename__ = 'billing_rate'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Rate details
    rate_type = db.Column(db.String(50), default='standard')  # standard, contingency, flat_fee
    hourly_rate = db.Column(db.Float, nullable=False)
    
    # Optional: Different rates for different case types or activities
    case_type = db.Column(db.String(50))
    activity_type = db.Column(db.String(50))
    
    # Validity
    effective_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='billing_rates')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'hourly_rate': self.hourly_rate,
            'rate_type': self.rate_type,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None
        }


# ==================== CALENDAR & SCHEDULING ====================

class CalendarEvent(db.Model):
    """Calendar events linked to cases/clients with optional reminders"""
    __tablename__ = 'calendar_event'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=True)
    all_day = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(255))

    # Links
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Reminders
    reminder_minutes_before = db.Column(db.Integer, default=0)

    status = db.Column(db.String(50), default='scheduled')  # scheduled, completed, cancelled

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    case = db.relationship('Case', backref='calendar_events')
    client = db.relationship('Client', backref='calendar_events')
    created_by = db.relationship('User', backref='created_events')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_at': self.start_at.isoformat() if self.start_at else None,
            'end_at': self.end_at.isoformat() if self.end_at else None,
            'all_day': self.all_day,
            'location': self.location,
            'case_id': self.case_id,
            'client_id': self.client_id,
            'reminder_minutes_before': self.reminder_minutes_before,
            'status': self.status
        }


# ==================== INTEGRATIONS / OAUTH ====================

class OAuthAccount(db.Model):
    """Stores external provider connections (Google/Microsoft) for users."""
    __tablename__ = 'oauth_account'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # 'google' | 'microsoft'

    # Tokens (mock for now)
    access_token = db.Column(db.String(512))
    refresh_token = db.Column(db.String(512))
    expires_at = db.Column(db.DateTime)
    scopes = db.Column(db.Text)

    status = db.Column(db.String(20), default='connected')  # connected | revoked | error
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('oauth_accounts', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'provider': self.provider,
            'status': self.status,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None
        }
