# coding=utf8
import os
from tempfile import mkdtemp

from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
from models import db, User, Portfolio, Transaction

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24))

# psycopg2 does not support the channel_binding parameter; strip it if present
_db_url = os.environ.get("DATABASE_URL", "sqlite:///finance.db")
if "channel_binding" in _db_url:
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    _parsed = urlparse(_db_url)
    _params = {k: v[0] for k, v in parse_qs(_parsed.query).items() if k != "channel_binding"}
    _db_url = urlunparse(_parsed._replace(query=urlencode(_params)))

app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

db.init_app(app)
Session(app)
app.jinja_env.filters["usd"] = usd

with app.app_context():
    db.create_all()


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.route("/")
@login_required
def index():
    user = User.query.get(session["user_id"])
    holdings = Portfolio.query.filter_by(user_id=user.id).all()
    stocks_value = sum(float(h.total) for h in holdings)
    total = float(user.cash) + stocks_value
    return render_template("index.html", holdings=holdings, cash=user.cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        if not symbol:
            return apology("Must provide a stock symbol", 400)

        stock = lookup(symbol)
        if not stock:
            return apology("Stock not found", 400)

        try:
            shares = int(request.form.get("shares"))
            if shares <= 0:
                return apology("Shares must be a positive number", 400)
        except (ValueError, TypeError):
            return apology("Invalid number of shares", 400)

        user = User.query.get(session["user_id"])
        cost = shares * stock["price"]

        if float(user.cash) < cost:
            return apology("Insufficient funds", 400)

        user.cash = float(user.cash) - cost

        holding = Portfolio.query.filter_by(user_id=user.id, symbol=symbol).first()
        if holding:
            holding.shares += shares
            holding.total = holding.shares * stock["price"]
        else:
            db.session.add(Portfolio(user_id=user.id, symbol=symbol,
                                     shares=shares, price=stock["price"], total=cost))

        db.session.add(Transaction(user_id=user.id, symbol=symbol,
                                   shares=shares, price=stock["price"]))
        db.session.commit()
        return redirect("/")

    return render_template("buy.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user = User.query.get(session["user_id"])
    holdings = Portfolio.query.filter_by(user_id=user.id).all()

    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        if not symbol:
            return apology("Must provide a stock symbol", 400)

        stock = lookup(symbol)
        if not stock:
            return apology("Invalid stock", 400)

        holding = Portfolio.query.filter_by(user_id=user.id, symbol=symbol).first()
        if not holding:
            return apology("You don't own that stock", 400)

        try:
            shares = int(request.form.get("shares"))
            if shares <= 0:
                return apology("Shares must be a positive number", 400)
            if shares > holding.shares:
                return apology("Not enough shares", 400)
        except (ValueError, TypeError):
            return apology("Invalid number of shares", 400)

        user.cash = float(user.cash) + shares * stock["price"]

        if shares == holding.shares:
            db.session.delete(holding)
        else:
            holding.shares -= shares
            holding.total = holding.shares * stock["price"]

        db.session.add(Transaction(user_id=user.id, symbol=symbol,
                                   shares=-shares, price=stock["price"]))
        db.session.commit()
        return redirect("/")

    return render_template("sell.html", holdings=holdings)


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        if not symbol:
            return apology("Must provide a stock symbol", 400)
        stock = lookup(symbol)
        if not stock:
            return apology("Stock not found", 400)
        return render_template("quoted.html", stock=stock)
    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username:
            return apology("Must provide username", 400)
        if not password:
            return apology("Must provide password", 400)
        if len(password) < 8:
            return apology("Password must be at least 8 characters", 400)
        if password != confirmation:
            return apology("Passwords do not match", 400)
        if User.query.filter_by(username=username).first():
            return apology("Username already taken", 400)

        user = User(username=username, hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username:
            return apology("Must provide username", 403)
        if not password:
            return apology("Must provide password", 403)

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.hash, password):
            return apology("Invalid username or password", 403)

        session["user_id"] = user.id
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/history")
@login_required
def history():
    transactions = Transaction.query.filter_by(user_id=session["user_id"]).all()
    return render_template("history.html", transactions=transactions)


def errorhandler(e):
    return apology(e.name, e.code)


for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
