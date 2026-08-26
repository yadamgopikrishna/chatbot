from flask import Blueprint, render_template, request, redirect, session, jsonify, flash, url_for
from models import (
    get_user_by_email,
    create_user,
    create_password_reset_token,
    verify_password_reset_token,
    mark_password_reset_used,
    update_user_password
)

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
        if user.get("api_key"):
            session["gemini_api_key"] = user["api_key"]

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


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")

    email = (request.form.get("email") or (request.get_json() or {}).get("email") or "").strip()
    if not email:
        return render_template("forgot_password.html", error="Please enter your email address.")

    user = get_user_by_email(email)
    if not user:
        return render_template("forgot_password.html", error="No account found with this email address.")

    token = create_password_reset_token(email)
    reset_url = url_for("auth.reset_password", token=token, _external=True)

    if request.is_json:
        return jsonify({"success": True, "reset_url": reset_url, "token": token})

    return render_template("forgot_password.html", success=True, reset_url=reset_url, email=email)


@auth_bp.route("/reset-password", methods=["GET", "POST"])
@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token=None):
    if not token:
        token = request.args.get("token") or request.form.get("token")

    if not token:
        return render_template("reset_password.html", error="Invalid or missing password reset link.")

    email = verify_password_reset_token(token)
    if not email:
        return render_template("reset_password.html", error="Password reset link is invalid or has expired.")

    if request.method == "GET":
        return render_template("reset_password.html", token=token, email=email)

    password = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not password or len(password) < 4:
        return render_template("reset_password.html", token=token, email=email, error="Password must be at least 4 characters long.")

    if password != confirm_password:
        return render_template("reset_password.html", token=token, email=email, error="Passwords do not match.")

    # Update password
    update_user_password(email, password)
    mark_password_reset_used(token)

    return render_template("reset_password.html", success=True)


@auth_bp.route("/api/auth/change-password", methods=["POST"])
def change_password():
    """In-app password change for authenticated users."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    data = request.get_json() or {}
    current_password = data.get("current_password", "").strip()
    new_password = data.get("new_password", "").strip()

    if not current_password or not new_password:
        return jsonify({"success": False, "error": "Current and new passwords are required."}), 400

    if len(new_password) < 4:
        return jsonify({"success": False, "error": "New password must be at least 4 characters."}), 400

    user = get_user_by_email(session["email"])
    if not user or user["password"] != current_password:
        return jsonify({"success": False, "error": "Incorrect current password."}), 400

    update_user_password(session["email"], new_password)
    return jsonify({"success": True, "message": "Password changed successfully!"})


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
