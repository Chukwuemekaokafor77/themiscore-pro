from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from dotenv import load_dotenv

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app(config_class=None):
    # Create and configure the app
    app = Flask(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Configure database URI
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Default configuration
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key-change-in-production'),
        SQLALCHEMY_DATABASE_URI=DATABASE_URL or 'sqlite:///legalintake.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'),
        MAX_CONTENT_LENGTH=int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)),  # 16MB default
        PERMANENT_SESSION_LIFETIME=3600  # 1 hour in seconds
    )
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Register blueprints and routes
    from . import routes
    app.register_blueprint(routes.bp)
    
    # Register error handlers
    from .errors import bp as errors_bp
    app.register_blueprint(errors_bp)
    
    # Register filters
    from .filters import init_app
    init_app(app)
    
    return app
