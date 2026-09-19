
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

    # Record failed verification
    cur.execute("""
        INSERT INTO verification_records
        (credential_id, result)
        VALUES (%s, %s)
    """, (credential_id, "NOT_FOUND"))

    conn.commit()


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


    # Verify credential
    if calculated_hash == stored_hash and status == "ACTIVE":

        result = "VALID"

        print("\nCredential Verification: VALID ✅")

    else:

        result = "INVALID"

        print("\nCredential Verification: INVALID ❌")


    # Store verification result
    cur.execute("""
        INSERT INTO verification_records
        (credential_id, result)
        VALUES (%s, %s)
    """, (credential_id, result))

    conn.commit()

    print("Verification record saved successfully!")


# Close connection
cur.close()
conn.close()

print("\nDatabase connection closed.")

