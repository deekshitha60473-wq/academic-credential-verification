
from flask import Flask, render_template, request, url_for, send_file

import sqlite3
import hashlib
import uuid
import os
import qrcode

from werkzeug.utils import secure_filename

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization


app = Flask(__name__)

DATABASE = "credentials.db"

UPLOAD_FOLDER = "static/uploads"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# -------------------------------------------------
# LOAD PRIVATE KEY
# -------------------------------------------------

with open("private_key.pem", "rb") as key_file:

    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None
    )


# -------------------------------------------------
# LOAD PUBLIC KEY
# -------------------------------------------------

with open("public_key.pem", "rb") as key_file:

    public_key = serialization.load_pem_public_key(
        key_file.read()
    )


# -------------------------------------------------
# CHECK FILE TYPE
# -------------------------------------------------

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# -------------------------------------------------
# DATABASE
# -------------------------------------------------

def init_db():

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credential_id TEXT UNIQUE,
            student_name TEXT,
            student_id TEXT,
            course TEXT,
            institution TEXT,
            year TEXT,
            certificate_number TEXT,
            photo_filename TEXT,
            hash_value TEXT,
            status TEXT,
            signature TEXT
        )
    """)

    cursor.execute(
        "PRAGMA table_info(credentials)"
    )

    columns = [
        column[1]
        for column in cursor.fetchall()
    ]


    # Add photo column if missing

    if "photo_filename" not in columns:

        cursor.execute("""
            ALTER TABLE credentials
            ADD COLUMN photo_filename TEXT
        """)


    # Add signature column if missing

    if "signature" not in columns:

        cursor.execute("""
            ALTER TABLE credentials
            ADD COLUMN signature TEXT
        """)


    connection.commit()

    connection.close()


# -------------------------------------------------
# HOME
# -------------------------------------------------

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# -------------------------------------------------
# ISSUE PAGE
# -------------------------------------------------

@app.route(
    "/issue",
    methods=["GET"]
)
def issue_page():

    return render_template(
        "issue.html"
    )


# -------------------------------------------------
# ISSUE CREDENTIAL
# -------------------------------------------------

@app.route(
    "/issue",
    methods=["POST"]
)
def issue_credential():

    student_name = request.form.get(
        "student_name",
        ""
    )

    student_id = request.form.get(
        "student_id",
        ""
    )

    course = request.form.get(
        "course",
        ""
    )

    institution = request.form.get(
        "institution",
        ""
    )

    year = request.form.get(
        "year",
        ""
    )

    certificate_number = request.form.get(
        "certificate_number",
        ""
    )


    print("NEW CREDENTIAL DATA:")

    print("Student:", student_name)

    print("Student ID:", student_id)

    print("Course:", course)

    print("Institution:", institution)

    print("Year:", year)

    print("Certificate:", certificate_number)


    # -------------------------------------------------
    # PHOTO
    # -------------------------------------------------

    photo = request.files.get(
        "photo"
    )

    photo_filename = ""


    if photo and photo.filename:

        if allowed_file(
            photo.filename
        ):

            original_filename = secure_filename(
                photo.filename
            )

            photo_filename = (
                uuid.uuid4().hex[:10]
                + "_"
                + original_filename
            )

            os.makedirs(
                UPLOAD_FOLDER,
                exist_ok=True
            )

            photo_path = os.path.join(
                UPLOAD_FOLDER,
                photo_filename
            )

            photo.save(
                photo_path
            )

        else:

            return (
                "Invalid photo format. "
                "Please upload JPG, JPEG or PNG."
            )


    # -------------------------------------------------
    # CREDENTIAL ID
    # -------------------------------------------------

    credential_id = (
        "CRED-"
        + uuid.uuid4().hex[:10].upper()
    )


    # -------------------------------------------------
    # DATA TO PROTECT
    # -------------------------------------------------

    data = (
        credential_id
        + student_name
        + student_id
        + course
        + institution
        + year
        + certificate_number
        + photo_filename
    )


    # -------------------------------------------------
    # SHA-256 HASH
    # -------------------------------------------------

    hash_value = hashlib.sha256(
        data.encode("utf-8")
    ).hexdigest()


    # -------------------------------------------------
    # DIGITAL SIGNATURE
    # -------------------------------------------------

    signature = private_key.sign(

        data.encode("utf-8"),

        padding.PSS(
            mgf=padding.MGF1(
                hashes.SHA256()
            ),
            salt_length=padding.PSS.MAX_LENGTH
        ),

        hashes.SHA256()
    )


    signature_hex = signature.hex()


    # -------------------------------------------------
    # CREATE STATIC FOLDER
    # -------------------------------------------------

    os.makedirs(
        "static",
        exist_ok=True
    )


    # -------------------------------------------------
    # QR CODE
    # -------------------------------------------------

    qr_data = (
    "http://172.21.6.118:5000/verify?credential_id="
    + credential_id
)

    qr = qrcode.make(
        qr_data
    )

    qr_filename = (
        credential_id
        + ".png"
    )

    qr_path = os.path.join(
        "static",
        qr_filename
    )

    qr.save(
        qr_path
    )


    # -------------------------------------------------
    # DATABASE
    # -------------------------------------------------

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()


    cursor.execute("""
        INSERT INTO credentials
        (
            credential_id,
            student_name,
            student_id,
            course,
            institution,
            year,
            certificate_number,
            photo_filename,
            hash_value,
            status,
            signature
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        credential_id,
        student_name,
        student_id,
        course,
        institution,
        year,
        certificate_number,
        photo_filename,
        hash_value,
        "VALID",
        signature_hex
    ))


    connection.commit()

    connection.close()


    # -------------------------------------------------
    # RESULT PAGE
    # -------------------------------------------------

    return render_template(

        "result.html",

        credential_id=credential_id,

        student_name=student_name,

        student_id=student_id,

        course=course,

        institution=institution,

        year=year,

        certificate_number=certificate_number,

        photo_filename=photo_filename,

        hash_value=hash_value,

        qr_filename=qr_filename
    )


# -------------------------------------------------
# VERIFY CREDENTIAL
# -------------------------------------------------

@app.route(
    "/verify",
    methods=["GET", "POST"]
)
def verify_credential():

    credential_id = request.args.get(
        "credential_id"
    )


    if request.method == "POST":

        credential_id = request.form.get(
            "credential_id"
        )


    if not credential_id:

        return render_template(
            "verify.html",
            result="not_found",
            credential_id=""
        )


    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM credentials
        WHERE credential_id = ?
        """,
        (credential_id,)
    )


    credential = cursor.fetchone()

    connection.close()


    if credential is None:

        return render_template(
            "verify.html",
            result="not_found",
            credential_id=credential_id
        )


    # -------------------------------------------------
    # RECREATE ORIGINAL DATA
    # -------------------------------------------------

    data = (
        credential["credential_id"]
        + credential["student_name"]
        + credential["student_id"]
        + credential["course"]
        + credential["institution"]
        + credential["year"]
        + credential["certificate_number"]
        + credential["photo_filename"]
    )


    # -------------------------------------------------
    # VERIFY DIGITAL SIGNATURE
    # -------------------------------------------------

    signature_valid = False


    try:

        if credential["signature"]:

            public_key.verify(

                bytes.fromhex(
                    credential["signature"]
                ),

                data.encode("utf-8"),

                padding.PSS(
                    mgf=padding.MGF1(
                        hashes.SHA256()
                    ),
                    salt_length=padding.PSS.MAX_LENGTH
                ),

                hashes.SHA256()
            )

            signature_valid = True


    except Exception:

        signature_valid = False


    # -------------------------------------------------
    # REVOKED
    # -------------------------------------------------

    if credential["status"] == "REVOKED":

        return render_template(
            "verify.html",

            result="revoked",

            credential=credential,

            credential_id=credential_id,

            signature_valid=signature_valid
        )


    # -------------------------------------------------
    # FINAL RESULT
    # -------------------------------------------------

    if signature_valid:

        result = "valid"

    else:

        result = "fake"


    return render_template(

        "verify.html",

        result=result,

        credential=credential,

        credential_id=credential_id,

        signature_valid=signature_valid
    )


# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------

@app.route(
    "/dashboard"
)
def dashboard():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()


    cursor.execute("""
        SELECT *
        FROM credentials
        ORDER BY id DESC
    """)


    credentials = cursor.fetchall()

    connection.close()


    return render_template(
        "dashboard.html",
        credentials=credentials
    )


# -------------------------------------------------
# REVOKE CREDENTIAL
# -------------------------------------------------

@app.route(
    "/revoke",
    methods=["GET", "POST"]
)
def revoke_credential():

    result = None

    credential = None


    if request.method == "POST":

        credential_id = request.form.get(
            "credential_id",
            ""
        )


        connection = sqlite3.connect(
            DATABASE
        )

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()


        cursor.execute(
            """
            SELECT *
            FROM credentials
            WHERE credential_id = ?
            """,
            (credential_id,)
        )


        credential = cursor.fetchone()


        if credential is None:

            result = "not_found"

        else:

            cursor.execute(
                """
                UPDATE credentials
                SET status = 'REVOKED'
                WHERE credential_id = ?
                """,
                (credential_id,)
            )

            connection.commit()

            result = "revoked"


        connection.close()


    return render_template(
        "revoke.html",
        result=result,
        credential=credential
    )


# -------------------------------------------------
# DOWNLOAD PDF
# -------------------------------------------------

@app.route(
    "/download/<credential_id>"
)
def download_credential(
    credential_id
):

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM credentials
        WHERE credential_id = ?
        """,
        (credential_id,)
    )


    credential = cursor.fetchone()

    connection.close()


    if credential is None:

        return (
            "Credential not found",
            404
        )


    pdf_filename = (
        credential_id
        + ".pdf"
    )

    pdf_path = os.path.join(
        "static",
        pdf_filename
    )


    pdf = canvas.Canvas(
        pdf_path,
        pagesize=A4
    )


    width, height = A4


    pdf.setFont(
        "Helvetica-Bold",
        20
    )


    pdf.drawCentredString(
        width / 2,
        height - 80,
        "ACADEMIC CREDENTIAL"
    )


    pdf.setFont(
        "Helvetica",
        12
    )


    y = height - 130


    fields = [

        (
            "Credential ID",
            credential["credential_id"]
        ),

        (
            "Student Name",
            credential["student_name"]
        ),

        (
            "Student ID",
            credential["student_id"]
        ),

        (
            "Course",
            credential["course"]
        ),

        (
            "Institution",
            credential["institution"]
        ),

        (
            "Graduation Year",
            credential["year"]
        ),

        (
            "Certificate Number",
            credential["certificate_number"]
        )
    ]


    for label, value in fields:

        pdf.drawString(
            70,
            y,
            label + ": " + value
        )

        y -= 30


    pdf.setFont(
        "Helvetica-Bold",
        12
    )


    pdf.drawString(
        70,
        y,
        "SHA-256 Hash:"
    )


    y -= 20


    pdf.setFont(
        "Helvetica",
        8
    )


    pdf.drawString(
        70,
        y,
        credential["hash_value"]
    )


    y -= 40


    pdf.setFont(
        "Helvetica-Bold",
        12
    )


    pdf.drawString(
        70,
        y,
        "Status: "
        + credential["status"]
    )


    pdf.save()


    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=pdf_filename
    )


# -------------------------------------------------
# START APPLICATION
# -------------------------------------------------

if __name__ == "__main__":

    init_db()


    os.makedirs(
        UPLOAD_FOLDER,
        exist_ok=True
    )


    os.makedirs(
        "static",
        exist_ok=True
    )


    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )

