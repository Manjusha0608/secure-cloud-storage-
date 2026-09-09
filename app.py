import os
import sqlite3
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    flash
)

from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet


# -----------------------------
# Flask configuration
# -----------------------------

app = Flask(__name__)

app.secret_key = "change-this-secret-key-later"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE = os.path.join(BASE_DIR, "database.db")
KEY_FILE = os.path.join(BASE_DIR, "secret.key")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -----------------------------
# Encryption
# -----------------------------

def get_encryption_key():

    if not os.path.exists(KEY_FILE):

        key = Fernet.generate_key()

        with open(KEY_FILE, "wb") as file:
            file.write(key)

    with open(KEY_FILE, "rb") as file:
        return file.read()


ENCRYPTION_KEY = get_encryption_key()

cipher = Fernet(ENCRYPTION_KEY)


# -----------------------------
# Database
# -----------------------------

def get_db():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS shared_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            shared_with INTEGER NOT NULL,
            FOREIGN KEY(file_id) REFERENCES files(id),
            FOREIGN KEY(shared_with) REFERENCES users(id)
        )
    """)

    connection.commit()

    connection.close()


# -----------------------------
# Login required
# -----------------------------

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash("Please login first.")

            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return decorated_function


# -----------------------------
# Home
# -----------------------------

@app.route("/")
def home():

    if "user_id" in session:

        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# -----------------------------
# Register
# -----------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()

        password = request.form["password"]

        if not username or not password:

            flash("Username and password are required.")

            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        connection = get_db()

        try:

            connection.execute(
                """
                INSERT INTO users (username, password)
                VALUES (?, ?)
                """,
                (username, hashed_password)
            )

            connection.commit()

        except sqlite3.IntegrityError:

            connection.close()

            flash("Username already exists.")

            return redirect(url_for("register"))

        connection.close()

        flash("Registration successful.")

        return redirect(url_for("login"))

    return render_template("register.html")


# -----------------------------
# Login
# -----------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()

        password = request.form["password"]

        connection = get_db()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            session["username"] = user["username"]

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template("login.html")


# -----------------------------
# Logout
# -----------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# -----------------------------
# Dashboard
# -----------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_db()

    files = connection.execute(
        """
        SELECT *
        FROM files
        WHERE owner_id = ?
        """,
        (session["user_id"],)
    ).fetchall()

    shared_files = connection.execute(
        """
        SELECT
            files.id,
            files.original_name,
            users.username AS owner
        FROM shared_files
        JOIN files
            ON shared_files.file_id = files.id
        JOIN users
            ON files.owner_id = users.id
        WHERE shared_files.shared_with = ?
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        files=files,
        shared_files=shared_files
    )


# -----------------------------
# Upload
# -----------------------------

@app.route("/upload", methods=["POST"])
@login_required
def upload():

    uploaded_file = request.files.get("file")

    if not uploaded_file or uploaded_file.filename == "":

        flash("Please select a file.")

        return redirect(url_for("dashboard"))

    original_name = uploaded_file.filename

    file_data = uploaded_file.read()

    # Encrypt the file
    encrypted_data = cipher.encrypt(file_data)

    # Generate random stored filename
    stored_name = os.urandom(16).hex() + ".enc"

    stored_path = os.path.join(
        UPLOAD_FOLDER,
        stored_name
    )

    with open(stored_path, "wb") as file:

        file.write(encrypted_data)

    connection = get_db()

    connection.execute(
        """
        INSERT INTO files (
            original_name,
            stored_name,
            owner_id
        )
        VALUES (?, ?, ?)
        """,
        (
            original_name,
            stored_name,
            session["user_id"]
        )
    )

    connection.commit()

    connection.close()

    flash("File uploaded and encrypted successfully.")

    return redirect(url_for("dashboard"))


# -----------------------------
# Download
# -----------------------------

@app.route("/download/<int:file_id>")
@login_required
def download(file_id):

    connection = get_db()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE id = ?
        """,
        (file_id,)
    ).fetchone()

    connection.close()

    if not file_record:

        flash("File not found.")

        return redirect(url_for("dashboard"))

    # Check access permission
    connection = get_db()

    has_access = connection.execute(
        """
        SELECT files.id
        FROM files
        LEFT JOIN shared_files
            ON files.id = shared_files.file_id
        WHERE files.id = ?
        AND (
            files.owner_id = ?
            OR shared_files.shared_with = ?
        )
        """,
        (
            file_id,
            session["user_id"],
            session["user_id"]
        )
    ).fetchone()

    connection.close()

    if not has_access:

        flash("You do not have permission to access this file.")

        return redirect(url_for("dashboard"))

    stored_path = os.path.join(
        UPLOAD_FOLDER,
        file_record["stored_name"]
    )

    if not os.path.exists(stored_path):

        flash("Encrypted file is missing.")

        return redirect(url_for("dashboard"))

    with open(stored_path, "rb") as file:

        encrypted_data = file.read()

    # Decrypt file
    decrypted_data = cipher.decrypt(encrypted_data)

    temp_path = os.path.join(
        UPLOAD_FOLDER,
        "temp_" + file_record["original_name"]
    )

    with open(temp_path, "wb") as file:

        file.write(decrypted_data)

    return send_file(
        temp_path,
        as_attachment=True,
        download_name=file_record["original_name"]
    )


# -----------------------------
# Share file
# -----------------------------

@app.route("/share/<int:file_id>", methods=["POST"])
@login_required
def share(file_id):

    username = request.form["username"].strip()

    connection = get_db()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE id = ?
        AND owner_id = ?
        """,
        (file_id, session["user_id"])
    ).fetchone()

    if not file_record:

        connection.close()

        flash("You can only share your own files.")

        return redirect(url_for("dashboard"))

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    if not user:

        connection.close()

        flash("User does not exist.")

        return redirect(url_for("dashboard"))

    if user["id"] == session["user_id"]:

        connection.close()

        flash("You cannot share a file with yourself.")

        return redirect(url_for("dashboard"))

    connection.execute(
        """
        INSERT INTO shared_files (
            file_id,
            shared_with
        )
        VALUES (?, ?)
        """,
        (file_id, user["id"])
    )

    connection.commit()

    connection.close()

    flash("File shared successfully.")

    return redirect(url_for("dashboard"))


# -----------------------------
# Run application
# -----------------------------

if __name__ == "__main__":

    initialize_database()

    app.run(debug=True)