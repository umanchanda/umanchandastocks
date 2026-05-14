from flask import Blueprint, flash, redirect, render_template, request, session, current_app
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.security import check_password_hash, generate_password_hash

from models import db, User

auth_bp = Blueprint("auth", __name__)

_mail = None


def set_mail(mail_instance):
    global _mail
    _mail = mail_instance


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username:
            flash("Must provide username", "error")
            return redirect("/register")
        if not email or "@" not in email:
            flash("Must provide a valid email address", "error")
            return redirect("/register")
        if not password:
            flash("Must provide password", "error")
            return redirect("/register")
        if len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return redirect("/register")
        if password != confirmation:
            flash("Passwords do not match", "error")
            return redirect("/register")
        try:
            username_taken = User.query.filter_by(username=username).first()
            email_taken = User.query.filter_by(email=email).first()
        except Exception:
            flash("An error occurred. Please try again.", "error")
            return redirect("/register")

        if username_taken:
            flash("Username already taken", "error")
            return redirect("/register")
        if email_taken:
            flash("An account with that email already exists", "error")
            return redirect("/register")

        try:
            user = User(username=username, email=email, hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("An error occurred creating your account. Please try again.", "error")
            return redirect("/register")
        session["user_id"] = user.id
        return redirect("/")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username:
            flash("Must provide username", "error")
            return redirect("/login")
        if not password:
            flash("Must provide password", "error")
            return redirect("/login")

        try:
            user = User.query.filter_by(username=username).first()
        except Exception:
            flash("An error occurred. Please try again.", "error")
            return redirect("/login")

        if not user or not check_password_hash(user.hash, password):
            flash("Invalid username or password", "error")
            return redirect("/login")

        session["user_id"] = user.id
        return redirect("/")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Must provide an email address", "error")
            return redirect("/forgot-password")

        user = User.query.filter_by(email=email).first()
        # Always show the same message to avoid leaking which emails are registered
        if user and _mail:
            token = _serializer().dumps(user.email, salt="password-reset")
            reset_url = request.host_url.rstrip("/") + f"/reset-password/{token}"
            msg = Message(
                subject="UDAY Finance — Password Reset",
                recipients=[user.email],
                body=(
                    f"Hi {user.username},\n\n"
                    f"Click the link below to reset your password. "
                    f"This link expires in 1 hour.\n\n"
                    f"{reset_url}\n\n"
                    f"If you did not request a password reset, you can ignore this email."
                )
            )
            try:
                _mail.send(msg)
            except Exception:
                flash("Could not send reset email — please check the mail configuration.", "error")
                return redirect("/forgot-password")

        flash("If that email is registered, you'll receive a reset link shortly.", "success")
        return redirect("/login")

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = _serializer().loads(token, salt="password-reset", max_age=3600)
    except SignatureExpired:
        flash("That reset link has expired. Please request a new one.", "error")
        return redirect("/forgot-password")
    except BadSignature:
        flash("Invalid reset link.", "error")
        return redirect("/forgot-password")

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User not found.", "error")
        return redirect("/forgot-password")

    if request.method == "POST":
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not password:
            flash("Must provide a new password", "error")
            return redirect(f"/reset-password/{token}")
        if len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return redirect(f"/reset-password/{token}")
        if password != confirmation:
            flash("Passwords do not match", "error")
            return redirect(f"/reset-password/{token}")

        user.hash = generate_password_hash(password)
        db.session.commit()
        flash("Password updated successfully. Please log in.", "success")
        return redirect("/login")

    return render_template("auth/reset_password.html", token=token)
