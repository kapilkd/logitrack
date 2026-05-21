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
    log_alert,
    get_company_profile, upsert_company_profile,
    get_all_contact_emails_by_user,
    upsert_gmail_account, get_gmail_account, delete_gmail_account,
    save_email, get_emails_by_user, get_email_by_id,
    get_emails_by_thread, upsert_ai_processing, get_ai_processing,
)
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown, get_filtered_vendors, get_billing_stats, get_shipment_billing_list, get_recent_alerts, get_shipment_bill_vendors, get_emails_with_shipment_links, get_vendor_ledger, get_vendor_ledger_stats
from gmail_utils import (
    GMAIL_AVAILABLE, SCOPES, credentials_file_exists,
    encrypt_token, decrypt_token, sync_inbox, send_gmail, parse_message,
)
from ai_utils import ANTHROPIC_AVAILABLE, process_email_with_claude, generate_reply_with_claude

# Allow OAuth over HTTP in development
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False

_LOGO_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads", "logos")
os.makedirs(_LOGO_UPLOAD_FOLDER, exist_ok=True)
_ALLOWED_LOGO_EXT = {"png", "jpg", "jpeg", "gif", "webp", "svg"}

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
    return render_template("placeholder.html", title="Reports", active_section="reports")


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


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true", port=5001)
