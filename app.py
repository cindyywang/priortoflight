from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

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

# 路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/categories')
def categories():
    categories_list = Category.query.all()
    return render_template('categories.html', categories=categories_list)

@app.route('/category/<int:category_id>')
def category_items(category_id):
    category = Category.query.get_or_404(category_id)
    items = Item.query.filter_by(category_id=category_id).all()
    return render_template('category_items.html', category=category, items=items)

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        # 简单搜索实现 - 实际项目中可能需要更复杂的搜索逻辑
        items = Item.query.filter(
            (Item.name.contains(query)) | (Item.name_en.contains(query)) |
            (Item.description.contains(query)) | (Item.description_en.contains(query))
        ).all()
    else:
        items = []
    return render_template('search.html', items=items, query=query)

@app.route('/about')
def about():
    return render_template('about.html')

# API端点
@app.route('/api/items')
def api_items():
    items = Item.query.all()
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'name_en': item.name_en,
        'status': item.status,
        'category': item.category.name_en
    } for item in items])

@app.route('/api/item/<int:item_id>')
def api_item(item_id):
    item = Item.query.get_or_404(item_id)
    return jsonify({
        'id': item.id,
        'name': item.name,
        'name_en': item.name_en,
        'description': item.description,
        'description_en': item.description_en,
        'status': item.status,
        'restrictions': item.restrictions,
        'restrictions_en': item.restrictions_en,
        'category': item.category.name_en,
        'source': item.source,
        'last_updated': item.last_updated.isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True)
