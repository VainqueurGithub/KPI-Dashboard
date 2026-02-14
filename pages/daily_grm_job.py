import psycopg2
from datetime import date

conn = psycopg2.connect(
    host="localhost",
    database="grm_db",
    user="grm_user",
    password="password"
)

cur = conn.cursor()

# Example: find overdue grievances
cur.execute("""
    INSERT INTO redd_project.notifications (
        grievance_id,
        notification_type,
        recipient_role,
        message
    )
    SELECT
        grievance_id,
        'FOLLOW_UP_DUE',
        'Safeguards Officer',
        CONCAT('3-month follow-up is due today: ', reference_number)
    FROM redd_project.follow_ups
    WHERE
        followup_due_date <= CURRENT_DATE
        AND followup_status = 'Pending'
        AND grievance_id NOT IN (SELECT grievance_id FROM redd_project.notifications WHERE notification_type = 'FOLLOW_UP_DUE';
""")

conn.commit()
cur.close()
conn.close()
