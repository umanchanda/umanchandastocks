# coding=utf8
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import os
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database, or a DATABASE_URL env var for production
db = SQL(os.environ.get("DATABASE_URL", "sqlite:///finance.db"))


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    stocks = db.execute("SELECT * FROM portfolio WHERE id=:id", id=session['user_id'])
    cash_db = db.execute("SELECT cash FROM users WHERE id=:id", id=session['user_id'])

    cash = cash_db[0]['cash']

    stocks_value = sum(float(stock['total']) for stock in stocks)
    total = cash + stocks_value

    cash = '{0:.2f}'.format(cash)
    total = '{0:.2f}'.format(total)

    return render_template("index.html", stocks=stocks, total=total, cash=cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Must provide a stock symbol", 400)
        stock = lookup(symbol.upper())
        if not stock:
            return apology("Stock not found", 400)

        try:
            shares_bought = int(request.form.get("shares"))
            if shares_bought <= 0:
                return apology("Shares must be a positive number", 400)
        except (ValueError, TypeError):
            return apology("Invalid number of shares", 400)

        money = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
        money_available = money[0]["cash"]
        stock_price = stock["price"]

        money_left = money_available - shares_bought * stock_price

        if money_left < 0:
            return apology("Invalid Funds", 400)

        db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=money_left, id=session["user_id"])
        db.execute("INSERT INTO histories (id, symbol, shares, price) VALUES (:id, :symbol, :shares, :price)",
                    id=session["user_id"], symbol=stock["symbol"], shares=shares_bought, price=stock_price)

        num_shares = db.execute("SELECT shares FROM portfolio WHERE id=:id AND symbol=:symbol",
                                id=session["user_id"], symbol=stock["symbol"])

        if not num_shares:
            portfolio = db.execute("INSERT INTO portfolio (id, symbol, shares, price, total) VALUES (:id, :symbol, :shares, :price, :total)",
                                    id=session["user_id"], symbol=stock["symbol"], shares=shares_bought, price=stock_price, total=shares_bought * stock_price)
        else:
            new_shares = str(int(num_shares[0]["shares"]) + shares_bought)
            updated_total = int(new_shares) * stock_price
            db.execute("UPDATE portfolio SET shares=:shares, total=:total WHERE id=:id AND symbol=:symbol",
                        shares=new_shares, total=updated_total, id=session["user_id"], symbol=stock["symbol"])

        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    histories = db.execute("SELECT * FROM histories WHERE id=:id", id=session["user_id"])

    return render_template("history.html", histories=histories)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Must provide a stock symbol", 400)
        stock = lookup(symbol.upper())
        if not stock:
            return apology("Stock not found", 400)

        return render_template("quoted.html", stock=stock)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # forget any user id
    session.clear()

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password meets minimum length
        elif len(request.form.get("password")) < 8:
            return apology("password must be at least 8 characters", 400)

        # Ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        hashed_passwd = generate_password_hash(request.form.get("password"))

        check_username = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if len(check_username) != 0:
            return apology("username already exists", 400)

        insert = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                            username=request.form.get("username"), hash=hashed_passwd)

        session["user_id"] = insert

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    portfolio = db.execute("SELECT * FROM portfolio WHERE id=:id", id=session['user_id'])

    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Must provide a stock symbol", 400)
        stock = lookup(symbol.upper())
        if not stock:
            return apology("invalid stock", 400)
        stock_price = stock["price"]

        stuff = db.execute("SELECT shares,price,total FROM portfolio WHERE id=:id AND symbol=:symbol",
                            id=session['user_id'], symbol=stock['symbol'])
        curr_shares = int(stuff[0]['shares'])
        cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session['user_id'])
        cash = cash[0]['cash']

        try:
            shares_sold = int(request.form.get("shares"))
            if shares_sold <= 0:
                return apology("Shares must be a positive number", 400)
            elif curr_shares < shares_sold:
                return apology("Do not have enough shares", 400)
        except (ValueError, TypeError):
            return apology("Invalid number of shares", 400)

        db.execute("INSERT INTO histories (id, symbol, shares, price) VALUES (:id, :symbol, :shares, :price)",
                    id=session["user_id"], symbol=stock["symbol"], shares=-shares_sold, price=stock_price)

        new_total = float(cash) + shares_sold * float(stock_price)
        db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=new_total, id=session['user_id'])

        new_shares = curr_shares-shares_sold
        if new_shares > 0:
            db.execute("UPDATE portfolio SET shares=:shares WHERE id=:id AND symbol=:symbol",
                        shares=new_shares, id=session['user_id'], symbol=stock['symbol'])
        else:
            db.execute("DELETE FROM portfolio WHERE id=:id AND symbol=:symbol", id=session['user_id'], symbol=stock['symbol'])

        return redirect("/")
    else:
        return render_template("sell.html", stocks=portfolio)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
