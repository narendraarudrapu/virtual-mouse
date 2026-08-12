# Web auth for AI Virtual Mouse

This small Flask app provides signup, login, a 10-day free trial, and basic subscription selection.

Quick start

1. Create and activate a Python virtualenv.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the app

```bash
python web/app.py
```

3. Open http://127.0.0.1:5000 in your browser.

Notes
- Payment processing is not implemented; subscription changes are stored in SQLite at `web/database.db`.
- Trial length is 10 days from signup. After expiry users are routed to the subscription page.
