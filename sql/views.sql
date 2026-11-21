USE ticketdesk;

CREATE OR REPLACE VIEW v_admin_summary AS
SELECT (SELECT COUNT(*)               FROM users)    AS users,
       (SELECT COUNT(*)               FROM events)   AS events,
       (SELECT COUNT(*)               FROM bookings) AS bookings,
       (SELECT COALESCE(SUM(amount),0) FROM payments) AS revenue;
