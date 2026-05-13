from flask import Blueprint, flash, redirect, render_template, request, session

from helpers import login_required, lookup
from models import db, User, Portfolio, Transaction, OptionPosition

stocks_bp = Blueprint("stocks", __name__)


@stocks_bp.route("/")
@login_required
def index():
    user = db.session.get(User, session["user_id"])
    holdings = Portfolio.query.filter_by(user_id=user.id).all()
    option_positions = OptionPosition.query.filter_by(user_id=user.id).all()
    stocks_value = sum(float(h.total) for h in holdings)
    total = float(user.cash) + stocks_value
    return render_template("index.html", holdings=holdings, cash=user.cash,
                           total=total, option_positions=option_positions)


@stocks_bp.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        if not symbol:
            flash("Must provide a stock symbol", "error")
            return redirect("/buy")

        stock = lookup(symbol)
        if not stock:
            flash("Stock not found", "error")
            return redirect("/buy")

        mode = request.form.get("mode", "shares")
        try:
            if mode == "dollars":
                dollars = float(request.form.get("dollars"))
                if dollars <= 0:
                    flash("Amount must be a positive number", "error")
                    return redirect("/buy")
                shares = dollars / stock["price"]
            else:
                shares = float(request.form.get("shares"))
                if shares <= 0:
                    flash("Shares must be a positive number", "error")
                    return redirect("/buy")
        except (ValueError, TypeError):
            flash("Invalid amount", "error")
            return redirect("/buy")

        user = db.session.get(User, session["user_id"])
        cost = shares * stock["price"]

        if float(user.cash) < cost:
            flash("Insufficient funds", "error")
            return redirect("/buy")

        user.cash = float(user.cash) - cost

        holding = Portfolio.query.filter_by(user_id=user.id, symbol=symbol).first()
        if holding:
            holding.shares = float(holding.shares) + shares
            holding.total = holding.shares * stock["price"]
        else:
            db.session.add(Portfolio(user_id=user.id, symbol=symbol,
                                     shares=shares, price=stock["price"], total=cost))

        db.session.add(Transaction(user_id=user.id, symbol=symbol,
                                   shares=shares, price=stock["price"]))
        db.session.commit()
        return redirect("/")

    return render_template("buy.html")


@stocks_bp.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user = db.session.get(User, session["user_id"])
    holdings = Portfolio.query.filter_by(user_id=user.id).all()

    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        if not symbol:
            flash("Must provide a stock symbol", "error")
            return redirect("/sell")

        stock = lookup(symbol)
        if not stock:
            flash("Invalid stock", "error")
            return redirect("/sell")

        holding = Portfolio.query.filter_by(user_id=user.id, symbol=symbol).first()
        if not holding:
            flash("You don't own that stock", "error")
            return redirect("/sell")

        try:
            shares = float(request.form.get("shares"))
            if shares <= 0:
                flash("Shares must be a positive number", "error")
                return redirect("/sell")
            if shares > float(holding.shares):
                flash("Not enough shares", "error")
                return redirect("/sell")
        except (ValueError, TypeError):
            flash("Invalid number of shares", "error")
            return redirect("/sell")

        user.cash = float(user.cash) + shares * stock["price"]

        new_shares = float(holding.shares) - shares
        if new_shares < 0.0001:
            db.session.delete(holding)
        else:
            holding.shares = new_shares
            holding.total = new_shares * stock["price"]

        db.session.add(Transaction(user_id=user.id, symbol=symbol,
                                   shares=-shares, price=stock["price"]))
        db.session.commit()
        return redirect("/")

    return render_template("sell.html", holdings=holdings)


@stocks_bp.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        if not symbol:
            flash("Must provide a stock symbol", "error")
            return redirect("/quote")
        stock = lookup(symbol)
        if not stock:
            flash("Stock not found", "error")
            return redirect("/quote")
        return render_template("quoted.html", stock=stock)
    return render_template("quote.html")


@stocks_bp.route("/history")
@login_required
def history():
    transactions = Transaction.query.filter_by(user_id=session["user_id"]).all()
    return render_template("history.html", transactions=transactions)
