from app import app, db
from models import *  # Import all models for Flask-Migrate

if __name__ == '__main__':
    app.run(debug=True)
