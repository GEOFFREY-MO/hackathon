# backend/database/__init__.py
from flask import Flask
from .models import db

def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_retail.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
