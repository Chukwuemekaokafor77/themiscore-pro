from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy
db = SQLAlchemy()

# Association table for many-to-many relationship between cases and actions
case_actions = db.Table('case_actions',
    db.Column('case_id', db.Integer, db.ForeignKey('case.id'), primary_key=True),
    db.Column('action_id', db.Integer, db.ForeignKey('action.id'), primary_key=True),
    db.Column('assigned_to_id', db.Integer, db.ForeignKey('user.id'), nullable=True),
    db.Column('due_date', db.DateTime, nullable=True),
    db.Column('status', db.String(50), default='pending'),
    db.Column('notes', db.Text, nullable=True)
)

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
    assigned_cases = db.relationship('Case', 
                                   foreign_keys='Case.assigned_to_id', 
                                   back_populates='assigned_user',
                                   lazy=True)
    created_cases = db.relationship('Case', 
                                  foreign_keys='Case.created_by_id', 
                                  back_populates='creator',
                                  lazy=True)
    created_actions = db.relationship('Action',
                                    foreign_keys='Action.created_by_id',
                                    back_populates='created_by',
                                    lazy=True)
    assigned_actions = db.relationship('Action',
                                     foreign_keys='Action.assigned_to_id',
                                     back_populates='assigned_to',
                                     lazy=True)
    uploaded_documents = db.relationship('Document',
                                       foreign_keys='Document.uploaded_by_id',
                                       back_populates='uploaded_by',
                                       lazy=True)
    case_notes = db.relationship('CaseNote',
                               foreign_keys='CaseNote.created_by_id',
                               back_populates='created_by',
                               lazy=True)
    
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
    case_type = db.Column(db.String(100))  # e.g., 'slip_and_fall', 'car_accident'
    status = db.Column(db.String(50), default='open')  # 'open', 'in_progress', 'closed', 'on_hold'
    priority = db.Column(db.String(20), default='medium')  # 'low', 'medium', 'high', 'urgent'
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
    actions = db.relationship('Action', 
                             secondary=case_actions, 
                             lazy='subquery',
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
            'assigned_to': self.assigned_to.to_dict() if self.assigned_to else None,
            'document_count': len(self.documents),
            'note_count': len(self.notes)
        }

class Action(db.Model):
    """Action items model"""
    __tablename__ = 'action'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    action_type = db.Column(db.String(100), nullable=True)  # e.g., 'document_review', 'court_filing', 'client_meeting'
    status = db.Column(db.String(50), default='pending')  # 'pending', 'in_progress', 'completed', 'cancelled'
    priority = db.Column(db.String(20), default='medium')  # 'low', 'medium', 'high', 'urgent'
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
    cases = db.relationship('Case', 
                           secondary=case_actions, 
                           back_populates='actions',
                           viewonly=True)
    
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

class Document(db.Model):
    """Document model for case-related files"""
    __tablename__ = 'document'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # in bytes
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
