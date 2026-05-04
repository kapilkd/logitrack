from flask import Flask, render_template

app = Flask(__name__)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/login")
def login():
    return render_template("login.html")


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
