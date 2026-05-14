from flask import Blueprint, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username:
            flash("Must provide username", "error")
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
            if User.query.filter_by(username=username).first():
                flash("Username already taken", "error")
                return redirect("/register")
            user = User(username=username, hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("An error occurred. Please try again.", "error")
            return redirect("/register")

        session.clear()
        session["user_id"] = user.id
        return redirect("/")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
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

        session.clear()
        session["user_id"] = user.id
        return redirect("/")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
