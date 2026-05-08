from datetime import datetime
from database.db import get_db


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


def get_summary_stats(user_id):
    conn = get_db()
    totals = conn.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total, COUNT(*) AS cnt "
        "FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = ? "
        "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return {
        "total_spent": f"₹{totals['total']:,.2f}",
        "transaction_count": totals["cnt"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount FROM expenses "
        "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        try:
            formatted = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y")
        except ValueError:
            formatted = row["date"]
        result.append({
            "date": formatted,
            "description": row["description"] or "",
            "category": row["category"],
            "amount": f"₹{row['amount']:,.2f}",
        })
    return result


def get_category_breakdown(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT category AS name, SUM(amount) AS amount, COUNT(*) AS count "
        "FROM expenses WHERE user_id = ? GROUP BY category ORDER BY amount DESC",
        (user_id,),
    ).fetchall()
    total_row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS t FROM expenses WHERE user_id = ?",
        (user_id,),
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
