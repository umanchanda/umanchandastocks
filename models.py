from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    hash = db.Column(db.String(256), nullable=False)
    cash = db.Column(db.Numeric(12, 2), nullable=False, default=10000.00)

    holdings = db.relationship("Portfolio", backref="user", lazy=True)
    transactions = db.relationship("Transaction", backref="user", lazy=True)


class Portfolio(db.Model):
    __tablename__ = "portfolio"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Numeric(12, 4), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    total = db.Column(db.Numeric(12, 2), nullable=False)


class Transaction(db.Model):
    __tablename__ = "histories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Numeric(12, 4), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    datetime = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
