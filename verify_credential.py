
import psycopg
import hashlib

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


# Ask for credential ID
credential_id = input("Enter Credential ID: ")


# Find credential in database
cur.execute("""
    SELECT
        student_id,
        institution_id,
        course,
        issue_date,
        credential_hash,
        status,
        student_name,
        institution_name
    FROM credentials
    WHERE credential_id = %s
""", (credential_id,))

credential = cur.fetchone()


# Check whether credential exists
if credential is None:

    print("\nCredential not found ❌")

else:

    (
        student_id,
        institution_id,
        course,
        issue_date,
        stored_hash,
        status,
        student_name,
        institution_name
    ) = credential

    print("\nCredential Found!")
    print("Student:", student_name)
    print("Course:", course)
    print("Institution:", institution_name)
    print("Issue Date:", issue_date)
    print("Status:", status)


    # Generate hash again
    credential_data = (
        str(student_id) +
        str(institution_id) +
        course +
        str(issue_date)
    )

    calculated_hash = hashlib.sha256(
        credential_data.encode()
    ).hexdigest()


    # Compare hashes
    if calculated_hash == stored_hash:

        print("\nCredential Verification: VALID ✅")

    else:

        print("\nCredential Verification: INVALID ❌")


# Close connection
cur.close()
conn.close()

print("\nDatabase connection closed.")

