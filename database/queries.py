from datetime import datetime
from database.db import get_db


def _date_filter(from_date, to_date):
    sql, params = "", []
    if from_date is not None:
        sql += " AND date >= ?"
        params.append(from_date)
    if to_date is not None:
        sql += " AND date <= ?"
        params.append(to_date)
    return sql, params


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    member_since = datetime.strptime(row["created_at"][:10], "%Y-%m-%d").strftime("%B %Y")
    name = row["name"]
    initials = "".join(w[0].upper() for w in name.split() if w)
    return {"name": name, "initials": initials, "email": row["email"], "member_since": member_since}


def get_summary_stats(user_id, from_date=None, to_date=None):
    extra_sql, extra_params = _date_filter(from_date, to_date)
    conn = get_db()
    totals = conn.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total, COUNT(*) AS cnt "
        "FROM expenses WHERE user_id = ?" + extra_sql,
        (user_id, *extra_params),
    ).fetchone()
    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = ?" + extra_sql +
        " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user_id, *extra_params),
    ).fetchone()
    conn.close()
    return {
        "total_spent": f"₹{totals['total']:,.2f}",
        "transaction_count": totals["cnt"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, from_date=None, to_date=None):
    extra_sql, extra_params = _date_filter(from_date, to_date)
    conn = get_db()
    rows = conn.execute(
        "SELECT id, date, description, category, amount FROM expenses "
        "WHERE user_id = ?" + extra_sql + " ORDER BY date DESC, id DESC LIMIT ?",
        (user_id, *extra_params, limit),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        try:
            formatted = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y")
        except ValueError:
            formatted = row["date"]
        result.append({
            "id": row["id"],
            "date": formatted,
            "raw_date": row["date"],
            "description": row["description"] or "",
            "category": row["category"],
            "amount": f"₹{row['amount']:,.2f}",
            "raw_amount": row["amount"],
        })
    return result


def get_category_breakdown(user_id, from_date=None, to_date=None):
    extra_sql, extra_params = _date_filter(from_date, to_date)
    conn = get_db()
    rows = conn.execute(
        "SELECT category AS name, SUM(amount) AS amount, COUNT(*) AS count "
        "FROM expenses WHERE user_id = ?" + extra_sql + " GROUP BY category ORDER BY amount DESC",
        (user_id, *extra_params),
    ).fetchall()
    total_row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS t FROM expenses WHERE user_id = ?" + extra_sql,
        (user_id, *extra_params),
    ).fetchone()
    conn.close()
    total = total_row["t"]
    if not rows or total == 0:
        return []
    result = []
    assigned = 0
    for i, row in enumerate(rows):
        if i < len(rows) - 1:
            pct = round(row["amount"] / total * 100)
        else:
            pct = 100 - assigned
        assigned += pct
        result.append({
            "name": row["name"],
            "amount": f"₹{row['amount']:,.2f}",
            "count": row["count"],
            "pct": pct,
        })
    return result


_VENDOR_TYPES = {"INBOUND", "OUTBOUND"}
_VENDOR_STATUSES = {"ACTIVE", "INACTIVE", "BLOCKED"}
_VENDOR_CATEGORIES = {
    "CUSTOMER", "TRANSPORTER", "SHIPPER", "CONSIGNEE", "WAREHOUSE",
    "CUSTOM_CLEARANCE_AGENT", "FREIGHT_FORWARDER", "PACKAGING_VENDOR",
    "INSURANCE_PROVIDER", "SHIPPING_LINE", "AIR_CARRIER", "LOCAL_TRANSPORT",
    "PORT_AGENT", "COURIER_PARTNER", "BILLING_PARTNER", "OTHER",
}
_VALID_PAYMENT_STATUSES = {"PENDING", "PARTIAL", "PAID", "OVERDUE"}
_VALID_BILLING_TYPES = {"PAYABLE", "RECEIVABLE"}


def get_filtered_vendors(vendor_type=None, vendor_category=None, vendor_status=None):
    sql = "SELECT * FROM vendors WHERE 1=1"
    params = []
    if vendor_type in _VENDOR_TYPES:
        sql += " AND vendor_type = ?"
        params.append(vendor_type)
    if vendor_category in _VENDOR_CATEGORIES:
        sql += " AND vendor_category = ?"
        params.append(vendor_category)
    if vendor_status in _VENDOR_STATUSES:
        sql += " AND status = ?"
        params.append(vendor_status)
    sql += " ORDER BY vendor_name ASC"
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_billing_stats(user_id):
    conn = get_db()
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN sv.billing_type = 'PAYABLE'
                              THEN sv.amount ELSE 0 END), 0.0) AS total_payable,
            COALESCE(SUM(CASE WHEN sv.billing_type = 'RECEIVABLE'
                              THEN sv.amount ELSE 0 END), 0.0) AS total_receivable,
            COALESCE(SUM(CASE WHEN sv.payment_status IN ('PENDING', 'PARTIAL', 'OVERDUE')
                              THEN sv.amount ELSE 0 END), 0.0) AS pending_amount,
            COUNT(CASE WHEN sv.payment_status = 'OVERDUE' THEN 1 END) AS overdue_count
        FROM shipment_vendors sv
        JOIN shipments s ON sv.shipment_id = s.id
        WHERE s.user_id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()
    return {
        "total_payable": row["total_payable"],
        "total_receivable": row["total_receivable"],
        "pending_amount": row["pending_amount"],
        "overdue_count": int(row["overdue_count"]),
    }


def get_shipment_billing_list(user_id, payment_status=None, billing_type=None):
    sql = """
        SELECT
            s.id AS shipment_id, s.shipment_number, s.origin, s.destination,
            s.status AS shipment_status, s.shipment_date,
            sv.id AS sv_id, sv.vendor_id, sv.relationship_type, sv.billing_type,
            sv.amount, sv.currency, sv.invoice_number, sv.invoice_date,
            sv.due_date, sv.payment_status,
            v.vendor_name, v.vendor_code, v.vendor_category
        FROM shipment_vendors sv
        JOIN shipments s ON sv.shipment_id = s.id
        JOIN vendors v ON sv.vendor_id = v.id
        WHERE s.user_id = ?
    """
    params = [user_id]
    if payment_status in _VALID_PAYMENT_STATUSES:
        sql += " AND sv.payment_status = ?"
        params.append(payment_status)
    if billing_type in _VALID_BILLING_TYPES:
        sql += " AND sv.billing_type = ?"
        params.append(billing_type)
    sql += " ORDER BY s.shipment_date DESC, s.id DESC, v.vendor_name ASC"

    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    shipments_map = {}
    order = []
    for row in rows:
        sid = row["shipment_id"]
        if sid not in shipments_map:
            shipments_map[sid] = {
                "shipment_id": sid,
                "shipment_number": row["shipment_number"],
                "origin": row["origin"] or "",
                "destination": row["destination"] or "",
                "shipment_status": row["shipment_status"],
                "shipment_date": row["shipment_date"] or "",
                "total_payable": 0.0,
                "total_receivable": 0.0,
                "_vendor_ids": set(),
                "vendor_count": 0,
                "pending_count": 0,
                "overdue_count": 0,
                "vendors": [],
            }
            order.append(sid)
        entry = shipments_map[sid]
        if row["billing_type"] == "PAYABLE":
            entry["total_payable"] += row["amount"]
        else:
            entry["total_receivable"] += row["amount"]
        if row["payment_status"] in ("PENDING", "PARTIAL", "OVERDUE"):
            entry["pending_count"] += 1
        if row["payment_status"] == "OVERDUE":
            entry["overdue_count"] += 1
        entry["_vendor_ids"].add(row["vendor_id"])
        entry["vendors"].append({
            "sv_id": row["sv_id"],
            "vendor_name": row["vendor_name"],
            "vendor_code": row["vendor_code"],
            "vendor_category": row["vendor_category"],
            "relationship_type": row["relationship_type"],
            "billing_type": row["billing_type"],
            "amount": row["amount"],
            "currency": row["currency"],
            "invoice_number": row["invoice_number"] or "",
            "invoice_date": row["invoice_date"] or "",
            "due_date": row["due_date"] or "",
            "payment_status": row["payment_status"],
        })

    result = []
    for sid in order:
        entry = shipments_map[sid]
        entry["vendor_count"] = len(entry.pop("_vendor_ids"))
        result.append(entry)
    return result
