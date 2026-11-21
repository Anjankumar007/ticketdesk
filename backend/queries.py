"""queries.py - EVERY SQL statement in the project lives here.
To change a query in front of your professor, edit it in this file only.
%s are placeholders: values are passed separately, never pasted into the text."""

# ---------- Events page: WHERE, LIKE, ORDER BY ----------
EVENTS_LIST = """
SELECT e.event_id, e.title, e.type, v.name AS venue, v.city,
       e.event_date, e.base_price,
       (SELECT COUNT(*) FROM bookings b WHERE b.event_id = e.event_id) AS booked,
       v.capacity
FROM events e
JOIN venues v ON v.venue_id = e.venue_id
WHERE e.title LIKE %s
  AND (%s = '' OR e.type = %s)
ORDER BY {sort}
"""
EVENTS_SORT = {"event_date": "e.event_date", "base_price": "e.base_price", "title": "e.title"}

# ---------- Seat picker ----------
SEATS_FOR_EVENT = """
SELECT s.seat_no, s.category, (b.booking_id IS NOT NULL) AS booked
FROM events e
JOIN seats s ON s.venue_id = e.venue_id
LEFT JOIN bookings b ON b.event_id = e.event_id
                    AND b.venue_id = s.venue_id
                    AND b.seat_no  = s.seat_no
WHERE e.event_id = %s
ORDER BY s.seat_no
"""

# ---------- Bookings ----------
EVENT_VENUE = "SELECT venue_id FROM events WHERE event_id = %s"

INSERT_BOOKING = """
INSERT INTO bookings (user_id, event_id, venue_id, seat_no)
VALUES (%s, %s, %s, %s)
"""

# price = base price, x1.5 for VIP seats
INSERT_PAYMENT = """
INSERT INTO payments (booking_id, amount, method)
SELECT %s, IF(s.category = 'VIP', e.base_price * 1.5, e.base_price), %s
FROM events e
JOIN seats s ON s.venue_id = e.venue_id
WHERE e.event_id = %s AND s.seat_no = %s
"""

BOOKINGS_LIST = """
SELECT b.booking_id, u.name AS `user`, e.title AS event, b.seat_no,
       p.amount AS price, b.status, b.booked_at
FROM bookings b
JOIN users u    ON u.user_id    = b.user_id
JOIN events e   ON e.event_id   = b.event_id
JOIN payments p ON p.booking_id = b.booking_id
ORDER BY b.booking_id DESC
LIMIT 60
"""

DELETE_BOOKING = "DELETE FROM bookings WHERE booking_id = %s"

# ---------- Reports: name -> (title, column headings, SQL) ----------
REPORTS = {
    "dashboard": ("Admin dashboard (view: v_admin_summary)",
                  ["Users", "Events", "Bookings", "Revenue (INR)"],
                  "SELECT * FROM v_admin_summary;"),

    "bookings_per_event": ("Bookings per event (5 or more)",
                           ["Event", "Type", "Bookings"],
                           """SELECT e.title, e.type, COUNT(*) AS bookings
FROM events e
JOIN bookings b ON b.event_id = e.event_id
GROUP BY e.event_id, e.title, e.type
HAVING COUNT(*) >= 5
ORDER BY bookings DESC
LIMIT 20;"""),

    "revenue_per_venue": ("Revenue per venue",
                          ["Venue", "City", "Revenue (INR)"],
                          """SELECT v.name, v.city, SUM(p.amount) AS revenue
FROM venues v
JOIN events e   ON e.venue_id   = v.venue_id
JOIN bookings b ON b.event_id   = e.event_id
JOIN payments p ON p.booking_id = b.booking_id
GROUP BY v.venue_id, v.name, v.city
ORDER BY revenue DESC;"""),

    "zero_bookings": ("Events with zero bookings",
                      ["Event", "Type", "Date"],
                      """SELECT e.title, e.type, e.event_date
FROM events e
LEFT JOIN bookings b ON b.event_id = e.event_id
WHERE b.booking_id IS NULL;"""),

    "referrals": ("Users and who referred them (self join)",
                  ["User", "Referred by"],
                  """SELECT u.name AS user_name, r.name AS referred_by
FROM users u
JOIN users r ON u.referred_by = r.user_id
ORDER BY u.user_id
LIMIT 25;"""),

    "above_venue_avg": ("Events priced above their venue average (correlated subquery)",
                        ["Event", "Venue", "Price"],
                        """SELECT e.title, v.name, e.base_price
FROM events e
JOIN venues v ON v.venue_id = e.venue_id
WHERE e.base_price > (
    SELECT AVG(e2.base_price)
    FROM events e2
    WHERE e2.venue_id = e.venue_id
)
ORDER BY e.base_price DESC
LIMIT 25;"""),
}

# ---------- Admin: bulk operations ----------
PRICE_HIKE = """UPDATE events
SET base_price = ROUND(base_price * 1.10, 2)
WHERE event_id IN (SELECT event_id FROM concert);"""

COMPLETE_PAST = """UPDATE bookings
SET status = 'completed'
WHERE status = 'confirmed'
  AND event_id IN (SELECT event_id FROM events WHERE event_date < CURDATE());"""

ARCHIVE_COPY = """INSERT INTO bookings_archive (booking_id, user_id, event_id, venue_id, seat_no, status, booked_at)
SELECT booking_id, user_id, event_id, venue_id, seat_no, status, booked_at
FROM bookings
WHERE status = 'completed';"""

ARCHIVE_DELETE = "DELETE FROM bookings WHERE status = 'completed';"

# Statements that MUST be rejected by MySQL (constraint demos)
TEST_DOUBLE_BOOKING = """INSERT INTO bookings (user_id, event_id, venue_id, seat_no)
SELECT 1, event_id, venue_id, seat_no FROM bookings LIMIT 1;"""
TEST_NEGATIVE_PRICE = "UPDATE events SET base_price = -100 WHERE event_id = 1;"
TEST_DELETE_VENUE = "DELETE FROM venues WHERE venue_id = (SELECT venue_id FROM events LIMIT 1);"
