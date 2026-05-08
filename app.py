import os
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import get_db, init_db, seed_db, get_user_by_email, create_user

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.")

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    if get_user_by_email(email):
        return render_template("register.html", error="An account with that email already exists.")

    create_user(name, email, generate_password_hash(password))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    name = session.get("user_name", "Demo User")
    initials = "".join(w[0].upper() for w in name.split() if w)

    user = {"name": name, "initials": initials, "email": "demo@logitrack.com", "member_since": "January 2026"}

    stats = {"total_spent": "₹2,47,830.00", "transaction_count": 24, "top_category": "Freight Charges"}

    transactions = [
        {"date": "07 May 2026", "description": "Sea freight Mumbai to Dubai",     "category": "Freight Charges",   "amount": "₹12,500.00"},
        {"date": "06 May 2026", "description": "Marine cargo insurance premium",  "category": "Insurance",          "amount": "₹2,100.00"},
        {"date": "05 May 2026", "description": "Cold storage 7 days",             "category": "Warehouse Charges", "amount": "₹4,750.00"},
        {"date": "04 May 2026", "description": "Bill of lading and packing list", "category": "Documentation",     "amount": "₹950.00"},
        {"date": "03 May 2026", "description": "Import clearance charges",        "category": "Customs Duty",      "amount": "₹3,200.00"},
        {"date": "02 May 2026", "description": "Port handling fee JNPT",          "category": "Port Charges",      "amount": "₹1,800.00"},
    ]

    categories = [
        {"name": "Freight Charges",     "amount": "₹87,500.00", "count": 7, "pct": 85},
        {"name": "Vendor Payments",     "amount": "₹62,300.00", "count": 5, "pct": 65},
        {"name": "Customs Duty",        "amount": "₹45,800.00", "count": 4, "pct": 45},
        {"name": "Penalty & Demurrage", "amount": "₹28,600.00", "count": 3, "pct": 28},
        {"name": "Insurance",           "amount": "₹15,400.00", "count": 3, "pct": 15},
        {"name": "Warehouse Charges",   "amount": "₹8,230.00",  "count": 2, "pct": 8},
    ]

    return render_template("profile.html", user=user, stats=stats, transactions=transactions, categories=categories)


@app.route("/shipments/add")
def add_shipment():
    return "Add shipment — coming in Step 7"


@app.route("/shipments/<int:id>/edit")
def edit_shipment(id):
    return "Edit shipment — coming in Step 8"


@app.route("/shipments/<int:id>/delete")
def delete_shipment(id):
    return "Delete shipment — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
