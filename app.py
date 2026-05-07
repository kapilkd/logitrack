import os
from flask import Flask, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash
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


@app.route("/login")
def login():
    return render_template("login.html")


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
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
