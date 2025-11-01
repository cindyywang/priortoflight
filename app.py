from flask import Flask, render_template, request, jsonify, url_for, abort, current_app, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from config import Config
from sqlalchemy import text # (or your SQLAlchemy methods)
import re
import click
import sqlite3
import os


basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Define the DB path here:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

db = SQLAlchemy()


# Simple bot blacklist
BAD_BOTS = ["curl", "python", "scrapy", "spider", "bot"]

# 数据模型
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    description_en = db.Column(db.Text)
    items = db.relationship('Item', backref='category', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    name_en = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    description_en = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False)  # allowed, restricted, prohibited
    restrictions = db.Column(db.Text)
    restrictions_en = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    source = db.Column(db.String(500))
    last_updated = db.Column(db.DateTime, server_default=db.func.now())

# 工具函数：获取当前语言
def get_lang():
    return request.args.get("lang", "zh")

# Add this function to your app.py

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

# --- END of init_db_command() ---

def init_db():
    # This command creates all tables defined in your SQLAlchemy models (if you had models)
    # OR, for raw SQL schema:

    # You will need to execute the raw schema directly since you're not defining models yet
    # To do this safely with SQLAlchemy, we get the engine connection:
    engine = db.engine
    # 2. Use a context manager to open a connection
    with engine.connect() as connection:
        # 3. Read the schema file
        with current_app.open_resource('schema.sql') as f:
            sql_script = f.read().decode('utf8')
            # 💡 New Logic: Split the script into individual statements
            statements = [s.strip() for s in sql_script.split(';') if s.strip()]

            for statement in statements:
                # Execute each CREATE TABLE statement individually
                connection.exec_driver_sql(statement)

        # 5. Commit the changes to the database
        connection.commit()

def init_app(app):
    # Registers the 'init-db' command with the application
    app.cli.add_command(init_db_command)

# --- END of init_app() ---

# 2. Define the application factory function (standard Flask pattern)
def create_app(config_class=Config): # You may have this already, if not, create it
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 3. Initialize the db object here, INSIDE the function
    db.init_app(app)

    # 4. Define or register your database initialization command here
    init_app(app) # You defined this to register the command

    # ... other routes/blueprints ...

    return app

app = create_app()

# Limit each IP to 60 requests per minute
limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])

# 路由
@app.route('/')
def index():
    lang = get_lang()
    # 🌟 1. FIX: You must fetch the data for the homepage 🌟
    # This query fetches the 4 items you want to display
    popular_items = db.session.execute(
        text("SELECT * FROM Item WHERE id IN (27, 27, 29, 23)")
    ).mappings().fetchall()
    # 🌟 2. FIX: Pass 'popular_items' to the template 🌟
    return render_template(
        'index.html',
        lang=lang,
        popular_items=popular_items
    )

@app.route('/categories')
def categories():
    lang = get_lang()
    categories_list = db.session.execute(
        text("SELECT * FROM Category")
    ).mappings().fetchall()
    return render_template('all_categories.html', categories=categories_list, lang=lang)

@app.route('/category/<int:category_id>')
def category_page(category_id):
    lang = get_lang()
    # 1. Fetch the SINGLE category object
    category = db.session.execute(
        text("SELECT * FROM Category WHERE id = :id"),
        {"id": category_id}
    ).mappings().fetchone() # Use fetchone() for a single result

    # 2. Fetch the LIST of items for that category
    items_list = db.session.execute(
        text("SELECT * FROM Item WHERE :_id = :id"),
        {"id": category_id}
    ).mappings().fetchall() # Use fetchall() for multiple results

    # 3. 🌟 CRITICAL FIX: Pass BOTH 'category=category' AND 'items=items_list'
    return render_template(
        'categories.html',
        category=category,
        items=items_list,
        lang=lang
    )

@app.route('/item/<int:item_id>')
def item_detail(item_id):# <-- Note: function name matches url_for
    lang = get_lang()
    # 1. Fetch the SINGLE item from the database using item_id
    item = db.session.execute(
        text("SELECT * FROM Item WHERE id = :id"),
        {"id": item_id}
    ).mappings().fetchone() # Use fetchone() for a single item

    if item is None:
        # Handle cases where the item ID doesn't exist
        return "Item not found", 404

    # 2. Render the 'item.html' template (which you should have created)
    return render_template('item.html', item=item, lang=lang)

@app.route('/search')
def search():
    lang = get_lang()
    query = request.args.get('q', '').strip()
    items = []
    if query:
        # 🌟 Define search_term ONLY IF q EXISTS 🌟
        # Use LIKE with % wildcards for searching
        search_term = f'%{query}%'
        # Now run the database query
        items = db.session.execute(
            text("""
                SELECT * FROM Item
                WHERE name LIKE :term OR name_en LIKE :term COLLATE NOCASE
            """),
            {"term": search_term}
        ).mappings().fetchall()
    return render_template('search.html', items=items, query=query, lang=lang)

@app.route('/about')
def about():
    lang = get_lang()
    return render_template('about.html', lang=lang)

# API端点
@app.route('/api/items')
def api_items():
    lang = get_lang()
    items = Item.query.all()
    return jsonify([{
        'id': item.id,
        'name': item.name_en if lang == "en" else item.name,
        'status': item.status,
        'category': item.category.name_en if lang == "en" else item.category.name
    } for item in items])

@app.route('/api/item/<int:item_id>')
def api_item(item_id):
    lang = get_lang()
    item = Item.query.get_or_404(item_id)
    return jsonify({
        'id': item.id,
        'name': item.name_en if lang == "en" else item.name,
        'description': item.description_en if lang == "en" else item.description,
        'status': item.status,
        'restrictions': item.restrictions_en if lang == "en" else item.restrictions,
        'category': item.category.name_en if lang == "en" else item.category.name,
        'source': item.source,
        'last_updated': item.last_updated.isoformat()
    })

@app.before_request
def block_bots():
    ua = request.headers.get("User-Agent", "").lower()
    if any(b in ua for b in BAD_BOTS):
        abort(403)

# Optional JS challenge check
@app.before_request
def js_check():
    token = request.cookies.get("js_challenge")
    if not token and "text/html" in request.headers.get("Accept", ""):
        # serve a small JS snippet first
        return """
        <script>
        document.cookie = "js_challenge=1; path=/";
        location.reload();
        </script>
        """, 200, {"Content-Type": "text/html"}

@app.after_request
def log_requests(response):
    ip = request.remote_addr
    ua = request.headers.get("User-Agent", "")
    with open("access_log.txt", "a") as f:
        f.write(f"{ip}\t{ua}\n")
    return response

@app.route('/')
def home():
    return "Welcome to Prior to Flight!"

if __name__ == '__main__':
    app.run(debug=True)


