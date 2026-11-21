# TicketDesk: Event Ticket Booking System

A full-stack DBMS course project. Users browse concerts, movies and sports events, pick specific seats and book them. The **database does the heavy lifting**: keys, constraints and referential rules, not application code, stop bad data such as double bookings.

**Stack:** MySQL 8 · Python Flask · raw SQL (no ORM) · plain HTML/CSS/JavaScript

> Built for a syllabus covering ER/EER modelling, DDL/DML, joins, subqueries and views. Data is generated, payments are simulated, and there is no login system.

---

## What you can do in the app

| Page | What it does |
|---|---|
| **Events** | Search, filter by type, sort by date or price |
| **Seat picker** | Choose 1 to 8 seats on a full seat map and book them together |
| **My Bookings** | See every booking and cancel one |
| **Reports** | Six reports built from joins, aggregates, subqueries and a view |
| **Admin** | Bulk updates and archive on hundreds of rows, plus checks that try to break the database rules |

---

## Setup

**You need:** MySQL Server **8.0.16 or newer** and MySQL Workbench, plus Python **3.9+**. (Older MySQL versions silently ignore `CHECK` constraints.)

1. **Clone the repo** and open the folder in VS Code.
2. **Create your `.env` file.** Copy `.env.example` to `.env` and put your MySQL password in it:
   ```
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_mysql_password_here
   ```
   `.env` is git-ignored, so your password never gets uploaded.
3. **Install packages** (from the `backend` folder):
   ```
   cd backend
   pip install -r requirements.txt
   ```
4. **Create the database.** In MySQL Workbench, open and run `sql/schema.sql`, then `sql/views.sql` (lightning-bolt button runs the whole script).
   > Warning: `schema.sql` starts with `DROP DATABASE IF EXISTS ticketdesk;`. Running it again wipes all data. That is also how you reset the project.
5. **Load the sample data:**
   ```
   python seed.py
   ```
   You should see row counts and `Done. Data committed.`
6. **Start the app:**
   ```
   python app.py
   ```
   Open **http://127.0.0.1:5000**

**Quick check in Workbench:** `SELECT COUNT(*) FROM bookings;` should return 500.

---

## Project structure

```
ticketdesk/
├── sql/
│   ├── schema.sql      all tables, keys and constraints
│   └── views.sql       the admin summary view
├── backend/
│   ├── app.py          Flask routes only (no SQL inside)
│   ├── db.py           MySQL connection and transactions
│   ├── queries.py      EVERY SQL statement lives here
│   ├── seed.py         generates the sample data
│   ├── requirements.txt
│   └── static/
│       └── index.html  the whole frontend
├── .env.example
└── README.md
```

## How it works

```
Browser (index.html)  →  Flask route (app.py)  →  SQL text (queries.py)  →  MySQL
        ←  JSON  ←                       ←  rows  ←
```

- The page never talks to MySQL. It calls `/api/...` routes and gets JSON back.
- `app.py` validates input and calls `db.py`; the actual SQL is looked up in `queries.py`.
- Values are passed as `%s` placeholders, never pasted into SQL strings, which blocks SQL injection.
- Booking a seat writes to `bookings` and `payments` in **one transaction**: both save, or neither does.

### API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/events?q=&type=&sort=` | Search, filter and sort events |
| GET | `/api/events/<id>/seats` | Seat map for one event |
| GET | `/api/bookings` | Latest 60 bookings |
| POST | `/api/bookings` | Book one or more seats (`user_id`, `event_id`, `seat_nos`) |
| DELETE | `/api/bookings/<id>` | Cancel a booking |
| GET | `/api/reports/<name>` | Run one report |
| POST | `/api/admin/<action>` | Bulk operations and constraint checks |

---

## The database

**10 tables:** `users`, `venues`, `seats`, `events`, `concert`, `movie`, `sports_event`, `bookings`, `payments`, `bookings_archive`. About 150 users, 15 venues, 1,100 seats, 100 events, 500 bookings and 500 payments are loaded.

| Concept | Where to find it |
|---|---|
| **Weak entity** | `seats`: composite primary key `(venue_id, seat_no)`, cannot exist without a venue |
| **EER specialization** | `events` is the supertype; `concert`, `movie`, `sports_event` are subtypes sharing its key |
| **Many-to-many resolved** | `bookings` links users to events and seats |
| **Self-referencing key** | `users.referred_by` points to another user |
| **Double-booking guard** | `UNIQUE (event_id, venue_id, seat_no)` on `bookings` |
| **CHECK constraints** | price above 0, capacity above 0, valid email, different teams in a match |
| **ON DELETE rules** | `RESTRICT` on venue to events; `CASCADE` from booking to payment; `SET NULL` on referrer |
| **View** | `v_admin_summary` feeds the Overview report |

### Queries and where they show up

| Report | SQL concept |
|---|---|
| Events page | `WHERE`, `LIKE`, `ORDER BY` |
| Top events | `JOIN`, `GROUP BY`, `HAVING` |
| Venue revenue | multi-table `JOIN`, `SUM` |
| No bookings yet | `LEFT JOIN ... IS NULL` |
| Referrals | self join |
| Premium events | correlated subquery |
| Overview | view |
| Admin actions | bulk `UPDATE` with a subquery, `INSERT ... SELECT`, bulk `DELETE` |

### Known design decision
`bookings.venue_id` can be worked out from `event_id`, so strictly the table is not in 3NF. It is kept **on purpose**: two composite foreign keys use it to guarantee a seat belongs to the venue hosting the event.

---

## Learn by trying things

1. **Break a rule.** On the Admin page, run the three "Data protection checks". MySQL itself rejects a double booking, a negative price and a venue deletion. Look in `schema.sql` to find the constraint behind each.
2. **Follow one booking.** Book a seat, then in Workbench run `SELECT * FROM bookings ORDER BY booking_id DESC LIMIT 1;` and the same for `payments`. Cancel it and watch the payment disappear (`ON DELETE CASCADE`).
3. **Change a query.** Edit a report's `LIMIT` in `queries.py` and save. Flask reloads itself, so refresh the page.
4. **Change the schema.** In Workbench: `ALTER TABLE users ADD COLUMN phone VARCHAR(15);` then `UPDATE users SET phone = '9000000000';`

If a manual bulk `UPDATE` or `DELETE` fails in Workbench with **error 1175**, that is safe-update mode. Run `SET SQL_SAFE_UPDATES = 0;` first. The app itself is not affected.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `DB_PASSWORD is not set` | You have not created `.env`. Copy `.env.example` to `.env` |
| Access denied (error 1045) | Wrong password in `.env` |
| Browser shows **Not Found** at `/` | `static/index.html` must sit next to `app.py`, with exactly that name |
| `Tables already contain data` | `seed.py` refuses to run twice. Re-run `schema.sql` for a clean start |
| `pip` not found | Try `python -m pip install -r requirements.txt` |
| Cannot connect to MySQL | Make sure the MySQL server is running |
| Constraints seem ignored | Check `SELECT VERSION();` is 8.0.16 or higher |

## Limitations

- No login. The seat page asks for a customer ID (1 to 150).
- Payments are simulated (always recorded as UPI).
- **Archiving bookings also deletes their payments**, because of `ON DELETE CASCADE`.
- Flask runs in debug mode. This is a learning project, not a production deployment.

## Contributors

Add your names here.
