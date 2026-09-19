
import psycopg
import hashlib
from datetime import date
import uuid

# Connect to PostgreSQL
conn = psycopg.connect(
    host="localhost",
    dbname="postgres",
    user="postgres",
    password=7892,
    port=5432
)

cur = conn.cursor()

print("Connected to PostgreSQL successfully!")


# --------------------------------------------------
# Credential information
# --------------------------------------------------

student_name = "Rahul Kumar"
student_id = 1

institution_name = "ABC Engineering College"
institution_id = 1

course = "B.Tech Computer Science"

issue_date = date.today()

status = "ACTIVE"


# --------------------------------------------------
# Create data to generate the hash
# --------------------------------------------------

credential_data = (
    str(student_id) +
    str(institution_id) +
    course +
    str(issue_date)
)


# --------------------------------------------------
# Generate SHA-256 hash
# --------------------------------------------------

credential_hash = hashlib.sha256(
    credential_data.encode()
).hexdigest()

print("\nCredential Hash:")
print(credential_hash)


# --------------------------------------------------
# Generate unique credential ID
# --------------------------------------------------

credential_id = str(uuid.uuid4())

print("\nCredential ID:")
print(credential_id)


# --------------------------------------------------
# Store credential in PostgreSQL
# --------------------------------------------------

cur.execute("""
    INSERT INTO credentials (
        credential_id,
        student_id,
        institution_id,
        course,
        issue_date,
        credential_hash,
        status,
        student_name,
        institution_name
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    credential_id,
    student_id,
    institution_id,
    course,
    issue_date,
    credential_hash,
    status,
    student_name,
    institution_name
))

conn.commit()

print("\nCredential stored successfully!")


# --------------------------------------------------
# Close database connection
# --------------------------------------------------

cur.close()
conn.close()

print("Database connection closed.")

