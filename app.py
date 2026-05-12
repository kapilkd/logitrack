import math
import os
import re
from datetime import date, timedelta
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import (
    get_db, init_db, seed_db, get_user_by_email, create_user,
    create_expense, get_expense_by_id, update_expense, delete_expense,
    create_vendor, get_vendor_by_id as get_vendor_row, update_vendor,
    get_vendors_by_user, get_all_vendors, get_vendor_count,
    create_contact, get_contacts_by_vendor, get_contact_by_id,
    update_contact, delete_contact,
    SHIPMENT_STATUSES, INCOTERMS,
    create_shipment, get_shipment_by_id, get_shipments_by_user,
    update_shipment, update_shipment_status, get_shipment_by_number,
    get_expenses_by_shipment,
    RELATIONSHIP_TYPES, BILLING_TYPES, PAYMENT_STATUSES, CURRENCIES,
    create_shipment_vendor, get_shipment_vendor_by_id,
    get_vendors_by_shipment, update_shipment_vendor,
    delete_shipment_vendor as db_delete_shipment_vendor,
    get_shipment_vendor_count, get_total_payables_by_shipment,
    get_total_receivables_by_shipment,
)
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown, get_filtered_vendors, get_billing_stats, get_shipment_billing_list

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
    shipment_list = get_shipments_by_user(uid)
    active_rows, closed_rows = [], []
    for s in shipment_list:
        enriched = {
            **dict(s),
            "vendor_count": get_shipment_vendor_count(s["id"]),
            "total_payables": get_total_payables_by_shipment(s["id"]),
            "total_receivables": get_total_receivables_by_shipment(s["id"]),
        }
        (closed_rows if s["status"] == "CLOSED" else active_rows).append(enriched)
    return render_template("shipments.html", user=user,
        shipments=active_rows, closed_shipments=closed_rows,
        statuses=SHIPMENT_STATUSES)


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
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

    try:
        amount = float(amount_raw)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except ValueError:
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            today=date.today().isoformat(),
            error="Amount must be a positive number.",
            form=request.form,
        )

    if category not in EXPENSE_CATEGORIES:
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            today=date.today().isoformat(),
            error="Please select a valid category.",
            form=request.form,
        )

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_raw):
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            today=date.today().isoformat(),
            error="Please enter a valid date (YYYY-MM-DD).",
            form=request.form,
        )
    try:
        date.fromisoformat(date_raw)
    except ValueError:
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            today=date.today().isoformat(),
            error="Please enter a valid date.",
            form=request.form,
        )

    create_expense(session["user_id"], amount, category, date_raw, description or None)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:expense_id>/edit", methods=["POST"])
def edit_expense(expense_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(expense_id)
    if expense is None:
        abort(404)
    if expense["user_id"] != session["user_id"]:
        abort(403)

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    try:
        amount = float(amount_raw)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except ValueError:
        return redirect(url_for("profile"))

    if category not in EXPENSE_CATEGORIES:
        return redirect(url_for("profile"))

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_raw):
        return redirect(url_for("profile"))
    try:
        date.fromisoformat(date_raw)
    except ValueError:
        return redirect(url_for("profile"))

    update_expense(expense_id, amount, category, date_raw, description or None, expense["shipment_id"])
    return redirect(url_for("profile"))


@app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def delete_expense_route(expense_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    expense = get_expense_by_id(expense_id)
    if expense is None:
        abort(404)
    if expense["user_id"] != session["user_id"]:
        abort(403)

    delete_expense(expense_id)
    return jsonify({"ok": True})


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
    if vendor is None:
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


@app.route("/vendors/<int:vendor_id>/contacts")
def get_vendor_contacts(vendor_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    vendor = get_vendor_row(vendor_id)
    if vendor is None:
        abort(404)
    contacts = [dict(c) for c in get_contacts_by_vendor(vendor_id)]
    return jsonify(contacts)


@app.route("/vendors/<int:vendor_id>/info")
def vendor_info(vendor_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    vendor = get_vendor_row(vendor_id)
    if vendor is None:
        abort(404)
    return jsonify({
        "vendor_category": vendor["vendor_category"],
        "currency": vendor["currency"] or "INR",
    })


@app.route("/vendors/<int:vendor_id>/contacts/add", methods=["POST"])
def add_contact(vendor_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    vendor = get_vendor_row(vendor_id)
    if vendor is None:
        abort(404)
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("vendors"))

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    is_primary = 1 if request.form.get("is_primary") == "1" else 0
    create_contact(
        vendor_id=vendor_id, name=name, title=_f("title"),
        phone=_f("phone"), email=_f("email"),
        is_primary=is_primary, notes=_f("notes"),
    )
    return redirect(url_for("vendors"))


@app.route("/vendors/<int:vendor_id>/contacts/<int:contact_id>/edit", methods=["POST"])
def edit_contact(vendor_id, contact_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    vendor = get_vendor_row(vendor_id)
    if vendor is None:
        abort(404)
    contact = get_contact_by_id(contact_id)
    if contact is None or contact["vendor_id"] != vendor_id:
        abort(404)
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("vendors"))

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    is_primary = 1 if request.form.get("is_primary") == "1" else 0
    update_contact(
        contact_id=contact_id, vendor_id=vendor_id, name=name,
        title=_f("title"), phone=_f("phone"), email=_f("email"),
        is_primary=is_primary, notes=_f("notes"),
    )
    return redirect(url_for("vendors"))


@app.route("/vendors/<int:vendor_id>/contacts/<int:contact_id>/delete", methods=["POST"])
def delete_contact_route(vendor_id, contact_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    vendor = get_vendor_row(vendor_id)
    if vendor is None:
        abort(404)
    contact = get_contact_by_id(contact_id)
    if contact is None or contact["vendor_id"] != vendor_id:
        abort(404)
    delete_contact(contact_id)
    return jsonify({"ok": True})


@app.route("/vendors")
def vendors():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    filters = {
        "vendor_type":     request.args.get("vendor_type", ""),
        "vendor_category": request.args.get("vendor_category", ""),
        "vendor_status":   request.args.get("vendor_status", ""),
    }
    vendor_list = [dict(v) for v in get_filtered_vendors(
        vendor_type=filters["vendor_type"] or None,
        vendor_category=filters["vendor_category"] or None,
        vendor_status=filters["vendor_status"] or None,
    )]
    active_count = sum(1 for v in vendor_list if v["status"] == "ACTIVE")
    stats = {
        "total":    len(vendor_list),
        "active":   active_count,
        "inactive": len(vendor_list) - active_count,
    }
    all_vendors = [dict(v) for v in get_all_vendors()]
    return render_template(
        "vendors.html",
        user=user,
        vendors=vendor_list,
        stats=stats,
        filters=filters,
        next_vendor_code=_next_vendor_code(all_vendors),
    )


@app.route("/billing")
def billing():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    payment_status = request.args.get("payment_status", "").strip() or None
    billing_type   = request.args.get("billing_type",   "").strip() or None
    stats     = get_billing_stats(uid)
    shipments = get_shipment_billing_list(uid, payment_status=payment_status, billing_type=billing_type)
    filters   = {"payment_status": payment_status or "", "billing_type": billing_type or ""}
    return render_template(
        "billing.html",
        user=user,
        stats=stats,
        shipments=shipments,
        filters=filters,
        PAYMENT_STATUSES=PAYMENT_STATUSES,
        BILLING_TYPES=BILLING_TYPES,
    )


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
            "add_shipment.html",
            statuses=SHIPMENT_STATUSES,
            incoterms=INCOTERMS,
            today=date.today().isoformat(),
        )

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    shipment_number = _f("shipment_number")
    if not shipment_number:
        return render_template(
            "add_shipment.html",
            statuses=SHIPMENT_STATUSES,
            incoterms=INCOTERMS,
            today=date.today().isoformat(),
            error="Shipment number is required.",
            form=request.form,
        )

    if get_shipment_by_number(shipment_number):
        return render_template(
            "add_shipment.html",
            statuses=SHIPMENT_STATUSES,
            incoterms=INCOTERMS,
            today=date.today().isoformat(),
            error="A shipment with that number already exists.",
            form=request.form,
        )

    status = request.form.get("status", "DRAFT")
    if status not in SHIPMENT_STATUSES:
        status = "DRAFT"

    create_shipment(
        user_id=session["user_id"],
        shipment_number=shipment_number,
        origin=_f("origin"),
        destination=_f("destination"),
        carrier=_f("carrier"),
        status=status,
        shipment_date=_f("shipment_date"),
        etd=_f("etd"),
        eta=_f("eta"),
        port_of_loading=_f("port_of_loading"),
        port_of_discharge=_f("port_of_discharge"),
        incoterms=_f("incoterms"),
        description=_f("description"),
    )
    return redirect(url_for("shipments"))


@app.route("/shipments/<int:id>")
def shipment_detail(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    shipment = get_shipment_by_id(id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)

    expenses = get_expenses_by_shipment(id)
    vendors = get_vendors_by_shipment(id)
    all_vendors = [v for v in get_all_vendors() if v["status"] == "ACTIVE"]
    total_expenses = sum(e["amount"] for e in expenses)
    payables = get_total_payables_by_shipment(id)
    receivables = get_total_receivables_by_shipment(id)

    return render_template(
        "shipment_detail.html",
        shipment=shipment,
        expenses=expenses,
        vendors=vendors,
        all_vendors=all_vendors,
        total_expenses=total_expenses,
        payables=payables,
        receivables=receivables,
        categories=EXPENSE_CATEGORIES,
        relationship_types=RELATIONSHIP_TYPES,
        billing_types=BILLING_TYPES,
        payment_statuses=PAYMENT_STATUSES,
        currencies=CURRENCIES,
        today=date.today().isoformat(),
    )


@app.route("/shipments/<int:id>/edit", methods=["GET", "POST"])
def edit_shipment(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    shipment = get_shipment_by_id(id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)

    if request.method == "GET":
        return render_template(
            "edit_shipment.html",
            shipment=shipment,
            statuses=SHIPMENT_STATUSES,
            incoterms=INCOTERMS,
        )

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    shipment_number = _f("shipment_number")
    if not shipment_number:
        return render_template(
            "edit_shipment.html",
            shipment=shipment,
            statuses=SHIPMENT_STATUSES,
            incoterms=INCOTERMS,
            error="Shipment number is required.",
        )

    existing = get_shipment_by_number(shipment_number)
    if existing and existing["id"] != id:
        return render_template(
            "edit_shipment.html",
            shipment=shipment,
            statuses=SHIPMENT_STATUSES,
            incoterms=INCOTERMS,
            error="A shipment with that number already exists.",
        )

    status = request.form.get("status", shipment["status"])
    if status not in SHIPMENT_STATUSES:
        status = shipment["status"]

    update_shipment(
        shipment_id=id,
        shipment_number=shipment_number,
        origin=_f("origin"),
        destination=_f("destination"),
        carrier=_f("carrier"),
        status=status,
        shipment_date=_f("shipment_date"),
        etd=_f("etd"),
        eta=_f("eta"),
        port_of_loading=_f("port_of_loading"),
        port_of_discharge=_f("port_of_discharge"),
        incoterms=_f("incoterms"),
        description=_f("description"),
    )
    return redirect(url_for("shipment_detail", id=id))


@app.route("/shipments/<int:id>/status", methods=["POST"])
def update_shipment_status_route(id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    shipment = get_shipment_by_id(id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()
    if new_status not in SHIPMENT_STATUSES:
        return jsonify({"ok": False, "error": "Invalid status"}), 400
    update_shipment_status(id, new_status)
    return jsonify({"ok": True, "status": new_status})


@app.route("/shipments/<int:shipment_id>/expenses/add", methods=["POST"])
def add_shipment_expense(shipment_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    shipment = get_shipment_by_id(shipment_id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    try:
        amount = float(amount_raw)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except ValueError:
        return redirect(url_for("shipment_detail", id=shipment_id))

    if category not in EXPENSE_CATEGORIES:
        return redirect(url_for("shipment_detail", id=shipment_id))

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_raw):
        return redirect(url_for("shipment_detail", id=shipment_id))
    try:
        date.fromisoformat(date_raw)
    except ValueError:
        return redirect(url_for("shipment_detail", id=shipment_id))

    create_expense(session["user_id"], amount, category, date_raw, description or None, shipment_id)
    return redirect(url_for("shipment_detail", id=shipment_id))


@app.route("/shipments/<int:shipment_id>/expenses/<int:expense_id>/edit", methods=["POST"])
def edit_shipment_expense(shipment_id, expense_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    shipment = get_shipment_by_id(shipment_id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)

    expense = get_expense_by_id(expense_id)
    if expense is None or expense["shipment_id"] != shipment_id:
        abort(404)

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    try:
        amount = float(amount_raw)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except ValueError:
        return redirect(url_for("shipment_detail", id=shipment_id))

    if category not in EXPENSE_CATEGORIES:
        return redirect(url_for("shipment_detail", id=shipment_id))

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_raw):
        return redirect(url_for("shipment_detail", id=shipment_id))
    try:
        date.fromisoformat(date_raw)
    except ValueError:
        return redirect(url_for("shipment_detail", id=shipment_id))

    update_expense(expense_id, amount, category, date_raw, description or None, shipment_id)
    return redirect(url_for("shipment_detail", id=shipment_id))


@app.route("/shipments/<int:shipment_id>/expenses/<int:expense_id>/delete", methods=["POST"])
def delete_shipment_expense(shipment_id, expense_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    shipment = get_shipment_by_id(shipment_id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)

    expense = get_expense_by_id(expense_id)
    if expense is None or expense["shipment_id"] != shipment_id:
        abort(404)

    delete_expense(expense_id)
    return jsonify({"ok": True})


@app.route("/shipments/<int:shipment_id>/vendors/add", methods=["POST"])
def add_shipment_vendor(shipment_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    shipment = get_shipment_by_id(shipment_id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    def _num(key, cast, default):
        try:
            return cast(request.form.get(key, "").strip())
        except (ValueError, TypeError):
            return default

    vendor_id = _num("vendor_id", int, None)
    relationship_type = _f("relationship_type")
    billing_type = _f("billing_type")

    if not vendor_id or not relationship_type or billing_type not in BILLING_TYPES:
        return redirect(url_for("shipment_detail", id=shipment_id))

    payment_status = request.form.get("payment_status", "PENDING")
    if payment_status not in PAYMENT_STATUSES:
        payment_status = "PENDING"

    create_shipment_vendor(
        vendor_id=vendor_id,
        shipment_id=shipment_id,
        relationship_type=relationship_type,
        billing_type=billing_type,
        amount=_num("amount", float, 0.0),
        currency=request.form.get("currency", "INR") or "INR",
        invoice_number=_f("invoice_number"),
        invoice_date=_f("invoice_date"),
        due_date=_f("due_date"),
        payment_status=payment_status,
        notes=_f("notes"),
    )
    return redirect(url_for("shipment_detail", id=shipment_id))


@app.route("/shipments/<int:shipment_id>/vendors/<int:sv_id>/edit", methods=["POST"])
def edit_shipment_vendor(shipment_id, sv_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    shipment = get_shipment_by_id(shipment_id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)

    sv = get_shipment_vendor_by_id(sv_id)
    if sv is None or sv["shipment_id"] != shipment_id:
        abort(404)

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    def _num(key, cast, default):
        try:
            return cast(request.form.get(key, "").strip())
        except (ValueError, TypeError):
            return default

    relationship_type = _f("relationship_type")
    billing_type = _f("billing_type")
    if not relationship_type or billing_type not in BILLING_TYPES:
        return redirect(url_for("shipment_detail", id=shipment_id))

    payment_status = request.form.get("payment_status", "PENDING")
    if payment_status not in PAYMENT_STATUSES:
        payment_status = "PENDING"

    update_shipment_vendor(
        sv_id=sv_id,
        relationship_type=relationship_type,
        billing_type=billing_type,
        amount=_num("amount", float, 0.0),
        currency=request.form.get("currency", "INR") or "INR",
        invoice_number=_f("invoice_number"),
        invoice_date=_f("invoice_date"),
        due_date=_f("due_date"),
        payment_status=payment_status,
        notes=_f("notes"),
    )
    return redirect(url_for("shipment_detail", id=shipment_id))


@app.route("/shipments/<int:shipment_id>/vendors/<int:sv_id>/delete", methods=["POST"])
def delete_shipment_vendor_route(shipment_id, sv_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    shipment = get_shipment_by_id(shipment_id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)

    sv = get_shipment_vendor_by_id(sv_id)
    if sv is None or sv["shipment_id"] != shipment_id:
        abort(404)

    db_delete_shipment_vendor(sv_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true", port=5001)
