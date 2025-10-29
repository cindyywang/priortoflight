# run_init_db.py

import os
import sys

# Add your project directory to the path so it can find 'app'
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Assuming your main application factory or instance is named 'app'
# and is defined in app.py
from app import app, init_db

# Context is needed for the database functions to work
with app.app_context():
    print("Starting database initialization...")
    init_db()
    print("Database successfully initialized from schema.sql!")
