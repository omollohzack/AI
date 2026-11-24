import os
import sqlite3
import secrets
from urllib.parse import urlparse
from pathlib import Path

from authlib.integrations.flask_client import OAuth
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from AIChat import generate_code


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")
app.config["GITHUB_CLIENT_ID"] = os.getenv("GITHUB_CLIENT_ID")
app.config["GITHUB_CLIENT_SECRET"] = os.getenv("GITHUB_CLIENT_SECRET")
app.config["APPLE_CLIENT_ID"] = os.getenv("APPLE_CLIENT_ID")
app.config["APPLE_CLIENT_SECRET"] = os.getenv("APPLE_CLIENT_SECRET")

oauth = OAuth(app)
oauth.register(
    "google",
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
oauth.register(
    "github",
    client_id=app.config["GITHUB_CLIENT_ID"],
    client_secret=app.config["GITHUB_CLIENT_SECRET"],
    authorize_url="https://github.com/login/oauth/authorize",
    access_token_url="https://github.com/login/oauth/access_token",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)
oauth.register(
    "apple",
    client_id=app.config["APPLE_CLIENT_ID"],
    client_secret=app.config["APPLE_CLIENT_SECRET"],
    authorize_url="https://appleid.apple.com/auth/authorize",
    access_token_url="https://appleid.apple.com/auth/token",
    jwks_uri="https://appleid.apple.com/auth/oauth2/v2/keys",
    client_kwargs={"scope": "name email", "response_mode": "form_post"},
)

DATABASE = Path(__file__).resolve().parent / "users.db"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS model_settings (
                user_id INTEGER PRIMARY KEY,
                provider_name TEXT NOT NULL DEFAULT 'OpenAI',
                base_url TEXT,
                api_key TEXT,
                model TEXT NOT NULL DEFAULT 'gpt-4o-mini',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )


initialize_database()


def ensure_oauth_user(email):
    email = email.strip().lower()
    if not email:
        return None
    with get_db() as connection:
        user = connection.execute("SELECT id, email FROM users WHERE email = ?", (email,)).fetchone()
        if user is None:
            cursor = connection.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, generate_password_hash(secrets.token_urlsafe(32))),
            )
            user_id = cursor.lastrowid
        else:
            user_id = user["id"]
    session.clear()
    session["user_id"] = user_id
    session["email"] = email
    return user_id


@app.before_request
def require_login():
    public_routes = {
        "login", "login_post", "register", "register_post", "static",
        "oauth_login", "oauth_callback",
    }
    if request.endpoint not in public_routes and "user_id" not in session:
        return redirect(url_for("login"))


@app.get("/login")
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    oauth_error = session.pop("oauth_error", None)
    return render_template("login.html", mode="login", oauth_error=oauth_error)


@app.post("/login")
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not email or not password:
        return render_template("login.html", mode="login", error="Enter your email and password.")

    with get_db() as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", mode="login", error="Invalid email or password.")

    session.clear()
    session["user_id"] = user["id"]
    session["email"] = user["email"]
    return redirect(url_for("index"))


@app.get("/register")
def register():
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("login.html", mode="register")


@app.post("/register")
def register_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    if not email or "@" not in email:
        return render_template("login.html", mode="register", error="Enter a valid email address.")
    if len(password) < 8:
        return render_template("login.html", mode="register", error="Password must be at least 8 characters.")
    if password != confirm_password:
        return render_template("login.html", mode="register", error="Passwords do not match.")

    try:
        with get_db() as connection:
            cursor = connection.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, generate_password_hash(password)),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return render_template("login.html", mode="register", error="An account already exists for this email.")

    session.clear()
    session["user_id"] = user_id
    session["email"] = email
    return redirect(url_for("index"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/auth/<provider>")
def oauth_login(provider):
    if provider not in ("google", "github", "apple"):
        return redirect(url_for("login"))
    client = oauth.create_client(provider)
    if client is None:
        return redirect(url_for("login"))
    configured_secret = app.config[f"{provider.upper()}_CLIENT_SECRET"]
    if not configured_secret:
        session["oauth_error"] = f"{provider.title()} sign-in is not configured. Add your OAuth credentials."
        return redirect(url_for("login"))
    if provider == "apple":
        redirect_uri = url_for("oauth_callback", provider="apple", _external=True)
    else:
        redirect_uri = url_for("oauth_callback", provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)


@app.route("/auth/<provider>/callback", methods=["GET", "POST"])
def oauth_callback(provider):
    if provider not in ("google", "github", "apple"):
        return redirect(url_for("login"))
    client = oauth.create_client(provider)
    if client is None:
        session["oauth_error"] = f"{provider.title()} sign-in is unavailable."
        return redirect(url_for("login"))
    try:
        token = client.authorize_access_token()
        if provider == "google":
            user_info = token.get("userinfo") or client.parse_id_token(token)
            email = user_info.get("email")
        elif provider == "github":
            user_info = client.get("user").json()
            email = user_info.get("email")
            if not email:
                emails = client.get("user/emails").json()
                email = next((item["email"] for item in emails if item.get("primary") and item.get("verified")), None)
        else:
            user_info = token.get("userinfo") or {}
            email = user_info.get("email")
            if not email:
                id_token = token.get("id_token")
                if id_token:
                    claims = client.parse_id_token(token)
                    email = claims.get("email")
    except Exception as error:
        app.logger.exception("OAuth sign-in failed")
        session["oauth_error"] = f"{provider.title()} sign-in could not be completed."
        return redirect(url_for("login"))

    if not email:
        session["oauth_error"] = f"{provider.title()} did not provide an email address."
        return redirect(url_for("login"))
    ensure_oauth_user(email)
    return redirect(url_for("index"))


def get_model_settings(user_id):
    with get_db() as connection:
        settings = connection.execute(
            "SELECT provider_name, base_url, api_key, model FROM model_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if settings is None:
        return {
            "provider_name": "OpenAI",
            "base_url": os.getenv("OPENAI_BASE_URL", ""),
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        }
    return dict(settings)


@app.get("/api/models/settings")
def model_settings():
    settings = get_model_settings(session["user_id"])
    settings["api_key"] = bool(settings["api_key"])
    return jsonify(settings)


@app.post("/api/models/settings")
def save_model_settings():
    payload = request.get_json(silent=True) or {}
    provider_name = str(payload.get("provider_name", "Custom")).strip()[:100]
    base_url = str(payload.get("base_url", "")).strip().rstrip("/")
    api_key = str(payload.get("api_key", "")).strip()
    model = str(payload.get("model", "")).strip()

    if base_url:
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return jsonify({"error": "Base URL must start with http:// or https://."}), 400
    if not api_key:
        return jsonify({"error": "Enter an API key."}), 400
    if not model:
        return jsonify({"error": "Enter a model name or ID."}), 400

    existing = get_model_settings(session["user_id"])
    if api_key == "••••••••":
        api_key = existing["api_key"]
    if not api_key:
        return jsonify({"error": "Enter an API key."}), 400

    with get_db() as connection:
        connection.execute(
            """
            INSERT INTO model_settings (user_id, provider_name, base_url, api_key, model, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                provider_name = excluded.provider_name,
                base_url = excluded.base_url,
                api_key = excluded.api_key,
                model = excluded.model,
                updated_at = CURRENT_TIMESTAMP
            """,
            (session["user_id"], provider_name, base_url or None, api_key, model),
        )
    return jsonify({"ok": True, "provider_name": provider_name, "model": model})


@app.get("/")
def index():
    settings = get_model_settings(session["user_id"])
    return render_template(
        "index.html",
        api_configured=bool(settings["api_key"]),
        email=session.get("email", ""),
        provider_name=settings["provider_name"],
        model=settings["model"],
    )


@app.post("/api/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"error": "Enter a prompt to generate code."}), 400
    if len(prompt) > 12000:
        return jsonify({"error": "Prompt must be 12,000 characters or fewer."}), 400
    settings = get_model_settings(session["user_id"])
    if not settings["api_key"]:
        return jsonify({"error": "Configure a model API key in Model Settings."}), 503

    try:
        return jsonify({
            "code": generate_code(
                prompt,
                api_key=settings["api_key"],
                base_url=settings["base_url"],
                model=settings["model"],
            )
        })
    except Exception as error:
        app.logger.exception("Code generation failed")
        return jsonify({"error": str(error)}), 502


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
