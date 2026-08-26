from flask import Blueprint, render_template, request, redirect, session, jsonify, flash
from models import get_user_by_email, create_user

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def index():
    if "email" in session:
        return redirect("/dashboard")
    return render_template("login.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "email" in session:
            return redirect("/dashboard")
        return render_template("login.html")

    # Form or JSON login
    if request.is_json:
        data = request.get_json() or {}
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
    else:
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

    user = get_user_by_email(email)
    if user and user["password"] == password:
        session["email"] = user["email"]
        session["name"] = user["name"]
        session["preferred_lang"] = user.get("preferred_lang", "auto")
        session["theme"] = user.get("theme", "dark")

        if request.is_json:
            return jsonify({"success": True, "redirect": "/dashboard", "user": {"name": user["name"], "email": user["email"]}})
        return redirect("/dashboard")
    else:
        if request.is_json:
            return jsonify({"success": False, "error": "Invalid email or password"}), 401
        return render_template("login.html", error="Invalid email or password")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if "email" in session:
            return redirect("/dashboard")
        return render_template("register.html")

    if request.is_json:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
    else:
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

    if not name or not email or not password:
        if request.is_json:
            return jsonify({"success": False, "error": "All fields are required"}), 400
        return render_template("register.html", error="All fields are required")

    existing = get_user_by_email(email)
    if existing:
        if request.is_json:
            return jsonify({"success": False, "error": "An account with this email already exists"}), 400
        return render_template("register.html", error="Email already registered. Please login.")

    create_user(name, email, password)
    session["email"] = email
    session["name"] = name
    session["preferred_lang"] = "auto"
    session["theme"] = "dark"

    if request.is_json:
        return jsonify({"success": True, "redirect": "/dashboard"})
    return redirect("/dashboard")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@auth_bp.route("/api/auth/me")
def me():
    if "email" not in session:
        return jsonify({"authenticated": False}), 401
    return jsonify({
        "authenticated": True,
        "email": session["email"],
        "name": session.get("name", "User"),
        "preferred_lang": session.get("preferred_lang", "auto"),
        "theme": session.get("theme", "dark")
    })
