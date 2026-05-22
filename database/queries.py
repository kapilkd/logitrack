from datetime import datetime
from database.db import get_db


def _date_filter(from_date, to_date):
    sql, params = "", []
    if from_date is not None:
        sql += " AND date >= %s"
        params.append(from_date)
    if to_date is not None:
        sql += " AND date <= %s"
        params.append(to_date)
    return sql, params


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    created = row["created_at"]
    if isinstance(created, datetime):
        member_since = created.strftime("%B %Y")
    else:
        member_since = datetime.strptime(str(created)[:10], "%Y-%m-%d").strftime("%B %Y")
    name = row["name"]
    initials = "".join(w[0].upper() for w in name.split() if w)
    return {"name": name, "initials": initials, "email": row["email"], "member_since": member_since}


def get_summary_stats(user_id, from_date=None, to_date=None):
    extra_sql, extra_params = _date_filter(from_date, to_date)
    conn = get_db()
    totals = conn.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total, COUNT(*) AS cnt"
        " FROM expenses WHERE user_id = %s" + extra_sql,
        (user_id, *extra_params),
    ).fetchone()
    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = %s" + extra_sql +
        " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user_id, *extra_params),
    ).fetchone()
    conn.close()
    return {
        "total_spent": "₹{:,.2f}".format(totals['total']),
        "transaction_count": totals["cnt"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, from_date=None, to_date=None):
    extra_sql, extra_params = _date_filter(from_date, to_date)
    conn = get_db()
    rows = conn.execute(
        "SELECT id, date, description, category, amount FROM expenses"
        " WHERE user_id = %s" + extra_sql + " ORDER BY date DESC, id DESC LIMIT %s",
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
            "amount": "₹{:,.2f}".format(row['amount']),
            "raw_amount": row["amount"],
        })
    return result


def get_category_breakdown(user_id, from_date=None, to_date=None):
    extra_sql, extra_params = _date_filter(from_date, to_date)
    conn = get_db()
    rows = conn.execute(
        "SELECT category AS name, SUM(amount) AS amount, COUNT(*) AS count"
        " FROM expenses WHERE user_id = %s" + extra_sql +
        " GROUP BY category ORDER BY amount DESC",
        (user_id, *extra_params),
    ).fetchall()
    total_row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS t FROM expenses WHERE user_id = %s" + extra_sql,
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
            "amount": "₹{:,.2f}".format(row['amount']),
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
        sql += " AND vendor_type = %s"
        params.append(vendor_type)
    if vendor_category in _VENDOR_CATEGORIES:
        sql += " AND vendor_category = %s"
        params.append(vendor_category)
    if vendor_status in _VENDOR_STATUSES:
        sql += " AND status = %s"
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
        WHERE s.user_id = %s
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
        WHERE s.user_id = %s
    """
    params = [user_id]
    if payment_status in _VALID_PAYMENT_STATUSES:
        sql += " AND sv.payment_status = %s"
        params.append(payment_status)
    if billing_type in _VALID_BILLING_TYPES:
        sql += " AND sv.billing_type = %s"
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


def get_shipment_bill_vendors(shipment_id):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT sv.id AS sv_id, sv.relationship_type, sv.billing_type, sv.amount, sv.currency,
               sv.invoice_number, sv.invoice_date, sv.due_date, sv.payment_status, sv.notes,
               v.vendor_name, v.vendor_code, v.vendor_category, v.vendor_type,
               v.company_name, v.owner_name, v.email AS vendor_email, v.phone AS vendor_phone,
               v.address_line1, v.address_line2, v.city, v.state, v.country, v.pincode,
               v.gst_number, v.pan_number, v.iec_code,
               v.bank_name, v.account_number, v.ifsc_code, v.upi_id
        FROM shipment_vendors sv
        JOIN vendors v ON sv.vendor_id = v.id
        WHERE sv.shipment_id = %s
        ORDER BY v.vendor_name ASC
        """,
        (shipment_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_alerts(user_id, limit=50):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, entity_type, entity_id, entity_label, action, description, created_at"
        " FROM system_alerts WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
        (user_id, limit),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        created = row["created_at"]
        try:
            if isinstance(created, datetime):
                formatted = created.strftime("%d %b %Y, %H:%M")
            else:
                formatted = datetime.strptime(str(created)[:16], "%Y-%m-%d %H:%M").strftime("%d %b %Y, %H:%M")
        except (ValueError, TypeError):
            formatted = str(created) if created else ""
        result.append({
            "id": row["id"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "entity_label": row["entity_label"] or "",
            "action": row["action"],
            "description": row["description"] or "",
            "created_at": formatted,
        })
    return result


def get_vendor_ledger(vendor_id):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT sv.id AS sv_id, sv.relationship_type, sv.billing_type,
               sv.amount, sv.currency, sv.invoice_number, sv.invoice_date,
               sv.due_date, sv.payment_status, sv.notes,
               s.id AS shipment_id, s.shipment_number,
               s.origin, s.destination, s.status AS shipment_status,
               s.shipment_date
        FROM shipment_vendors sv
        JOIN shipments s ON sv.shipment_id = s.id
        WHERE sv.vendor_id = %s
        ORDER BY s.shipment_date DESC, sv.id ASC
        """,
        (vendor_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_vendor_ledger_stats(vendor_id):
    conn = get_db()
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN billing_type = 'PAYABLE' THEN amount ELSE 0 END), 0.0)   AS total_payable,
            COALESCE(SUM(CASE WHEN billing_type = 'RECEIVABLE' THEN amount ELSE 0 END), 0.0) AS total_receivable,
            COALESCE(SUM(CASE WHEN payment_status IN ('PENDING','PARTIAL','OVERDUE') THEN amount ELSE 0 END), 0.0) AS pending_amount,
            COUNT(CASE WHEN payment_status = 'OVERDUE' THEN 1 END) AS overdue_count
        FROM shipment_vendors
        WHERE vendor_id = %s
        """,
        (vendor_id,),
    ).fetchone()
    conn.close()
    return {
        "total_payable":    row["total_payable"],
        "total_receivable": row["total_receivable"],
        "pending_amount":   row["pending_amount"],
        "overdue_count":    int(row["overdue_count"]),
    }


def get_emails_with_shipment_links(user_id, limit=100):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT
            e.id,
            e.gmail_message_id,
            e.gmail_thread_id,
            e.direction,
            e.from_email,
            e.from_name,
            e.to_email,
            e.subject,
            e.snippet,
            e.received_at,
            e.sent_at,
            e.synced_at,
            eap.shipment_reference,
            eap.processing_status    AS ai_status,
            s.id                     AS linked_shipment_id,
            s.shipment_number        AS linked_shipment_number,
            s.status                 AS linked_shipment_status,
            s.origin                 AS linked_shipment_origin,
            s.destination            AS linked_shipment_destination
        FROM emails e
        LEFT JOIN email_ai_processing eap ON eap.email_id = e.id
        LEFT JOIN shipments s
               ON s.shipment_number = eap.shipment_reference
              AND s.user_id = %s
        WHERE e.user_id = %s
        ORDER BY COALESCE(e.received_at, e.sent_at, e.synced_at::text) DESC
        LIMIT %s
        """,
        (user_id, user_id, limit),
    ).fetchall()
    conn.close()
    return rows


def get_shipment_report_rows(user_id, status=None, from_date=None, to_date=None):
    sql = """
        SELECT
            s.id          AS shipment_id,
            s.shipment_number,
            s.origin,
            s.destination,
            s.status,
            s.shipment_date,
            s.carrier,
            COALESCE(e.expense_total, 0.0)                                        AS expense_total,
            COALESCE(sv.total_payable, 0.0)                                       AS total_payable,
            COALESCE(sv.total_receivable, 0.0)                                    AS total_receivable,
            COALESCE(sv.total_receivable, 0.0) - COALESCE(sv.total_payable, 0.0) AS net_position,
            COALESCE(sv.vendor_count, 0)                                          AS vendor_count
        FROM shipments s
        LEFT JOIN (
            SELECT shipment_id, SUM(amount) AS expense_total
            FROM expenses
            GROUP BY shipment_id
        ) e ON e.shipment_id = s.id
        LEFT JOIN (
            SELECT
                shipment_id,
                SUM(CASE WHEN billing_type = 'PAYABLE'    THEN amount ELSE 0 END) AS total_payable,
                SUM(CASE WHEN billing_type = 'RECEIVABLE' THEN amount ELSE 0 END) AS total_receivable,
                COUNT(DISTINCT vendor_id)                                          AS vendor_count
            FROM shipment_vendors
            GROUP BY shipment_id
        ) sv ON sv.shipment_id = s.id
        WHERE s.user_id = %s
    """
    params = [user_id]
    if status:
        sql += " AND s.status = %s"
        params.append(status)
    if from_date:
        sql += " AND s.shipment_date >= %s"
        params.append(from_date)
    if to_date:
        sql += " AND s.shipment_date <= %s"
        params.append(to_date)
    sql += " ORDER BY s.shipment_date DESC, s.id DESC"

    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [
        {
            "shipment_id":      row["shipment_id"],
            "shipment_number":  row["shipment_number"],
            "origin":           row["origin"] or "",
            "destination":      row["destination"] or "",
            "status":           row["status"],
            "shipment_date":    row["shipment_date"] or "",
            "carrier":          row["carrier"] or "",
            "expense_total":    row["expense_total"],
            "total_payable":    row["total_payable"],
            "total_receivable": row["total_receivable"],
            "net_position":     row["net_position"],
            "vendor_count":     int(row["vendor_count"]),
        }
        for row in rows
    ]


def get_report_summary_stats(user_id, status=None, from_date=None, to_date=None):
    sql = """
        SELECT
            COUNT(*)                                AS shipment_count,
            COALESCE(SUM(e.expense_total), 0.0)    AS expense_total,
            COALESCE(SUM(sv.total_payable), 0.0)   AS total_payable,
            COALESCE(SUM(sv.total_receivable), 0.0) AS total_receivable
        FROM shipments s
        LEFT JOIN (
            SELECT shipment_id, SUM(amount) AS expense_total
            FROM expenses
            GROUP BY shipment_id
        ) e ON e.shipment_id = s.id
        LEFT JOIN (
            SELECT
                shipment_id,
                SUM(CASE WHEN billing_type = 'PAYABLE'    THEN amount ELSE 0 END) AS total_payable,
                SUM(CASE WHEN billing_type = 'RECEIVABLE' THEN amount ELSE 0 END) AS total_receivable
            FROM shipment_vendors
            GROUP BY shipment_id
        ) sv ON sv.shipment_id = s.id
        WHERE s.user_id = %s
    """
    params = [user_id]
    if status:
        sql += " AND s.status = %s"
        params.append(status)
    if from_date:
        sql += " AND s.shipment_date >= %s"
        params.append(from_date)
    if to_date:
        sql += " AND s.shipment_date <= %s"
        params.append(to_date)

    conn = get_db()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return {
        "shipment_count":   int(row["shipment_count"]),
        "expense_total":    row["expense_total"],
        "total_payable":    row["total_payable"],
        "total_receivable": row["total_receivable"],
    }


def get_expense_link_summary(user_id, from_date=None, to_date=None):
    sql = """
        SELECT
            COALESCE(SUM(amount), 0.0)                                                   AS total,
            COUNT(*)                                                                      AS total_count,
            COALESCE(SUM(CASE WHEN shipment_id IS NOT NULL THEN amount ELSE 0 END), 0.0) AS linked_total,
            COUNT(CASE WHEN shipment_id IS NOT NULL THEN 1 END)                          AS linked_count,
            COALESCE(SUM(CASE WHEN shipment_id IS NULL THEN amount ELSE 0 END), 0.0)     AS standalone_total,
            COUNT(CASE WHEN shipment_id IS NULL THEN 1 END)                              AS standalone_count
        FROM expenses
        WHERE user_id = %s
    """
    params = [user_id]
    if from_date:
        sql += " AND date >= %s"
        params.append(from_date)
    if to_date:
        sql += " AND date <= %s"
        params.append(to_date)
    conn = get_db()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return {
        "total":            row["total"],
        "total_count":      int(row["total_count"]),
        "linked_total":     row["linked_total"],
        "linked_count":     int(row["linked_count"]),
        "standalone_total": row["standalone_total"],
        "standalone_count": int(row["standalone_count"]),
    }


def get_monthly_expense_trend(user_id, from_date=None, to_date=None):
    sql = """
        SELECT
            TO_CHAR(date::date, 'YYYY-MM') AS month,
            SUM(amount)                    AS total,
            COUNT(*)                       AS count
        FROM expenses
        WHERE user_id = %s
    """
    params = [user_id]
    if from_date:
        sql += " AND date >= %s"
        params.append(from_date)
    if to_date:
        sql += " AND date <= %s"
        params.append(to_date)
    sql += " GROUP BY TO_CHAR(date::date, 'YYYY-MM') ORDER BY month ASC"
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    result = []
    for row in rows:
        try:
            label = datetime.strptime(row["month"], "%Y-%m").strftime("%B %Y")
        except (ValueError, TypeError):
            label = row["month"]
        result.append({
            "month":       row["month"],
            "month_label": label,
            "total":       row["total"],
            "count":       int(row["count"]),
        })
    return result


def get_vendor_report_rows(user_id, vendor_type=None, vendor_category=None,
                            vendor_status=None, from_date=None, to_date=None):
    sql = """
        SELECT
            v.id                                                                        AS vendor_id,
            v.vendor_code,
            v.vendor_name,
            v.vendor_category,
            v.vendor_type,
            v.status,
            COALESCE(SUM(CASE WHEN sv.billing_type = 'PAYABLE'
                              THEN sv.amount ELSE 0 END), 0.0)                         AS total_payable,
            COALESCE(SUM(CASE WHEN sv.billing_type = 'RECEIVABLE'
                              THEN sv.amount ELSE 0 END), 0.0)                         AS total_receivable,
            COALESCE(SUM(CASE WHEN sv.billing_type = 'RECEIVABLE'
                              THEN sv.amount ELSE 0 END), 0.0)
            - COALESCE(SUM(CASE WHEN sv.billing_type = 'PAYABLE'
                              THEN sv.amount ELSE 0 END), 0.0)                         AS net_position,
            COUNT(DISTINCT sv.shipment_id)                                              AS shipment_count,
            COUNT(CASE WHEN sv.payment_status IN ('PENDING','PARTIAL','OVERDUE')
                       THEN sv.id END)                                                  AS pending_count
        FROM vendors v
        LEFT JOIN shipment_vendors sv ON sv.vendor_id = v.id
        LEFT JOIN shipments s ON s.id = sv.shipment_id
        WHERE v.user_id = %s
    """
    params = [user_id]
    if vendor_type in _VENDOR_TYPES:
        sql += " AND v.vendor_type = %s"
        params.append(vendor_type)
    if vendor_category in _VENDOR_CATEGORIES:
        sql += " AND v.vendor_category = %s"
        params.append(vendor_category)
    if vendor_status in _VENDOR_STATUSES:
        sql += " AND v.status = %s"
        params.append(vendor_status)
    if from_date:
        sql += " AND (s.shipment_date IS NULL OR s.shipment_date >= %s)"
        params.append(from_date)
    if to_date:
        sql += " AND (s.shipment_date IS NULL OR s.shipment_date <= %s)"
        params.append(to_date)
    sql += " GROUP BY v.id ORDER BY v.vendor_name ASC"
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [
        {
            "vendor_id":        row["vendor_id"],
            "vendor_code":      row["vendor_code"],
            "vendor_name":      row["vendor_name"],
            "vendor_category":  row["vendor_category"],
            "vendor_type":      row["vendor_type"],
            "status":           row["status"],
            "total_payable":    row["total_payable"],
            "total_receivable": row["total_receivable"],
            "net_position":     row["net_position"],
            "shipment_count":   int(row["shipment_count"]),
            "pending_count":    int(row["pending_count"]),
        }
        for row in rows
    ]


def get_vendor_report_summary(user_id, vendor_type=None, vendor_category=None,
                               vendor_status=None, from_date=None, to_date=None):
    sql = """
        SELECT
            COUNT(DISTINCT v.id)                                                        AS vendor_count,
            COALESCE(SUM(CASE WHEN sv.billing_type = 'PAYABLE'
                              THEN sv.amount ELSE 0 END), 0.0)                         AS total_payable,
            COALESCE(SUM(CASE WHEN sv.billing_type = 'RECEIVABLE'
                              THEN sv.amount ELSE 0 END), 0.0)                         AS total_receivable,
            COUNT(DISTINCT sv.shipment_id)                                              AS total_shipments,
            COUNT(CASE WHEN sv.payment_status = 'OVERDUE' THEN sv.id END)              AS overdue_count
        FROM vendors v
        LEFT JOIN shipment_vendors sv ON sv.vendor_id = v.id
        LEFT JOIN shipments s ON s.id = sv.shipment_id
        WHERE v.user_id = %s
    """
    params = [user_id]
    if vendor_type in _VENDOR_TYPES:
        sql += " AND v.vendor_type = %s"
        params.append(vendor_type)
    if vendor_category in _VENDOR_CATEGORIES:
        sql += " AND v.vendor_category = %s"
        params.append(vendor_category)
    if vendor_status in _VENDOR_STATUSES:
        sql += " AND v.status = %s"
        params.append(vendor_status)
    if from_date:
        sql += " AND (s.shipment_date IS NULL OR s.shipment_date >= %s)"
        params.append(from_date)
    if to_date:
        sql += " AND (s.shipment_date IS NULL OR s.shipment_date <= %s)"
        params.append(to_date)
    conn = get_db()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return {
        "vendor_count":     int(row["vendor_count"]),
        "total_payable":    row["total_payable"],
        "total_receivable": row["total_receivable"],
        "total_shipments":  int(row["total_shipments"]),
        "overdue_count":    int(row["overdue_count"]),
    }
