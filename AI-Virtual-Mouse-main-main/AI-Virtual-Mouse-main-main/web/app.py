from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import subprocess
import sys
from flask import send_file, abort
from authlib.integrations.flask_client import OAuth
import secrets
from dotenv import load_dotenv
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
SESSION_FILE = os.path.join(BASE_DIR, 'session.json')
# Default background video path - update or override via BG_VIDEO env var if needed
BG_VIDEO_PATH = os.environ.get('BG_VIDEO') or r"c:\Users\KANTI VARUN VENKAT\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions\9E7D93CC39851C783396A51A89CCBFB3C5CE7A59\transfers\2026-14\WhatsApp Video 2026-04-06 at 11.42.47 PM.mp4"

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-change-me')

# Load .env for local development (optional)
load_dotenv()

# Basic startup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# show whether OAuth config is present (masked)
def mask(s):
    if not s:
        return None
    s = str(s)
    if len(s) <= 8:
        return s[:1] + '***'
    return s[:4] + '...' + s[-4:]

logger.info('GOOGLE_CLIENT_ID=%s', mask(os.environ.get('GOOGLE_CLIENT_ID')))
logger.info('MICROSOFT_CLIENT_ID=%s', mask(os.environ.get('MICROSOFT_CLIENT_ID')))

# OAuth setup (requires environment variables)
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

oauth.register(
    name='microsoft',
    client_id=os.environ.get('MICROSOFT_CLIENT_ID'),
    client_secret=os.environ.get('MICROSOFT_CLIENT_SECRET'),
    server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile User.Read'},
)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.execute(
        '''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            subscription_plan TEXT NOT NULL,
            subscription_start TEXT,
            subscription_active INTEGER NOT NULL
        )''')
    db.commit()
    # ensure subscription_price column exists (add if missing)
    try:
        db.execute('ALTER TABLE users ADD COLUMN subscription_price REAL DEFAULT 0')
        db.commit()
    except Exception:
        # column probably exists already; ignore
        pass


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def find_user_by_email(email):
    db = get_db()
    cur = db.execute('SELECT * FROM users WHERE email = ?', (email,))
    return cur.fetchone()


def create_user_for_oauth(email):
    db = get_db()
    # create a user with a random password hash
    pw_hash = generate_password_hash(secrets.token_urlsafe(24))
    now = datetime.utcnow().isoformat()
    try:
        db.execute('INSERT INTO users (email, password_hash, created_at, subscription_plan, subscription_start, subscription_active, subscription_price) VALUES (?,?,?,?,?,?,?)',
                   (email, pw_hash, now, 'trial', now, 1, 0.0))
        db.commit()
    except Exception:
        pass
    cur = db.execute('SELECT * FROM users WHERE email = ?', (email,))
    return cur.fetchone()


def write_session_file(user_row):
    try:
        import json
        data = {
            'id': user_row['id'],
            'email': user_row['email'],
            'subscription_plan': user_row['subscription_plan'],
            'subscription_active': int(user_row['subscription_active']),
            'subscription_price': float(user_row['subscription_price']) if 'subscription_price' in user_row.keys() and user_row['subscription_price'] is not None else 0.0,
            'created_at': user_row['created_at']
        }
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass


def clear_session_file():
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        pass


def start_ai_mouse():
    """Start the AI virtual mouse script in a new process (detached console on Windows)."""
    try:
        python = sys.executable or 'python'
        script = os.path.join(os.path.dirname(BASE_DIR), 'aivirtualmouseproject.py')
        # On Windows, open a new console so the camera app can show its window.
        if os.name == 'nt':
            subprocess.Popen([python, script], creationflags=subprocess.CREATE_NEW_CONSOLE, close_fds=True)
        else:
            subprocess.Popen([python, script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    except Exception:
        pass


@app.route('/bgvideo')
def bg_video():
    """Serve configured local background video file.

    Note: the browser will request this route; it streams the local file if present.
    If the file doesn't exist, this returns 404.
    You can override the file path by setting the BG_VIDEO environment variable.
    """
    path = os.environ.get('BG_VIDEO') or BG_VIDEO_PATH
    if not path or not os.path.exists(path):
        abort(404)
    try:
        return send_file(path, mimetype='video/mp4', conditional=True)
    except Exception:
        abort(404)


with app.app_context():
    init_db()


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash('Provide email and password')
            return redirect(url_for('signup'))
        if find_user_by_email(email):
            flash('Email already registered')
            return redirect(url_for('signup'))
        pw_hash = generate_password_hash(password)
        now = datetime.utcnow().isoformat()
        db = get_db()
        db.execute('INSERT INTO users (email, password_hash, created_at, subscription_plan, subscription_start, subscription_active) VALUES (?,?,?,?,?,?)',
                   (email, pw_hash, now, 'trial', now, 1))
        db.commit()
        flash('Account created — you have a 10-day free trial')
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = find_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            write_session_file(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
        return redirect(url_for('login'))
    return render_template('login.html')



@app.route('/login/google')
def login_google():
    redirect_uri = url_for('auth_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/auth/google')
def auth_google():
    token = oauth.google.authorize_access_token()
    userinfo = oauth.google.parse_id_token(token)
    email = userinfo.get('email')
    if not email:
        flash('Failed to retrieve email from Google')
        return redirect(url_for('login'))
    user = find_user_by_email(email)
    if not user:
        user = create_user_for_oauth(email)
    session['user_id'] = user['id']
    write_session_file(user)
    return redirect(url_for('dashboard'))


@app.route('/login/microsoft')
def login_microsoft():
    redirect_uri = url_for('auth_microsoft', _external=True)
    return oauth.microsoft.authorize_redirect(redirect_uri)


@app.route('/auth/microsoft')
def auth_microsoft():
    token = oauth.microsoft.authorize_access_token()
    # fetch user info from Microsoft Graph
    resp = oauth.microsoft.get('https://graph.microsoft.com/v1.0/me')
    if resp.status_code != 200:
        flash('Failed to retrieve Microsoft profile')
        return redirect(url_for('login'))
    profile = resp.json()
    email = profile.get('mail') or profile.get('userPrincipalName')
    if not email:
        flash('Failed to get email from Microsoft account')
        return redirect(url_for('login'))
    user = find_user_by_email(email)
    if not user:
        user = create_user_for_oauth(email)
    session['user_id'] = user['id']
    write_session_file(user)
    return redirect(url_for('dashboard'))


def get_user_by_id(user_id):
    db = get_db()
    cur = db.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    return cur.fetchone()


@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    user = get_user_by_id(user_id)
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login'))

    created = datetime.fromisoformat(user['created_at'])
    now = datetime.utcnow()
    days_since = (now - created).days
    trial_days = 10
    remaining = max(0, trial_days - days_since)

    # If trial expired and user didn't subscribe, mark inactive and prompt subscription
    if user['subscription_plan'] == 'trial' and days_since >= trial_days:
        db = get_db()
        db.execute('UPDATE users SET subscription_active = 0 WHERE id = ?', (user_id,))
        db.commit()
        flash('Your free trial has ended — choose a subscription')
        return redirect(url_for('subscribe'))

    return render_template('dashboard.html', user=user, remaining=remaining)


@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    user = get_user_by_id(user_id)
    if request.method == 'POST':
        plan = request.form.get('plan')
        prices = {'basic': 4.99, 'pro': 9.99, 'enterprise': 19.99}
        if plan not in prices:
            flash('Invalid plan')
            return redirect(url_for('subscribe'))
        price = prices[plan]
        now = datetime.utcnow().isoformat()
        db = get_db()
        # update plan, start, active and price
        db.execute('UPDATE users SET subscription_plan = ?, subscription_start = ?, subscription_active = 1, subscription_price = ? WHERE id = ?',
                   (plan, now, price, user_id))
        db.commit()
        # update session file if present
        try:
            cur = db.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            updated = cur.fetchone()
            if updated:
                write_session_file(updated)
        except Exception:
            pass
        # start the AI Virtual Mouse app when a user subscribes (opens camera)
        try:
            start_ai_mouse()
        except Exception:
            pass
        flash(f'Subscribed to {plan} successfully')
        return redirect(url_for('dashboard'))
    # show prices in template
    plan_prices = {'basic': 4.99, 'pro': 9.99, 'enterprise': 19.99}
    return render_template('subscribe.html', user=user, plan_prices=plan_prices)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    clear_session_file()
    return redirect(url_for('login'))


if __name__ == '__main__':
    os.makedirs(BASE_DIR, exist_ok=True)
    app.run(host='localhost', port=5000, debug=True)
