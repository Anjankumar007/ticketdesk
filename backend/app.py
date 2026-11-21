"""app.py - Flask routes only. No SQL here: SQL lives in queries.py.
Run:  python app.py     then open  http://127.0.0.1:5000"""
from flask import Flask, jsonify, request
import mysql.connector
import db
import queries as Q

app = Flask(__name__, static_folder="static", static_url_path="/static")


class ApiError(Exception):
    def __init__(self, message, code=400):
        self.message, self.code = message, code


@app.errorhandler(ApiError)
def handle_api_error(e):
    return jsonify(error=e.message), e.code


@app.errorhandler(mysql.connector.Error)
def handle_mysql_error(e):
    # Send MySQL's own message to the page, e.g. "Error 1062: Duplicate entry ..."
    return jsonify(error=f"Error {e.errno}: {e.msg}"), 400


def as_int(value, name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{name} must be a number")


@app.route("/")
def home():
    return app.send_static_file("index.html")


# ---------------- events ----------------
@app.get("/api/events")
def list_events():
    q = request.args.get("q", "")
    etype = request.args.get("type", "")
    order = Q.EVENTS_SORT.get(request.args.get("sort"), "e.event_date")  # whitelist: safe to put in SQL
    sql = Q.EVENTS_LIST.format(sort=order)
    return jsonify(db.query(sql, (f"%{q}%", etype, etype)))


@app.get("/api/events/<int:event_id>/seats")
def event_seats(event_id):
    rows = db.query(Q.SEATS_FOR_EVENT, (event_id,))
    for r in rows:
        r["booked"] = bool(r["booked"])
    return jsonify(rows)


# ---------------- bookings ----------------
@app.get("/api/bookings")
def list_bookings():
    return jsonify(db.query(Q.BOOKINGS_LIST))


@app.post("/api/bookings")
def create_booking():
    body = request.get_json(silent=True) or {}
    user_id = as_int(body.get("user_id"), "user_id")
    event_id = as_int(body.get("event_id"), "event_id")
    raw = body.get("seat_nos") or [body.get("seat_no")]     # one seat or a list of seats
    seat_nos = [as_int(s, "seat_no") for s in raw]
    if not 1 <= len(seat_nos) <= 10 or len(set(seat_nos)) != len(seat_nos):
        raise ApiError("Choose between 1 and 10 different seats")
    ids = []
    # every seat's booking + payment = ONE transaction: if any seat fails, nothing is saved
    with db.transaction() as cur:
        cur.execute(Q.EVENT_VENUE, (event_id,))
        ev = cur.fetchone()
        if ev is None:
            raise ApiError("Event not found", 404)
        for seat_no in seat_nos:
            cur.execute(Q.INSERT_BOOKING, (user_id, event_id, ev["venue_id"], seat_no))
            booking_id = cur.lastrowid
            cur.execute(Q.INSERT_PAYMENT, (booking_id, "UPI", event_id, seat_no))
            ids.append(booking_id)
    return jsonify(booking_id=ids[0], booking_ids=ids, sql="see queries.py"), 201


@app.delete("/api/bookings/<int:booking_id>")
def cancel_booking(booking_id):
    with db.transaction() as cur:
        cur.execute(Q.DELETE_BOOKING, (booking_id,))
        affected = cur.rowcount
    return jsonify(affected=affected, sql=Q.DELETE_BOOKING.replace("%s", str(booking_id)) + ";")


# ---------------- reports ----------------
@app.get("/api/reports/<name>")
def report(name):
    if name not in Q.REPORTS:
        raise ApiError("Unknown report", 404)
    title, columns, sql = Q.REPORTS[name]
    return jsonify(title=title, columns=columns, sql=sql, rows=db.query(sql, as_dict=False))


# ---------------- admin: bulk operations ----------------
def bulk_update(sql, message):
    with db.transaction() as cur:
        cur.execute(sql)
        n = cur.rowcount
    return jsonify(affected=n, message=message.format(n=n), sql=sql)


def must_fail(sql):
    """Run a statement that MySQL is supposed to reject. Always rolled back."""
    conn = db.connect()
    try:
        cur = conn.cursor()
        cur.execute(sql)  # a MySQL error here goes to handle_mysql_error
        conn.rollback()
        raise ApiError("MySQL accepted it, so the constraint is missing. Check schema.sql.", 500)
    finally:
        conn.close()


@app.post("/api/admin/<action>")
def admin(action):
    if action == "price_hike":
        return bulk_update(Q.PRICE_HIKE, "{n} concert prices raised by 10%")
    if action == "complete_past":
        return bulk_update(Q.COMPLETE_PAST, "{n} bookings marked completed")
    if action == "archive_completed":
        with db.transaction() as cur:          # copy then delete, together
            cur.execute(Q.ARCHIVE_COPY)
            cur.execute(Q.ARCHIVE_DELETE)
            n = cur.rowcount
        return jsonify(affected=n, message=f"{n} bookings moved to bookings_archive",
                       sql=Q.ARCHIVE_COPY + "\n" + Q.ARCHIVE_DELETE)
    tests = {"test_double_booking": Q.TEST_DOUBLE_BOOKING,
             "test_negative_price": Q.TEST_NEGATIVE_PRICE,
             "test_delete_venue": Q.TEST_DELETE_VENUE}
    if action in tests:
        must_fail(tests[action])
    raise ApiError("Unknown action", 404)


if __name__ == "__main__":
    app.run(debug=True)   # debug=True reloads automatically when you save a file
