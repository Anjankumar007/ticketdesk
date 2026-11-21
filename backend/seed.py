"""
seed.py - fills the ticketdesk database with 100+ rows per major table.
Run AFTER schema.sql and views.sql:   python seed.py
Needs: pip install mysql-connector-python Faker
"""
import os, sys, random, getpass
from datetime import date, datetime, timedelta
from faker import Faker
import mysql.connector
from dotenv import load_dotenv

load_dotenv()   # same .env file the app uses

random.seed(42)
Faker.seed(42)
fake = Faker("en_IN")

N_USERS, N_VENUES, N_EVENTS, N_BOOKINGS = 150, 15, 100, 500
CITIES = ["Bengaluru", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Pune", "Kolkata"]
GENRES = ["Rock", "Pop", "Classical", "Jazz", "Indie", "Hip-hop"]
LANGS = ["Hindi", "English", "Kannada", "Tamil", "Telugu"]
SPORTS = ["Cricket", "Football", "Kabaddi", "Hockey"]
METHODS = ["UPI", "Card", "Cash"]
TYPES = ["concert", "movie", "sports"]


def build_data():
    """Generate every row in memory (no database needed) so it can be checked first."""
    d = {}
    d["venues"] = [
        (i, f"{fake.last_name()} {random.choice(['Arena', 'Hall', 'Stadium', 'Theatre'])}",
         random.choice(CITIES), random.choice([60, 80, 100]))
        for i in range(1, N_VENUES + 1)
    ]
    cap = {v[0]: v[3] for v in d["venues"]}

    # seats: weak entity, first 10 seats of every venue are VIP
    d["seats"] = [(v, s, "VIP" if s <= 10 else "Regular")
                  for v, c in cap.items() for s in range(1, c + 1)]

    # users: referred_by points only at EARLIER users, so the FK is always valid
    users = []
    for i in range(1, N_USERS + 1):
        ref = random.randint(1, i - 1) if i > 5 and random.random() < 0.4 else None
        users.append((i, fake.name(), f"user{i}.{fake.user_name()}@example.com", ref))
    d["users"] = users

    # events + one subtype row each (type decides which subtype table)
    today = date.today()
    events, concert, movie, sports = [], [], [], []
    for i in range(1, N_EVENTS + 1):
        t = TYPES[i % 3]
        vid = random.randint(1, N_VENUES)
        when = today + timedelta(days=random.randint(-60, 90))
        price = random.randrange(300, 2500, 50)
        if t == "concert":
            title = f"{fake.first_name()} Live Tour {i}"
            concert.append((i, fake.name(), random.choice(GENRES)))
        elif t == "movie":
            title = f"{fake.word().title()} Premiere {i}"
            movie.append((i, fake.name(), random.choice(LANGS)))
        else:
            a, b = random.sample(CITIES, 2)
            title = f"{a} vs {b} Cup {i}"
            sports.append((i, random.choice(SPORTS), f"{a} United", f"{b} Titans"))
        events.append((i, vid, title, t, when.isoformat(), price))
    d["events"], d["concert"], d["movie"], d["sports_event"] = events, concert, movie, sports

    # bookings: skewed towards low event ids so some events end up with ZERO bookings
    ev = {e[0]: e for e in events}
    used, bookings, payments = set(), [], []
    bid = 1
    while len(bookings) < N_BOOKINGS:
        eid = 1 + int((random.random() ** 2) * N_EVENTS)
        vid = ev[eid][1]
        seat = random.randint(1, cap[vid])
        if (eid, seat) in used:
            continue
        used.add((eid, seat))
        uid = random.randint(1, N_USERS)
        booked = datetime.now() - timedelta(days=random.randint(0, 60))
        bookings.append((bid, uid, eid, vid, seat, "confirmed", booked.strftime("%Y-%m-%d %H:%M:%S")))
        price = ev[eid][5] * (1.5 if seat <= 10 else 1.0)
        payments.append((bid, round(price, 2), random.choice(METHODS)))
        bid += 1
    d["bookings"], d["payments"] = bookings, payments
    return d


SQL = {
    "venues": "INSERT INTO venues (venue_id, name, city, capacity) VALUES (%s,%s,%s,%s)",
    "seats": "INSERT INTO seats (venue_id, seat_no, category) VALUES (%s,%s,%s)",
    "users": "INSERT INTO users (user_id, name, email, referred_by) VALUES (%s,%s,%s,%s)",
    "events": "INSERT INTO events (event_id, venue_id, title, type, event_date, base_price) VALUES (%s,%s,%s,%s,%s,%s)",
    "concert": "INSERT INTO concert (event_id, artist, genre) VALUES (%s,%s,%s)",
    "movie": "INSERT INTO movie (event_id, director, language) VALUES (%s,%s,%s)",
    "sports_event": "INSERT INTO sports_event (event_id, sport, team_a, team_b) VALUES (%s,%s,%s,%s)",
    "bookings": "INSERT INTO bookings (booking_id, user_id, event_id, venue_id, seat_no, status, booked_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
    "payments": "INSERT INTO payments (booking_id, amount, method) VALUES (%s,%s,%s)",
}
# parents before children, so every foreign key already has its target row
ORDER = ["venues", "seats", "users", "events", "concert", "movie", "sports_event", "bookings", "payments"]


def main():
    pw = os.environ.get("DB_PASSWORD") or getpass.getpass("MySQL root password: ")
    conn = mysql.connector.connect(host=os.environ.get("DB_HOST", "localhost"),
                                   user=os.environ.get("DB_USER", "root"),
                                   password=pw, database="ticketdesk")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] > 0:
        sys.exit("Tables already contain data. Re-run schema.sql first for a clean start.")
    data = build_data()
    try:
        for t in ORDER:
            cur.executemany(SQL[t], data[t])
            print(f"{t:<13} {cur.rowcount} rows")
        conn.commit()          # all-or-nothing: nothing is saved without this line
        print("Done. Data committed.")
    except mysql.connector.Error as e:
        conn.rollback()
        sys.exit(f"Failed, nothing saved: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
