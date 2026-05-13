import os
from tempfile import mkdtemp

from flask import Flask
from flask_session import Session
from werkzeug.exceptions import default_exceptions

from helpers import apology, usd
from models import db
from routes.auth import auth_bp
from routes.stocks import stocks_bp
from routes.options import options_bp

app = Flask(__name__)

secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not set")
app.config["SECRET_KEY"] = secret_key

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

app.register_blueprint(auth_bp)
app.register_blueprint(stocks_bp)
app.register_blueprint(options_bp)

with app.app_context():
    db.create_all()


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def errorhandler(e):
    return apology(e.name, e.code)


for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
