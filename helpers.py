# coding=utf8
import csv
import os
import urllib.request

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Renders message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # reject symbol if it starts with caret
    if symbol.startswith("^"):
        return None

    # Reject symbol if it contains comma
    if "," in symbol:
        return None

    # Query Yahoo for quote
    # http://stackoverflow.com/a/21351911
    try:
        url = f"http://download.finance.yahoo.com/d/quotes.csv?f=snl1&s={symbol}"
        webpage = urllib.request.urlopen(url, timeout=5)
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())
        row = next(datareader)
        try:
            price = float(row[2])
        except (ValueError, IndexError):
            return None
        return {
            "name": row[1],
            "price": price,
            "symbol": row[0].upper()
        }
    except Exception:
        pass

    # Query Alpha Vantage for quote instead
    # https://www.alphavantage.co/documentation/
    try:
        api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        url = f"https://www.alphavantage.co/query?apikey={api_key}&datatype=csv&function=TIME_SERIES_INTRADAY&interval=1min&symbol={symbol}"
        webpage = urllib.request.urlopen(url, timeout=5)
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())
        next(datareader)
        row = next(datareader)
        try:
            price = float(row[4])
        except (ValueError, IndexError):
            return None
        return {
            "name": symbol.upper(),
            "price": price,
            "symbol": symbol.upper()
        }
    except Exception:
        return None


def usd(value):
    """Formats value as USD."""
    return f"${value:,.2f}"
