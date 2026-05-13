from datetime import date

import yfinance as yf
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session

from helpers import login_required
from models import db, User, OptionPosition, OptionTransaction

options_bp = Blueprint("options", __name__, url_prefix="/options")


def _get_option_price(symbol, expiration, option_type, strike):
    """Fetch the current market price for an option. Returns None on failure."""
    try:
        chain = yf.Ticker(symbol).option_chain(expiration)
        df = chain.calls if option_type == "call" else chain.puts
        row = df[df["strike"] == float(strike)]
        if row.empty:
            return None
        last = float(row.iloc[0]["lastPrice"])
        bid = float(row.iloc[0]["bid"])
        ask = float(row.iloc[0]["ask"])
        return round(last if last > 0 else (bid + ask) / 2, 4)
    except Exception:
        return None


@options_bp.route("/")
@login_required
def portfolio():
    positions = OptionPosition.query.filter_by(user_id=session["user_id"]).all()
    transactions = OptionTransaction.query.filter_by(user_id=session["user_id"]).all()
    return render_template("options/portfolio.html", positions=positions,
                           transactions=transactions)


@options_bp.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        expiration = request.form.get("expiration", "").strip()
        option_type = request.form.get("option_type", "").strip().lower()

        if not symbol or not expiration or option_type not in ("call", "put"):
            flash("Invalid option parameters", "error")
            return redirect("/options/buy")

        try:
            strike = float(request.form.get("strike"))
            contracts = int(request.form.get("contracts"))
            if contracts <= 0:
                flash("Contracts must be a positive number", "error")
                return redirect("/options/buy")
        except (ValueError, TypeError):
            flash("Invalid strike or contract count", "error")
            return redirect("/options/buy")

        premium = _get_option_price(symbol, expiration, option_type, strike)
        if premium is None:
            flash("Could not fetch current option price — try again", "error")
            return redirect("/options/buy")

        total_cost = premium * contracts * 100
        user = db.session.get(User, session["user_id"])

        if float(user.cash) < total_cost:
            flash("Insufficient funds", "error")
            return redirect("/options/buy")

        user.cash = float(user.cash) - total_cost

        exp_date = date.fromisoformat(expiration)
        position = OptionPosition.query.filter_by(
            user_id=user.id, symbol=symbol, option_type=option_type,
            strike=strike, expiration=exp_date
        ).first()

        if position:
            position.contracts += contracts
            position.total_cost = float(position.total_cost) + total_cost
        else:
            db.session.add(OptionPosition(
                user_id=user.id, symbol=symbol, option_type=option_type,
                strike=strike, expiration=exp_date,
                contracts=contracts, premium=premium, total_cost=total_cost
            ))

        db.session.add(OptionTransaction(
            user_id=user.id, symbol=symbol, option_type=option_type,
            strike=strike, expiration=exp_date,
            contracts=contracts, premium=premium
        ))
        db.session.commit()
        flash(f"Bought {contracts} {symbol} {option_type} contract(s)", "success")
        return redirect("/")

    return render_template("options/buy.html")


@options_bp.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user = db.session.get(User, session["user_id"])
    positions = OptionPosition.query.filter_by(user_id=user.id).all()

    if request.method == "POST":
        try:
            position_id = int(request.form.get("position_id"))
            contracts = int(request.form.get("contracts"))
        except (ValueError, TypeError):
            flash("Invalid input", "error")
            return redirect("/options/sell")

        position = db.session.get(OptionPosition, position_id)

        if not position or position.user_id != user.id:
            flash("Position not found", "error")
            return redirect("/options/sell")
        if contracts <= 0 or contracts > position.contracts:
            flash("Invalid number of contracts", "error")
            return redirect("/options/sell")

        exp_str = position.expiration.strftime("%Y-%m-%d")
        premium = _get_option_price(position.symbol, exp_str,
                                    position.option_type, float(position.strike))
        if premium is None:
            flash("Could not fetch current option price — try again", "error")
            return redirect("/options/sell")

        proceeds = premium * contracts * 100
        user.cash = float(user.cash) + proceeds

        db.session.add(OptionTransaction(
            user_id=user.id, symbol=position.symbol, option_type=position.option_type,
            strike=float(position.strike), expiration=position.expiration,
            contracts=-contracts, premium=premium
        ))

        if contracts == position.contracts:
            db.session.delete(position)
        else:
            position.contracts -= contracts

        db.session.commit()
        flash(f"Sold {contracts} contract(s) for ${proceeds:,.2f}", "success")
        return redirect("/")

    return render_template("options/sell.html", positions=positions)


@options_bp.route("/chain/<symbol>")
@login_required
def chain_expirations(symbol):
    try:
        expirations = list(yf.Ticker(symbol.upper()).options)
        return jsonify({"expirations": expirations})
    except Exception:
        return jsonify({"error": "Could not fetch options chain"}), 400


@options_bp.route("/chain/<symbol>/<expiration>")
@login_required
def chain_data(symbol, expiration):
    try:
        chain = yf.Ticker(symbol.upper()).option_chain(expiration)
        cols = ["strike", "lastPrice", "bid", "ask", "volume",
                "openInterest", "impliedVolatility"]

        def to_records(df):
            return [{c: float(row[c]) if c != "strike" else float(row[c])
                     for c in cols} for _, row in df[cols].fillna(0).iterrows()]

        return jsonify({"calls": to_records(chain.calls),
                        "puts": to_records(chain.puts)})
    except Exception:
        return jsonify({"error": "Could not fetch chain data"}), 400
