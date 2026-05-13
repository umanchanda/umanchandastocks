# coding=utf8
import csv
import os
import urllib.request

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
    if symbol.startswith("^") or "," in symbol:
        return None

    # Try Yahoo Finance first
    try:
        url = f"http://download.finance.yahoo.com/d/quotes.csv?f=snl1&s={symbol}"
        webpage = urllib.request.urlopen(url, timeout=5)
        row = next(csv.reader(webpage.read().decode("utf-8").splitlines()))
        return {"name": row[1], "price": float(row[2]), "symbol": row[0].upper()}
    except (ValueError, IndexError, StopIteration):
        return None
    except Exception:
        pass

    # Fall back to Alpha Vantage
    try:
        api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        url = (f"https://www.alphavantage.co/query?apikey={api_key}"
               f"&datatype=csv&function=TIME_SERIES_INTRADAY&interval=1min&symbol={symbol}")
        webpage = urllib.request.urlopen(url, timeout=5)
        reader = csv.reader(webpage.read().decode("utf-8").splitlines())
        next(reader)  # skip header
        row = next(reader)
        return {"name": symbol, "price": float(row[4]), "symbol": symbol}
    except (ValueError, IndexError, StopIteration):
        return None
    except Exception:
        return None


def usd(value):
    """Format a value as USD."""
    return f"${value:,.2f}"
