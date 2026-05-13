# coding=utf8
import yfinance as yf

from flask import redirect, render_template, session
from functools import wraps


def apology(message, code=400):
    """Render an error message to the user."""
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """Redirect to login if the user is not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Return current price data for a stock symbol, or None if not found."""
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.last_price
        if not price:
            return None
        return {"name": symbol.upper(), "price": round(price, 2), "symbol": symbol.upper()}
    except Exception:
        return None


def usd(value):
    """Format a value as USD."""
    return f"${value:,.2f}"
