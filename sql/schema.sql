-- TicketDesk schema (MySQL 8.0.16+ required: earlier versions parse but IGNORE CHECK constraints)
DROP DATABASE IF EXISTS ticketdesk;
CREATE DATABASE ticketdesk;
USE ticketdesk;

-- 1. users: self-referencing FK (referred_by) -> used for the self join report
CREATE TABLE users (
  user_id     INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(80)  NOT NULL,
  email       VARCHAR(120) NOT NULL,
  referred_by INT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_users_email UNIQUE (email),
  CONSTRAINT chk_users_email CHECK (email LIKE '%_@_%._%'),
  CONSTRAINT fk_users_referrer FOREIGN KEY (referred_by)
    REFERENCES users(user_id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- 2. venues
CREATE TABLE venues (
  venue_id INT AUTO_INCREMENT PRIMARY KEY,
  name     VARCHAR(100) NOT NULL,
  city     VARCHAR(60)  NOT NULL,
  capacity INT NOT NULL,
  CONSTRAINT chk_venue_capacity CHECK (capacity > 0)
);

-- 3. seats: WEAK ENTITY, identified only together with its venue (composite PK)
CREATE TABLE seats (
  venue_id INT NOT NULL,
  seat_no  INT NOT NULL,
  category ENUM('VIP','Regular') NOT NULL DEFAULT 'Regular',
  PRIMARY KEY (venue_id, seat_no),
  CONSTRAINT chk_seat_no CHECK (seat_no > 0),
  CONSTRAINT fk_seats_venue FOREIGN KEY (venue_id)
    REFERENCES venues(venue_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- 4. events: SUPERTYPE of the specialization
CREATE TABLE events (
  event_id   INT AUTO_INCREMENT PRIMARY KEY,
  venue_id   INT NOT NULL,
  title      VARCHAR(120) NOT NULL,
  type       ENUM('concert','movie','sports') NOT NULL,
  event_date DATE NOT NULL,
  base_price DECIMAL(10,2) NOT NULL,
  CONSTRAINT chk_base_price CHECK (base_price > 0),
  -- helper key so bookings can prove "this event is held at this venue"
  CONSTRAINT uq_event_venue UNIQUE (event_id, venue_id),
  -- RESTRICT: a venue that hosts events cannot be deleted (demo: error 1451)
  CONSTRAINT fk_events_venue FOREIGN KEY (venue_id)
    REFERENCES venues(venue_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 4a. SUBTYPES (EER specialization: disjoint, each shares the supertype's PK)
CREATE TABLE concert (
  event_id INT PRIMARY KEY,
  artist   VARCHAR(100) NOT NULL,
  genre    VARCHAR(40),
  CONSTRAINT fk_concert_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);
CREATE TABLE movie (
  event_id INT PRIMARY KEY,
  director VARCHAR(100) NOT NULL,
  language VARCHAR(30),
  CONSTRAINT fk_movie_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);
CREATE TABLE sports_event (
  event_id INT PRIMARY KEY,
  sport    VARCHAR(40) NOT NULL,
  team_a   VARCHAR(60) NOT NULL,
  team_b   VARCHAR(60) NOT NULL,
  CONSTRAINT chk_teams_differ CHECK (team_a <> team_b),
  CONSTRAINT fk_sports_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

-- 5. bookings: resolves users <-> events, and points at one specific seat.
-- NOTE (deliberate denormalization): venue_id is derivable from event_id. It is
-- kept so two composite FKs can guarantee the seat really belongs to the venue
-- that hosts the event. Explain this in the normalization write-up.
CREATE TABLE bookings (
  booking_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  event_id   INT NOT NULL,
  venue_id   INT NOT NULL,
  seat_no    INT NOT NULL,
  status     ENUM('confirmed','completed') NOT NULL DEFAULT 'confirmed',
  booked_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- the double-booking guard
  CONSTRAINT uq_event_seat UNIQUE (event_id, venue_id, seat_no),
  CONSTRAINT fk_bookings_user  FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_bookings_event FOREIGN KEY (event_id, venue_id) REFERENCES events(event_id, venue_id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_bookings_seat  FOREIGN KEY (venue_id, seat_no) REFERENCES seats(venue_id, seat_no)
    ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 6. payments: cancelling (deleting) a booking removes its payment
CREATE TABLE payments (
  payment_id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  amount     DECIMAL(10,2) NOT NULL,
  method     ENUM('UPI','Card','Cash') NOT NULL,
  paid_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_amount CHECK (amount >= 0),
  CONSTRAINT uq_payment_booking UNIQUE (booking_id),
  CONSTRAINT fk_payments_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

-- 7. bookings_archive: target of INSERT ... SELECT. No FKs / UNIQUE on purpose,
-- so a seat can be re-booked after its old booking has been archived.
CREATE TABLE bookings_archive (
  booking_id  INT NOT NULL,
  user_id     INT NOT NULL,
  event_id    INT NOT NULL,
  venue_id    INT NOT NULL,
  seat_no     INT NOT NULL,
  status      VARCHAR(20) NOT NULL,
  booked_at   TIMESTAMP NOT NULL,
  archived_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Helpful indexes for the report joins
CREATE INDEX idx_events_venue   ON events(venue_id);
CREATE INDEX idx_bookings_user  ON bookings(user_id);
