from flask import Flask, render_template, request, jsonify, url_for, abort, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from config import Config
import re
import click

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# Limit each IP to 60 requests per minute
limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])

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

def init_db():
    db = get_db()

    # Opens and reads the schema.sql file
    with current_app.open_resource('schema.sql') as f:
        # Executes the SQL commands to create the tables
        db.executescript(f.read().decode('utf8'))

# --- END of init_db() ---

# Add this function to your app.py

def init_app(app):
    # Closes the database connection after the app context ends
    app.teardown_appcontext(close_db)

    # Registers the 'init-db' command with the application
    app.cli.add_command(init_db_command)

# --- END of init_app() ---

# 路由
@app.route('/')
def index():
    lang = get_lang()
    return render_template('index.html', lang=lang)

@app.route('/categories')
def categories():
    lang = get_lang()
    categories_list = Category.query.all()
    return render_template('categories.html', categories=categories_list, lang=lang)

@app.route('/category/<int:category_id>')
def category_items(category_id):
    lang = get_lang()
    category = Category.query.get_or_404(category_id)
    items = Item.query.filter_by(category_id=category_id).all()
    return render_template('category_items.html', category=category, items=items, lang=lang)

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    lang = get_lang()
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item, lang=lang)

@app.route('/search')
def search():
    lang = get_lang()
    query = request.args.get('q', '')
    if query:
        items = Item.query.filter(
            (Item.name.contains(query)) | (Item.name_en.contains(query)) |
            (Item.description.contains(query)) | (Item.description_en.contains(query))
        ).all()
    else:
        items = []
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

# Add this function to your app.py

import click
from flask import current_app
# ... (ensure these imports are at the top)

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

# --- END of init_db_command() ---

if __name__ == '__main__':
    init_app(app)
    app.run(debug=True)


