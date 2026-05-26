import math
import os
import re

# Load .env file using stdlib — no python-dotenv needed
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _k = _k.strip()
                _v = _v.strip().strip('"').strip("'")
                os.environ.setdefault(_k, _v)
import secrets
from datetime import date, datetime, timedelta
from flask import Flask, abort, flash, get_flashed_messages, jsonify, redirect, render_template, request, session, url_for
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
    create_sv_payment, get_payments_by_sv, get_sv_payment_by_id,
    delete_sv_payment, get_payments_by_shipment,
    log_alert,
    get_company_profile, upsert_company_profile,
    get_all_contact_emails_by_user,
    upsert_gmail_account, get_gmail_account, delete_gmail_account,
    save_email, get_emails_by_user, get_email_by_id, delete_email,
    get_emails_by_thread, upsert_ai_processing, get_ai_processing,
    get_user_by_id as get_user_row_by_id, update_user_profile, update_user_password,
    create_enquiry, get_enquiries_by_user, get_enquiry_count,
    get_enquiry_by_id, update_enquiry,
    get_particular_types, ensure_particular_type,
    get_particulars_by_enquiry, create_enquiry_particular, delete_enquiry_particular,
    generate_customer_vendor_code,
    ENQUIRY_STATUSES, ENQUIRY_PRIORITIES, WEIGHT_UNITS, CONSIGNMENT_TYPES,
)
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown, get_filtered_vendors, get_billing_stats, get_shipment_billing_list, get_recent_alerts, get_shipment_bill_vendors, get_emails_with_shipment_links, get_vendor_ledger, get_vendor_ledger_stats, get_shipment_report_rows, get_report_summary_stats, get_expense_link_summary, get_monthly_expense_trend, get_vendor_report_rows, get_vendor_report_summary
from gmail_utils import (
    GMAIL_AVAILABLE, SCOPES, credentials_file_exists,
    encrypt_token, decrypt_token, sync_inbox, send_gmail, parse_message,
)
from ai_utils import ANTHROPIC_AVAILABLE, process_email_with_claude, generate_reply_with_claude
from forex_utils import FOREX_AVAILABLE, fetch_hdfc_usd_tt_selling_rate

_IS_PRODUCTION = os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("PRODUCTION")

# Allow OAuth over plain HTTP only in local development
if not _IS_PRODUCTION:
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = bool(_IS_PRODUCTION)

_LOGO_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads", "logos")
os.makedirs(_LOGO_UPLOAD_FOLDER, exist_ok=True)
_ALLOWED_LOGO_EXT = {"png", "jpg", "jpeg", "gif", "webp", "svg"}

with app.app_context():
    init_db()
    if not _IS_PRODUCTION:
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
        active_section="overview",
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
        statuses=SHIPMENT_STATUSES, active_section="shipments")


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
        log_alert(
            user_id=uid,
            entity_type="VENDOR",
            entity_id=None,
            entity_label=vendor_name,
            action="CREATED",
            description=f"Vendor '{vendor_name}' created",
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
    if vendor["user_id"] != uid:
        abort(403)

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
    log_alert(
        user_id=uid,
        entity_type="VENDOR",
        entity_id=vendor_id,
        entity_label=vendor_name,
        action="UPDATED",
        description=f"Vendor '{vendor_name}' updated",
    )
    return redirect(url_for("vendors"))


@app.route("/vendors/<int:vendor_id>/contacts")
def get_vendor_contacts(vendor_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    vendor = get_vendor_row(vendor_id)
    if vendor is None:
        abort(404)
    if vendor["user_id"] != session["user_id"]:
        abort(403)
    contacts = [dict(c) for c in get_contacts_by_vendor(vendor_id)]
    return jsonify(contacts)


@app.route("/vendors/<int:vendor_id>/info")
def vendor_info(vendor_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    vendor = get_vendor_row(vendor_id)
    if vendor is None:
        abort(404)
    if vendor["user_id"] != session["user_id"]:
        abort(403)
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
    if vendor["user_id"] != session["user_id"]:
        abort(403)
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
    if vendor["user_id"] != session["user_id"]:
        abort(403)
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
    if vendor["user_id"] != session["user_id"]:
        abort(403)
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
        user_id=uid,
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
    all_vendors = [dict(v) for v in get_all_vendors(user_id=uid)]
    return render_template(
        "vendors.html",
        user=user,
        vendors=vendor_list,
        stats=stats,
        filters=filters,
        next_vendor_code=_next_vendor_code(all_vendors),
        active_section="vendors",
    )


@app.route("/vendors/<int:vendor_id>/ledger")
def vendor_ledger(vendor_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    vendor = get_vendor_row(vendor_id)
    if vendor is None:
        abort(404)
    if vendor["user_id"] != session["user_id"]:
        abort(403)
    user    = get_user_by_id(session["user_id"])
    entries = get_vendor_ledger(vendor_id)
    stats   = get_vendor_ledger_stats(vendor_id)
    return render_template(
        "vendor_ledger.html",
        user=user,
        vendor=dict(vendor),
        entries=entries,
        stats=stats,
        PAYMENT_STATUSES=PAYMENT_STATUSES,
        BILLING_TYPES=BILLING_TYPES,
        active_section="vendors",
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
        active_section="billing",
    )


@app.route("/shipments/<int:id>/bill/print")
def shipment_bill_print(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    shipment = get_shipment_by_id(id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != uid:
        abort(403)
    vendors = get_shipment_bill_vendors(id)
    company = get_company_profile(uid)
    user = get_user_by_id(uid)
    total_payable = get_total_payables_by_shipment(id)
    total_receivable = get_total_receivables_by_shipment(id)
    return render_template(
        "bill_print.html",
        shipment=shipment,
        vendors=vendors,
        company=company,
        user=user,
        total_payable=total_payable,
        total_receivable=total_receivable,
        today=date.today().isoformat(),
    )


@app.route("/enquiries")
def enquiries():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    enquiry_list = get_enquiries_by_user(uid)
    active_rows = [e for e in enquiry_list if e["status"] not in ("CONVERTED", "CLOSED")]
    closed_rows = [e for e in enquiry_list if e["status"] in ("CONVERTED", "CLOSED")]
    return render_template("enquiries.html",
        user=user,
        enquiries=active_rows,
        closed_enquiries=closed_rows,
        statuses=ENQUIRY_STATUSES,
        priorities=ENQUIRY_PRIORITIES,
        active_section="enquiries",
    )


@app.route("/enquiries/add", methods=["GET", "POST"])
def add_enquiry():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    ctx = dict(
        user=user,
        statuses=ENQUIRY_STATUSES,
        priorities=ENQUIRY_PRIORITIES,
        weight_units=WEIGHT_UNITS,
        consignment_types=CONSIGNMENT_TYPES,
        incoterms=INCOTERMS,
        currencies=CURRENCIES,
        today=date.today().isoformat(),
        forex_available=FOREX_AVAILABLE,
        active_section="enquiries",
    )

    if request.method == "GET":
        return render_template("add_enquiry.html", **ctx)

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    enquiry_date = _f("enquiry_date")
    if not enquiry_date:
        ctx.update(error="Enquiry date is required.", form=request.form)
        return render_template("add_enquiry.html", **ctx)

    status = request.form.get("status", "OPEN")
    if status not in ENQUIRY_STATUSES:
        status = "OPEN"
    priority = request.form.get("priority", "NORMAL")
    if priority not in ENQUIRY_PRIORITIES:
        priority = "NORMAL"

    data = {
        "customer_name":    _f("customer_name"),
        "customer_email":   _f("customer_email"),
        "customer_phone":   _f("customer_phone"),
        "commodity":        _f("commodity"),
        "consignment_type": _f("consignment_type"),
        "shipment_terms":   _f("shipment_terms"),
        "weight":           request.form.get("weight") or 0,
        "weight_unit":      request.form.get("weight_unit") or "KGS",
        "packages":         request.form.get("packages") or 0,
        "mawb":             _f("mawb"),
        "hawb":             _f("hawb"),
        "origin":           _f("origin"),
        "destination":      _f("destination"),
        "ex_rate":          request.form.get("ex_rate") or 0,
        "incoterms":        _f("incoterms"),
        "currency":         request.form.get("currency") or "INR",
        "estimated_value":  request.form.get("estimated_value") or 0,
        "status":           status,
        "priority":         priority,
        "enquiry_date":     enquiry_date,
        "follow_up_date":   _f("follow_up_date"),
        "notes":            _f("notes"),
    }

    new_enq = create_enquiry(uid, data)
    log_alert(
        user_id=uid,
        entity_type="ENQUIRY",
        entity_id=new_enq["id"] if new_enq else None,
        entity_label=new_enq["enquiry_number"] if new_enq else None,
        action="CREATED",
        description=f"Enquiry {new_enq['enquiry_number']} created" if new_enq else "Enquiry created",
    )
    return redirect(url_for("enquiries"))


@app.route("/enquiries/forex-rate")
def enquiry_forex_rate():
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    rate = fetch_hdfc_usd_tt_selling_rate()
    if rate is not None:
        return jsonify({"ok": True, "rate": rate})
    return jsonify({"ok": False, "error": "HDFC rate not available. Please enter manually."}), 502


@app.route("/enquiries/<int:enquiry_id>/edit", methods=["GET", "POST"])
def edit_enquiry(enquiry_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    enq = get_enquiry_by_id(enquiry_id)
    if enq is None:
        abort(404)
    if enq["user_id"] != uid:
        abort(403)

    ctx = dict(
        user=user,
        enq=enq,
        statuses=ENQUIRY_STATUSES,
        priorities=ENQUIRY_PRIORITIES,
        weight_units=WEIGHT_UNITS,
        consignment_types=CONSIGNMENT_TYPES,
        incoterms=INCOTERMS,
        currencies=CURRENCIES,
        forex_available=FOREX_AVAILABLE,
        active_section="enquiries",
    )

    if request.method == "GET":
        return render_template("edit_enquiry.html", **ctx)

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    enquiry_date = _f("enquiry_date")
    if not enquiry_date:
        ctx.update(error="Enquiry date is required.", form=request.form)
        return render_template("edit_enquiry.html", **ctx)

    status = request.form.get("status", "OPEN")
    if status not in ENQUIRY_STATUSES:
        status = "OPEN"
    priority = request.form.get("priority", "NORMAL")
    if priority not in ENQUIRY_PRIORITIES:
        priority = "NORMAL"

    data = {
        "customer_name":    _f("customer_name"),
        "customer_email":   _f("customer_email"),
        "customer_phone":   _f("customer_phone"),
        "commodity":        _f("commodity"),
        "consignment_type": _f("consignment_type"),
        "shipment_terms":   _f("shipment_terms"),
        "weight":           request.form.get("weight") or 0,
        "weight_unit":      request.form.get("weight_unit", "KGS"),
        "packages":         request.form.get("packages") or 0,
        "mawb":             _f("mawb"),
        "hawb":             _f("hawb"),
        "origin":           _f("origin"),
        "destination":      _f("destination"),
        "ex_rate":          request.form.get("ex_rate") or 0,
        "incoterms":        _f("incoterms"),
        "currency":         request.form.get("currency", "INR"),
        "estimated_value":  request.form.get("estimated_value") or 0,
        "status":           status,
        "priority":         priority,
        "enquiry_date":     enquiry_date,
        "follow_up_date":   _f("follow_up_date"),
        "notes":            _f("notes"),
    }

    update_enquiry(enquiry_id, data)
    log_alert(
        user_id=uid,
        entity_type="ENQUIRY",
        entity_id=enquiry_id,
        entity_label=enq["enquiry_number"],
        action="UPDATED",
        description=f"Enquiry {enq['enquiry_number']} updated",
    )
    return redirect(url_for("enquiries"))


@app.route("/enquiries/<int:enquiry_id>/particulars")
def enquiry_particulars(enquiry_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    enq = get_enquiry_by_id(enquiry_id)
    if enq is None:
        abort(404)
    if enq["user_id"] != uid:
        abort(403)
    particulars = get_particulars_by_enquiry(enquiry_id)
    types_list = get_particular_types(uid)
    return render_template("enquiry_particulars.html",
        user=user,
        enq=enq,
        particulars=particulars,
        types_list=types_list,
        active_section="enquiries",
    )


@app.route("/enquiries/<int:enquiry_id>/particulars/add", methods=["POST"])
def add_enquiry_particular(enquiry_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    enq = get_enquiry_by_id(enquiry_id)
    if enq is None:
        abort(404)
    if enq["user_id"] != uid:
        abort(403)

    particular_type = request.form.get("particular_type", "").strip()
    custom_label = request.form.get("custom_label", "").strip()
    if particular_type == "Other" and custom_label:
        ensure_particular_type(uid, custom_label)
        particular_type = custom_label
    if not particular_type:
        return redirect(url_for("enquiry_particulars", enquiry_id=enquiry_id))

    use_formula = request.form.get("use_formula") == "1"
    data = {
        "particular_type": particular_type,
        "sac_hsn":         request.form.get("sac_hsn", "").strip() or None,
        "qty":             request.form.get("qty") or 1,
        "ex_rate":         enq["ex_rate"],
        "weight":          enq["weight"],
        "weight_unit":     enq["weight_unit"],
        "offered_rate":    request.form.get("offered_rate") or 0,
        "use_formula":     use_formula,
        "expense":         request.form.get("expense") or 0,
        "tax_rate":        request.form.get("tax_rate") or 0,
        "cgst":            request.form.get("cgst") or 0,
        "sgst":            request.form.get("sgst") or 0,
        "igst":            request.form.get("igst") or 0,
        "total":           request.form.get("total") or 0,
        "currency":        "INR",
    }
    create_enquiry_particular(enquiry_id, uid, data)
    return redirect(url_for("enquiry_particulars", enquiry_id=enquiry_id))


@app.route("/enquiries/<int:enquiry_id>/particulars/<int:particular_id>/delete", methods=["POST"])
def delete_enquiry_particular_route(enquiry_id, particular_id):
    if not session.get("user_id"):
        return jsonify({"ok": False}), 401
    uid = session["user_id"]
    enq = get_enquiry_by_id(enquiry_id)
    if enq is None or enq["user_id"] != uid:
        return jsonify({"ok": False}), 403
    delete_enquiry_particular(particular_id)
    return jsonify({"ok": True})


@app.route("/emails")
def emails():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    gmail_account = get_gmail_account(uid)
    email_list = get_emails_with_shipment_links(uid) if gmail_account else []
    contact_emails = get_all_contact_emails_by_user(uid)
    flashes = get_flashed_messages(with_categories=True)

    from collections import OrderedDict
    thread_map = OrderedDict()
    for em in email_list:
        key = em['gmail_thread_id'] or f"subj:{em['subject'] or ''}"
        thread_map.setdefault(key, []).append(em)
    thread_groups = [
        {'latest': msgs[0], 'extras': msgs[1:]}
        for msgs in thread_map.values()
    ]

    return render_template(
        "emails.html",
        user=user,
        gmail_account=gmail_account,
        email_list=email_list,
        thread_groups=thread_groups,
        contact_emails=contact_emails,
        flashes=flashes,
        active_section="emails",
    )


@app.route("/emails/sync")
def emails_sync():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    account = get_gmail_account(uid)
    if not account:
        flash("Connect your Gmail account first.", "error")
        return redirect(url_for("emails"))
    try:
        count = sync_inbox(uid, account)
        flash(f"Synced {count} new email(s).", "success")
    except Exception as exc:
        flash(f"Sync failed: {exc}", "error")
    return redirect(url_for("emails"))


@app.route("/emails/send", methods=["POST"])
def emails_send():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    account = get_gmail_account(uid)
    if not account:
        flash("Connect your Gmail account first.", "error")
        return redirect(url_for("emails"))

    to = request.form.get("to", "").strip()
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()
    reply_thread_id = request.form.get("reply_thread_id") or None
    cc  = request.form.get("cc",  "").strip() or None
    bcc = request.form.get("bcc", "").strip() or None

    if not to or not subject or not body:
        flash("To, Subject, and Body are all required.", "error")
        return redirect(url_for("emails"))

    try:
        sent = send_gmail(account, to=to, subject=subject, body=body,
                          reply_to_thread_id=reply_thread_id, cc=cc, bcc=bcc)
        now = datetime.utcnow().isoformat()
        save_email(
            user_id=uid,
            gmail_message_id=sent.get("id", f"sent-{secrets.token_hex(8)}"),
            gmail_thread_id=sent.get("threadId"),
            direction="OUTBOUND",
            from_email=account["gmail_email"],
            to_email=to,
            cc=cc,
            subject=subject,
            body_plain=body,
            status="SENT",
            sent_at=now,
        )
        log_alert(uid, "EMAIL", None, subject, "SENT", f"Email sent to {to}")
        flash(f"Email sent to {to}.", "success")
    except Exception as exc:
        flash(f"Failed to send email: {exc}", "error")
    return redirect(url_for("emails"))


@app.route("/emails/<int:email_id>")
def email_detail(email_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    email = get_email_by_id(email_id)
    if email is None:
        abort(404)
    if email["user_id"] != uid:
        abort(403)
    ai_result = get_ai_processing(email_id)
    thread = []
    if email["gmail_thread_id"]:
        thread = get_emails_by_thread(email["gmail_thread_id"], uid)
    account = get_gmail_account(uid)
    flashes = get_flashed_messages(with_categories=True)
    return render_template(
        "email_detail.html",
        user=user,
        email=email,
        ai_result=ai_result,
        thread=thread,
        gmail_account=account,
        flashes=flashes,
        active_section="emails",
    )


@app.route("/emails/<int:email_id>/process", methods=["POST"])
def email_process(email_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    uid = session["user_id"]
    email = get_email_by_id(email_id)
    if email is None:
        return jsonify({"ok": False, "error": "Not found"}), 404
    if email["user_id"] != uid:
        return jsonify({"ok": False, "error": "Forbidden"}), 403
    if not ANTHROPIC_AVAILABLE:
        return jsonify({"ok": False, "error": "Anthropic package not installed"}), 500

    result = process_email_with_claude(email)
    if result.get("processing_status") == "FAILED":
        upsert_ai_processing(email_id, processing_status="FAILED")
        return jsonify({"ok": False, "error": result.get("error", "Processing failed")}), 500

    upsert_ai_processing(
        email_id=email_id,
        ai_summary=result.get("summary"),
        detected_category=result.get("detected_category"),
        extracted_entities=result.get("extracted_entities"),
        shipment_reference=result.get("shipment_reference"),
        invoice_reference=result.get("invoice_reference"),
        processing_status="DONE",
    )
    return jsonify({
        "ok": True,
        "summary": result.get("summary"),
        "detected_category": result.get("detected_category"),
        "extracted_entities": result.get("extracted_entities"),
        "shipment_reference": result.get("shipment_reference"),
        "invoice_reference": result.get("invoice_reference"),
    })


@app.route("/emails/<int:email_id>/auto-reply", methods=["POST"])
def email_auto_reply(email_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    uid = session["user_id"]
    email = get_email_by_id(email_id)
    if email is None:
        return jsonify({"ok": False, "error": "Not found"}), 404
    if email["user_id"] != uid:
        return jsonify({"ok": False, "error": "Forbidden"}), 403
    if not ANTHROPIC_AVAILABLE:
        return jsonify({"ok": False, "error": "Anthropic package not installed"}), 500

    tone = request.form.get("tone", "professional")
    thread = [email]
    if email["gmail_thread_id"]:
        thread = get_emails_by_thread(email["gmail_thread_id"], uid) or [email]

    try:
        reply_text = generate_reply_with_claude(list(reversed(thread)), tone=tone)
        return jsonify({"ok": True, "reply_text": reply_text})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/emails/<int:email_id>/delete", methods=["POST"])
def email_delete(email_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    uid = session["user_id"]
    email = get_email_by_id(email_id)
    if email is None:
        return jsonify({"ok": False, "error": "Not found"}), 404
    if email["user_id"] != uid:
        return jsonify({"ok": False, "error": "Forbidden"}), 403
    if email["direction"] != "INBOUND":
        return jsonify({"ok": False, "error": "Only received emails can be deleted"}), 400
    subject = email["subject"] or "(no subject)"
    delete_email(email_id)
    log_alert(uid, "email", email_id, subject, "deleted")
    return jsonify({"ok": True})


# ------------------------------------------------------------------ #
# Gmail OAuth routes                                                  #
# ------------------------------------------------------------------ #

@app.route("/settings/gmail")
def gmail_settings():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    account = get_gmail_account(uid)
    has_creds_file = credentials_file_exists()
    has_token_key = bool(os.environ.get("GMAIL_TOKEN_KEY", "").strip())
    flashes = get_flashed_messages(with_categories=True)
    return render_template(
        "settings_gmail.html",
        user=user,
        account=account,
        has_creds_file=has_creds_file,
        has_token_key=has_token_key,
        flashes=flashes,
        active_section="settings",
    )


@app.route("/auth/gmail/connect")
def gmail_connect():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    if not credentials_file_exists():
        flash("credentials.json not found. Download it from Google Cloud Console.", "error")
        return redirect(url_for("gmail_settings"))
    if not os.environ.get("GMAIL_TOKEN_KEY", "").strip():
        flash("GMAIL_TOKEN_KEY environment variable is not set.", "error")
        return redirect(url_for("gmail_settings"))

    try:
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_secrets_file(
            "credentials.json",
            scopes=SCOPES,
            redirect_uri=url_for("gmail_callback", _external=True),
        )
        state = secrets.token_urlsafe(32)
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            state=state,
            prompt="select_account consent",
        )
        resp = redirect(auth_url)
        resp.set_cookie("oauth_state", state, httponly=True, samesite="Lax", max_age=600)
        return resp
    except Exception as exc:
        flash(f"OAuth error: {exc}", "error")
        return redirect(url_for("gmail_settings"))


@app.route("/auth/gmail/callback")
def gmail_callback():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    stored_state = request.cookies.get("oauth_state")
    incoming_state = request.args.get("state")
    if not stored_state or stored_state != incoming_state:
        flash("OAuth state mismatch. Please try connecting again.", "error")
        return redirect(url_for("gmail_settings"))

    error = request.args.get("error")
    if error:
        flash(f"Google denied access: {error}", "error")
        return redirect(url_for("gmail_settings"))

    try:
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_secrets_file(
            "credentials.json",
            scopes=SCOPES,
            state=stored_state,
            redirect_uri=url_for("gmail_callback", _external=True),
        )
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials

        uid = session["user_id"]
        gmail_email = None
        try:
            from googleapiclient.discovery import build as _build
            svc = _build("oauth2", "v2", credentials=creds)
            info = svc.userinfo().get().execute()
            gmail_email = info.get("email")
        except Exception:
            gmail_email = creds.client_id  # fallback

        upsert_gmail_account(
            user_id=uid,
            gmail_email=gmail_email or "",
            google_account_id=gmail_email,
            access_token_enc=encrypt_token(creds.token),
            refresh_token_enc=encrypt_token(creds.refresh_token or ""),
            token_expiry=creds.expiry.isoformat() if creds.expiry else None,
            scope=" ".join(creds.scopes) if creds.scopes else None,
        )
        log_alert(uid, "GMAIL", None, gmail_email, "CONNECTED",
                  f"Gmail account {gmail_email} connected")
        flash(f"Gmail account {gmail_email} connected successfully.", "success")
    except Exception as exc:
        flash(f"Failed to complete OAuth: {exc}", "error")

    resp = redirect(url_for("gmail_settings"))
    resp.delete_cookie("oauth_state")
    return resp


@app.route("/auth/gmail/disconnect", methods=["POST"])
def gmail_disconnect():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    account = get_gmail_account(uid)
    if account:
        try:
            import urllib.request
            token = decrypt_token(account["access_token"])
            url = f"https://oauth2.googleapis.com/revoke?token={token}"
            urllib.request.urlopen(url)
        except Exception:
            pass
        gmail_email = account["gmail_email"]
        delete_gmail_account(uid)
        log_alert(uid, "GMAIL", None, gmail_email, "DISCONNECTED",
                  f"Gmail account {gmail_email} disconnected")
        flash("Gmail account disconnected.", "success")
    return redirect(url_for("gmail_settings"))


@app.route("/notifications")
def notifications():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    alerts = get_recent_alerts(uid)
    return render_template("notifications.html", user=user, alerts=alerts, active_section="notifications")


@app.route("/reports")
def reports():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    status    = request.args.get("status",    "").strip() or None
    from_date = request.args.get("from_date", "").strip() or None
    to_date   = request.args.get("to_date",   "").strip() or None

    stats     = get_report_summary_stats(uid, status=status, from_date=from_date, to_date=to_date)
    shipments = get_shipment_report_rows(uid, status=status, from_date=from_date, to_date=to_date)
    filters   = {"status": status or "", "from_date": from_date or "", "to_date": to_date or ""}

    return render_template(
        "reports.html",
        user=user,
        stats=stats,
        shipments=shipments,
        filters=filters,
        SHIPMENT_STATUSES=SHIPMENT_STATUSES,
        active_section="reports",
    )


@app.route("/reports/financial")
def financial_reports():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    from_date = request.args.get("from_date", "").strip() or None
    to_date   = request.args.get("to_date",   "").strip() or None

    today            = date.today()
    first_this_month = today.replace(day=1)
    last_month_end   = first_this_month - timedelta(days=1)
    first_last_month = last_month_end.replace(day=1)
    last_3m_start    = today - timedelta(days=89)

    presets = {
        "this_month":    (first_this_month.isoformat(), today.isoformat()),
        "last_month":    (first_last_month.isoformat(), last_month_end.isoformat()),
        "last_3_months": (last_3m_start.isoformat(),   today.isoformat()),
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

    link_summary  = get_expense_link_summary(uid, from_date=from_date, to_date=to_date)
    categories    = get_category_breakdown(uid, from_date=from_date, to_date=to_date)
    monthly_trend = get_monthly_expense_trend(uid, from_date=from_date, to_date=to_date)

    return render_template(
        "financial_reports.html",
        user=user,
        link_summary=link_summary,
        categories=categories,
        monthly_trend=monthly_trend,
        presets=presets,
        active_preset=active_preset,
        from_date=from_date or "",
        to_date=to_date or "",
        active_section="reports",
    )


@app.route("/reports/vendors")
def vendor_reports():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    vendor_type     = request.args.get("vendor_type",     "").strip() or None
    vendor_category = request.args.get("vendor_category", "").strip() or None
    vendor_status   = request.args.get("vendor_status",   "").strip() or None
    from_date       = request.args.get("from_date",       "").strip() or None
    to_date         = request.args.get("to_date",         "").strip() or None

    summary = get_vendor_report_summary(
        uid,
        vendor_type=vendor_type, vendor_category=vendor_category,
        vendor_status=vendor_status, from_date=from_date, to_date=to_date,
    )
    vendors = get_vendor_report_rows(
        uid,
        vendor_type=vendor_type, vendor_category=vendor_category,
        vendor_status=vendor_status, from_date=from_date, to_date=to_date,
    )

    return render_template(
        "vendor_reports.html",
        user=user,
        summary=summary,
        vendors=vendors,
        vendor_type=vendor_type or "",
        vendor_category=vendor_category or "",
        vendor_status=vendor_status or "",
        from_date=from_date or "",
        to_date=to_date or "",
        VENDOR_TYPES=["INBOUND", "OUTBOUND"],
        VENDOR_CATEGORIES=[
            "AIR_CARRIER", "BILLING_PARTNER", "CONSIGNEE", "COURIER_PARTNER",
            "CUSTOM_CLEARANCE_AGENT", "CUSTOMER", "FREIGHT_FORWARDER",
            "INSURANCE_PROVIDER", "LOCAL_TRANSPORT", "OTHER", "PACKAGING_VENDOR",
            "PORT_AGENT", "SHIPPER", "SHIPPING_LINE", "TRANSPORTER", "WAREHOUSE",
        ],
        VENDOR_STATUSES=["ACTIVE", "INACTIVE", "BLOCKED"],
        active_section="reports",
    )


@app.route("/settings")
def settings():
    return redirect(url_for("settings_company_profile"))


@app.route("/settings/company-profile", methods=["GET", "POST"])
def settings_company_profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "GET":
        profile = get_company_profile(uid)
        return render_template(
            "settings_company_profile.html",
            user=user,
            profile=profile,
            currencies=CURRENCIES,
            incoterms=INCOTERMS,
            active_section="settings",
        )

    def _f(key):
        v = request.form.get(key, "").strip()
        return v or None

    company_name = (request.form.get("company_name") or "").strip()
    if not company_name:
        return render_template(
            "settings_company_profile.html",
            user=user,
            profile=get_company_profile(uid),
            currencies=CURRENCIES,
            incoterms=INCOTERMS,
            active_section="settings",
            error="Company name is required.",
            form=request.form,
        )

    # Handle logo upload — keep existing path when no new file is submitted
    existing_profile = get_company_profile(uid)
    logo_path = existing_profile["logo_path"] if existing_profile else None
    logo_file = request.files.get("company_logo")
    if logo_file and logo_file.filename:
        ext = logo_file.filename.rsplit(".", 1)[-1].lower() if "." in logo_file.filename else ""
        if ext not in _ALLOWED_LOGO_EXT:
            return render_template(
                "settings_company_profile.html",
                user=user,
                profile=existing_profile,
                currencies=CURRENCIES,
                incoterms=INCOTERMS,
                active_section="settings",
                error="Logo must be a PNG, JPG, GIF, WebP, or SVG file.",
                form=request.form,
            )
        filename = f"logo_{uid}.{ext}"
        logo_file.save(os.path.join(_LOGO_UPLOAD_FOLDER, filename))
        logo_path = f"uploads/logos/{filename}"

    upsert_company_profile(
        user_id=uid,
        company_name=company_name,
        legal_name=_f("legal_name"),
        industry=_f("industry"),
        website=_f("website"),
        email=_f("email"),
        phone=_f("phone"),
        address_line1=_f("address_line1"),
        address_line2=_f("address_line2"),
        city=_f("city"),
        state=_f("state"),
        country=_f("country"),
        pincode=_f("pincode"),
        gst_number=_f("gst_number"),
        pan_number=_f("pan_number"),
        iec_code=_f("iec_code"),
        currency=request.form.get("currency", "INR"),
        incoterms=_f("incoterms"),
        logo_path=logo_path,
        billing_terms=_f("billing_terms"),
    )
    log_alert(
        user_id=uid,
        entity_type="COMPANY_PROFILE",
        entity_id=uid,
        entity_label=company_name,
        action="UPDATED",
        description=f"Company profile updated for '{company_name}'",
    )
    return render_template(
        "settings_company_profile.html",
        user=user,
        profile=get_company_profile(uid),
        currencies=CURRENCIES,
        incoterms=INCOTERMS,
        active_section="settings",
        success="Company profile saved.",
    )


@app.route("/settings/user-management")
def user_management_settings():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    raw_user = get_user_row_by_id(uid)
    try:
        ca = raw_user["created_at"]
        joined = ca.strftime("%B %d, %Y") if hasattr(ca, "strftime") else datetime.strptime(str(ca)[:10], "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        joined = str(raw_user["created_at"])
    return render_template(
        "settings_user_management.html",
        user=user, raw_user=raw_user, joined=joined,
        active_section="settings",
    )


@app.route("/settings/user-management/profile", methods=["POST"])
def user_management_update_profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    raw_user = get_user_row_by_id(uid)
    try:
        ca = raw_user["created_at"]
        joined = ca.strftime("%B %d, %Y") if hasattr(ca, "strftime") else datetime.strptime(str(ca)[:10], "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        joined = str(raw_user["created_at"])

    name  = request.form.get("name",  "").strip()
    email = request.form.get("email", "").strip()

    def _render(error=None, success=None):
        return render_template(
            "settings_user_management.html",
            user=user, raw_user=raw_user, joined=joined,
            active_section="settings",
            profile_error=error, profile_success=success,
        )

    if not name:
        return _render(error="Display name is required.")
    if not email:
        return _render(error="Email address is required.")
    existing = get_user_by_email(email)
    if existing and existing["id"] != uid:
        return _render(error="That email address is already in use by another account.")

    update_user_profile(uid, name, email)
    session["user_name"] = name
    log_alert(user_id=uid, entity_type="USER", entity_id=uid, entity_label=name,
              action="UPDATED", description=f"User profile updated: name='{name}', email='{email}'")
    raw_user = get_user_row_by_id(uid)
    user = get_user_by_id(uid)
    return _render(success="Profile updated successfully.")


@app.route("/settings/user-management/password", methods=["POST"])
def user_management_update_password():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    raw_user = get_user_row_by_id(uid)
    try:
        ca = raw_user["created_at"]
        joined = ca.strftime("%B %d, %Y") if hasattr(ca, "strftime") else datetime.strptime(str(ca)[:10], "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        joined = str(raw_user["created_at"])

    current_password = request.form.get("current_password", "")
    new_password     = request.form.get("new_password",     "")
    confirm_password = request.form.get("confirm_password", "")

    def _render(error=None, success=None):
        return render_template(
            "settings_user_management.html",
            user=user, raw_user=raw_user, joined=joined,
            active_section="settings",
            password_error=error, password_success=success,
        )

    if not check_password_hash(raw_user["password_hash"], current_password):
        return _render(error="Current password is incorrect.")
    if len(new_password) < 8:
        return _render(error="New password must be at least 8 characters.")
    if new_password != confirm_password:
        return _render(error="New password and confirmation do not match.")

    update_user_password(uid, generate_password_hash(new_password))
    log_alert(user_id=uid, entity_type="USER", entity_id=uid, entity_label=user["name"],
              action="UPDATED", description="User password changed")
    return _render(success="Password changed successfully.")


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
            active_section="shipments",
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
            active_section="shipments",
        )

    if get_shipment_by_number(shipment_number):
        return render_template(
            "add_shipment.html",
            statuses=SHIPMENT_STATUSES,
            incoterms=INCOTERMS,
            today=date.today().isoformat(),
            error="A shipment with that number already exists.",
            form=request.form,
            active_section="shipments",
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
    _new_ship = get_shipment_by_number(shipment_number)
    log_alert(
        user_id=session["user_id"],
        entity_type="SHIPMENT",
        entity_id=_new_ship["id"] if _new_ship else None,
        entity_label=shipment_number,
        action="CREATED",
        description=f"Shipment {shipment_number} created",
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
    sv_list = get_vendors_by_shipment(id)
    payments_map = get_payments_by_shipment(id)

    payable_vendors    = [dict(v) for v in sv_list if v["billing_type"] == "PAYABLE"]
    receivable_vendors = [dict(v) for v in sv_list if v["billing_type"] == "RECEIVABLE"]

    for v in payable_vendors + receivable_vendors:
        v["payments"]    = payments_map.get(v["id"], [])
        v["paid_amount"] = round(sum(p["amount"] for p in v["payments"]), 2)
        v["balance"]     = round(float(v["amount"]) - v["paid_amount"], 2)

    active_vendors  = [v for v in get_all_vendors(user_id=session["user_id"]) if v["status"] == "ACTIVE"]
    inbound_vendors  = [v for v in active_vendors if v["vendor_type"] == "INBOUND"]
    outbound_vendors = [v for v in active_vendors if v["vendor_type"] == "OUTBOUND"]
    total_expenses  = sum(e["amount"] for e in expenses)
    payables    = get_total_payables_by_shipment(id)
    receivables = get_total_receivables_by_shipment(id)
    payables_paid    = round(sum(v["paid_amount"] for v in payable_vendors), 2)
    receivables_rcvd = round(sum(v["paid_amount"] for v in receivable_vendors), 2)

    return render_template(
        "shipment_detail.html",
        shipment=shipment,
        expenses=expenses,
        payable_vendors=payable_vendors,
        receivable_vendors=receivable_vendors,
        inbound_vendors=inbound_vendors,
        outbound_vendors=outbound_vendors,
        total_expenses=total_expenses,
        payables=payables,
        receivables=receivables,
        payables_paid=payables_paid,
        receivables_rcvd=receivables_rcvd,
        categories=EXPENSE_CATEGORIES,
        relationship_types=RELATIONSHIP_TYPES,
        billing_types=BILLING_TYPES,
        payment_statuses=PAYMENT_STATUSES,
        currencies=CURRENCIES,
        today=date.today().isoformat(),
        active_section="shipments",
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
            active_section="shipments",
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
            active_section="shipments",
        )

    existing = get_shipment_by_number(shipment_number)
    if existing and existing["id"] != id:
        return render_template(
            "edit_shipment.html",
            shipment=shipment,
            statuses=SHIPMENT_STATUSES,
            incoterms=INCOTERMS,
            error="A shipment with that number already exists.",
            active_section="shipments",
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
    log_alert(
        user_id=session["user_id"],
        entity_type="SHIPMENT",
        entity_id=id,
        entity_label=shipment_number,
        action="UPDATED",
        description=f"Shipment {shipment_number} updated",
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
    log_alert(
        user_id=session["user_id"],
        entity_type="SHIPMENT",
        entity_id=id,
        entity_label=shipment["shipment_number"],
        action="STATUS_CHANGED",
        description=f"Shipment {shipment['shipment_number']} status changed to {new_status}",
    )
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
    _sv_vendor = get_vendor_row(vendor_id)
    _sv_vendor_name = _sv_vendor["vendor_name"] if _sv_vendor else str(vendor_id)
    log_alert(
        user_id=session["user_id"],
        entity_type="BILLING",
        entity_id=None,
        entity_label=f"{_sv_vendor_name} / {shipment['shipment_number']}",
        action="CREATED",
        description=f"Billing entry created: {_sv_vendor_name} on {shipment['shipment_number']}",
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
    _sv_vendor = get_vendor_row(sv["vendor_id"])
    _sv_vendor_name = _sv_vendor["vendor_name"] if _sv_vendor else str(sv["vendor_id"])
    log_alert(
        user_id=session["user_id"],
        entity_type="BILLING",
        entity_id=sv_id,
        entity_label=f"{_sv_vendor_name} / {shipment['shipment_number']}",
        action="UPDATED",
        description=f"Billing entry updated: {_sv_vendor_name} on {shipment['shipment_number']}",
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
    log_alert(
        user_id=session["user_id"],
        entity_type="BILLING",
        entity_id=None,
        entity_label=f"Billing entry on {shipment['shipment_number']}",
        action="DELETED",
        description=f"Billing entry deleted on shipment {shipment['shipment_number']}",
    )
    return jsonify({"ok": True})


@app.route("/shipments/<int:shipment_id>/vendors/<int:sv_id>/payments/add", methods=["POST"])
def add_sv_payment(shipment_id, sv_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    shipment = get_shipment_by_id(shipment_id)
    if shipment is None:
        abort(404)
    if shipment["user_id"] != session["user_id"]:
        abort(403)
    sv = get_shipment_vendor_by_id(sv_id)
    if sv is None or sv["shipment_id"] != shipment_id:
        abort(404)

    try:
        amount = float(request.form.get("amount", "0").strip())
    except (ValueError, TypeError):
        amount = 0.0

    if amount <= 0:
        return redirect(url_for("shipment_detail", id=shipment_id))

    existing_paid = sum(p["amount"] for p in get_payments_by_sv(sv_id))
    total = float(sv["amount"] or 0)
    if existing_paid + amount > total + 0.005:
        return redirect(url_for("shipment_detail", id=shipment_id))

    payment_date = request.form.get("payment_date", "").strip() or date.today().isoformat()
    reference    = request.form.get("reference", "").strip() or None
    notes        = request.form.get("notes", "").strip() or None
    create_sv_payment(sv_id=sv_id, amount=amount, payment_date=payment_date,
                      reference=reference, notes=notes)
    return redirect(url_for("shipment_detail", id=shipment_id))


@app.route("/shipments/<int:shipment_id>/vendors/<int:sv_id>/payments/<int:payment_id>/delete",
           methods=["POST"])
def delete_sv_payment_route(shipment_id, sv_id, payment_id):
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
    payment = get_sv_payment_by_id(payment_id)
    if payment is None or payment["shipment_vendor_id"] != sv_id:
        abort(404)
    delete_sv_payment(payment_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true", port=port)
