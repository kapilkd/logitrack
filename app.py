import math
import os
import re
from datetime import date, timedelta
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import get_db, init_db, seed_db, get_user_by_email, create_user, create_expense, get_expense_by_id, update_expense, delete_expense, create_vendor, get_vendor_by_id as get_vendor_row, update_vendor, get_vendors_by_user, get_vendor_count
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

with app.app_context():
    init_db()
    seed_db()


def _parse_date(raw):
    if not raw:
        return None
    try:
        date.fromisoformat(raw)
        return raw
    except ValueError:
        return None


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
    # SECTION_USER_STATS_END

    from_date = _parse_date(request.args.get("from_date", ""))
    to_date = _parse_date(request.args.get("to_date", ""))

    today = date.today()
    first_this_month = today.replace(day=1)
    last_month_end = first_this_month - timedelta(days=1)
    first_last_month = last_month_end.replace(day=1)
    last_3m_start = today - timedelta(days=89)  # 89 days back + today = 90-day inclusive window

    presets = {
        "this_month":    (first_this_month.isoformat(), today.isoformat()),
        "last_month":    (first_last_month.isoformat(), last_month_end.isoformat()),
        "last_3_months": (last_3m_start.isoformat(),    today.isoformat()),
    }

    if from_date is None and to_date is None:
        active_preset = "all"
    elif (from_date, to_date) == presets["this_month"]:
        active_preset = "this_month"
    elif (from_date, to_date) == presets["last_month"]:
        active_preset = "last_month"
    elif (from_date, to_date) == presets["last_3_months"]:
        active_preset = "last_3_months"
    else:
        active_preset = "custom"

    # SECTION_USER_STATS_START
    stats = get_summary_stats(uid, from_date=from_date, to_date=to_date)
    # SECTION_USER_STATS_END

    # SECTION_TRANSACTIONS_START
    transactions = get_recent_transactions(uid, from_date=from_date, to_date=to_date)
    # SECTION_TRANSACTIONS_END

    # SECTION_CATEGORIES_START
    categories = get_category_breakdown(uid, from_date=from_date, to_date=to_date)
    # SECTION_CATEGORIES_END

    return render_template(
        "profile.html",
        user=user, stats=stats, transactions=transactions, categories=categories,
        from_date=from_date or "",
        to_date=to_date or "",
        active_preset=active_preset,
        presets=presets,
    )


@app.route("/shipments")
def shipments():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    transactions = get_recent_transactions(uid, limit=1000)
    return render_template("shipments.html", user=user, transactions=transactions)


def _next_vendor_code(vendor_list):
    max_num = 0
    for v in vendor_list:
        m = re.match(r'^VND-(\d+)$', v["vendor_code"] or "", re.IGNORECASE)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"VND-{max_num + 1:03d}"


@app.route("/vendors/add", methods=["POST"])
def add_vendor():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]

    vendor_code   = request.form.get("vendor_code", "").strip()
    vendor_name   = request.form.get("vendor_name", "").strip()
    vendor_type   = request.form.get("vendor_type", "").strip()
    vendor_cat    = request.form.get("vendor_category", "").strip()

    if not vendor_name or not vendor_type or not vendor_cat:
        return redirect(url_for("vendors"))

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    def _num(key, cast, default):
        try:
            return cast(request.form.get(key, "").strip())
        except (ValueError, TypeError):
            return default

    try:
        create_vendor(
            user_id=uid,
            vendor_code=vendor_code,
            vendor_name=vendor_name,
            vendor_type=vendor_type,
            vendor_category=vendor_cat,
            company_name=_f("company_name"),
            owner_name=_f("owner_name"),
            status=request.form.get("status", "ACTIVE"),
            email=_f("email"),
            phone=_f("phone"),
            alternate_phone=_f("alternate_phone"),
            website=_f("website"),
            address_line1=_f("address_line1"),
            address_line2=_f("address_line2"),
            city=_f("city"),
            state=_f("state"),
            pincode=_f("pincode"),
            gst_number=_f("gst_number"),
            pan_number=_f("pan_number"),
            iec_code=_f("iec_code"),
            bank_name=_f("bank_name"),
            account_number=_f("account_number"),
            ifsc_code=_f("ifsc_code"),
            upi_id=_f("upi_id"),
            currency=request.form.get("currency", "INR"),
            credit_limit=_num("credit_limit", float, 0.0),
            payment_terms_days=_num("payment_terms_days", int, 0),
            notes=_f("notes"),
            created_by=uid,
        )
    except Exception:
        pass

    return redirect(url_for("vendors"))


@app.route("/vendors/<int:vendor_id>/edit", methods=["POST"])
def edit_vendor(vendor_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]

    vendor = get_vendor_row(vendor_id)
    if vendor is None or vendor["user_id"] != uid:
        abort(404)

    vendor_name = request.form.get("vendor_name", "").strip()
    vendor_type = request.form.get("vendor_type", "").strip()
    vendor_cat  = request.form.get("vendor_category", "").strip()

    if not vendor_name or not vendor_type or not vendor_cat:
        return redirect(url_for("vendors"))

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    def _num(key, cast, default):
        try:
            return cast(request.form.get(key, "").strip())
        except (ValueError, TypeError):
            return default

    update_vendor(
        vendor_id=vendor_id,
        vendor_code=vendor["vendor_code"],
        vendor_name=vendor_name,
        vendor_type=vendor_type,
        vendor_category=vendor_cat,
        company_name=_f("company_name"),
        owner_name=_f("owner_name"),
        status=request.form.get("status", "ACTIVE"),
        email=_f("email"),
        phone=_f("phone"),
        alternate_phone=_f("alternate_phone"),
        website=_f("website"),
        address_line1=_f("address_line1"),
        address_line2=_f("address_line2"),
        city=_f("city"),
        state=_f("state"),
        pincode=_f("pincode"),
        gst_number=_f("gst_number"),
        pan_number=_f("pan_number"),
        iec_code=_f("iec_code"),
        bank_name=_f("bank_name"),
        account_number=_f("account_number"),
        ifsc_code=_f("ifsc_code"),
        upi_id=_f("upi_id"),
        currency=request.form.get("currency", "INR"),
        credit_limit=_num("credit_limit", float, 0.0),
        payment_terms_days=_num("payment_terms_days", int, 0),
        notes=_f("notes"),
        updated_by=uid,
    )
    return redirect(url_for("vendors"))


@app.route("/vendors")
def vendors():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    vendor_list = [dict(v) for v in get_vendors_by_user(uid)]
    active_count = sum(1 for v in vendor_list if v["status"] == "ACTIVE")
    stats = {
        "total": len(vendor_list),
        "active": active_count,
        "inactive": len(vendor_list) - active_count,
    }
    return render_template(
        "vendors.html",
        user=user,
        vendors=vendor_list,
        stats=stats,
        next_vendor_code=_next_vendor_code(vendor_list),
    )


@app.route("/billing")
def billing():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("placeholder.html", title="Billing")


@app.route("/emails")
def emails():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("placeholder.html", title="Emails")


@app.route("/notifications")
def notifications():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("placeholder.html", title="Notifications")


@app.route("/reports")
def reports():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("placeholder.html", title="Reports")


@app.route("/settings")
def settings():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("placeholder.html", title="Settings")


EXPENSE_CATEGORIES = [
    "Freight Charges", "Customs Duty", "Port Charges", "Documentation",
    "Warehouse Charges", "Insurance", "Courier & Shipping",
    "Penalty & Demurrage", "Other",
]


@app.route("/shipments/add", methods=["GET", "POST"])
def add_shipment():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            today=date.today().isoformat(),
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    def bad(msg):
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            today=date.today().isoformat(),
            error=msg,
            form=request.form,
        )

    try:
        amount = float(amount_raw)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except ValueError:
        return bad("Amount must be a positive number.")

    if category not in EXPENSE_CATEGORIES:
        return bad("Please select a valid category.")

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_raw):
        return bad("Please enter a valid date.")
    try:
        date.fromisoformat(date_raw)
    except ValueError:
        return bad("Please enter a valid date.")

    create_expense(session["user_id"], amount, category, date_raw, description or None)
    return redirect(url_for("profile"))


@app.route("/shipments/<int:id>/edit", methods=["GET", "POST"])
def edit_shipment(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id)
    if expense is None:
        abort(404)
    if expense["user_id"] != session["user_id"]:
        abort(403)

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=EXPENSE_CATEGORIES,
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    def bad(msg):
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=EXPENSE_CATEGORIES,
            error=msg,
            form=request.form,
        )

    try:
        amount = float(amount_raw)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except ValueError:
        return bad("Amount must be a positive number.")

    if category not in EXPENSE_CATEGORIES:
        return bad("Please select a valid category.")

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_raw):
        return bad("Please enter a valid date.")
    try:
        date.fromisoformat(date_raw)
    except ValueError:
        return bad("Please enter a valid date.")

    update_expense(id, amount, category, date_raw, description or None)
    return redirect(url_for("profile"))


@app.route("/shipments/<int:id>/delete", methods=["POST"])
def delete_shipment(id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    expense = get_expense_by_id(id)
    if expense is None:
        abort(404)
    if expense["user_id"] != session["user_id"]:
        abort(403)

    delete_expense(id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true", port=5001)
