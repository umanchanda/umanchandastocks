# umanchandastocks

A paper trading application for stocks and options, built with Flask and PostgreSQL.

## Features

- **Stocks**: Buy and sell stocks with real-time pricing via yfinance. Supports both share-count and dollar-amount orders, including fractional shares.
- **Options**: Buy and sell call/put options with an AJAX-driven chain browser (expirations, strikes, live bid/ask). Positions and transaction history tracked separately.
- **Portfolio**: Dashboard showing stock holdings, open options positions, and available cash.
- **History**: Full transaction log for stock trades.

## Running locally

1. Clone the repository:
   ```bash
   git clone https://github.com/umanchanda/umanchandastocks.git
   cd umanchandastocks
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set required environment variables:
   ```bash
   export SECRET_KEY="your-secret-key-here"
   export DATABASE_URL="sqlite:///finance.db"   # or a PostgreSQL URL

   # Optional — required for password reset emails
   export MAIL_SERVER="smtp.gmail.com"
   export MAIL_PORT="587"
   export MAIL_USE_TLS="true"
   export MAIL_USERNAME="you@example.com"
   export MAIL_PASSWORD="your-app-password"
   export MAIL_DEFAULT_SENDER="you@example.com"
   ```

4. Run the app:
   ```bash
   python application.py
   ```

5. Open `http://127.0.0.1:8000` in your browser.

## Deployment

The app is deployed on Heroku at [umanchandastocks.herokuapp.com](https://umanchandastocks.herokuapp.com).

Set the following config vars in Heroku:
- `SECRET_KEY` — a long random string
- `DATABASE_URL` — provided automatically by a Postgres add-on
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` — SMTP credentials for password reset emails (e.g. SendGrid or Gmail)

## Project structure

```
application.py        # App factory: config, blueprint registration, error handler
models.py             # SQLAlchemy models (User, Portfolio, Transaction, OptionPosition, OptionTransaction)
helpers.py            # login_required decorator, stock lookup, USD formatter
routes/
  auth.py             # /register, /login, /logout
  stocks.py           # /, /buy, /sell, /quote, /history
  options.py          # /options/, /options/buy, /options/sell, /options/chain/...
templates/
  layout.html         # Base template with navbar and flash messages
  options/            # Options-specific templates
static/               # CSS
```
