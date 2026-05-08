import os
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import get_db, init_db, seed_db, get_user_by_email, create_user
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown

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
    uid = session["user_id"]

    # SECTION_USER_STATS_START
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    stats = get_summary_stats(uid)
    # SECTION_USER_STATS_END

    # SECTION_TRANSACTIONS_START
    transactions = get_recent_transactions(uid)
    # SECTION_TRANSACTIONS_END

    # SECTION_CATEGORIES_START
    categories = get_category_breakdown(uid)
    # SECTION_CATEGORIES_END

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
