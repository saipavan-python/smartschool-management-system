# ================= IMPORTS =================

from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# ================= LOAD ENV =================

load_dotenv()

# ================= APP CONFIG =================

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret")

# ================= DATABASE CONNECTION =================
db = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME", "smartschool")
)

cur = db.cursor(dictionary=True)


# ================= LOGIN =================
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    uid = request.form["user_id"].strip()
    pw = request.form["password"].strip()

    cur.execute("SELECT * FROM users WHERE user_id=%s AND password=%s", (uid, pw))
    user = cur.fetchone()

    if not user:
        return "Invalid Login"

    session["user"] = user["user_id"]
    session["role"] = user["role"]

    return redirect("/" + user["role"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= ADMIN =================
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/")
    return render_template("admin_dashboard.html")

# => ADD STUDENT 
@app.route("/admin/add_student", methods=["POST"])
def add_student():
    if session.get("role") != "admin":
        return redirect("/")

    name = request.form["name"]
    class_name = request.form["class"]
    phone = request.form["phone"]

    try:
        cur.execute("""
            SELECT user_id FROM users
            WHERE user_id LIKE 'STU%'
            ORDER BY CAST(SUBSTRING(user_id,4) AS UNSIGNED) DESC
            LIMIT 1
        """)
        last = cur.fetchone()
        new_number = int(last["user_id"][3:]) + 1 if last else 1001

        student_id = f"STU{new_number}"
        parent_id = "PAR" + student_id

        cur.execute("INSERT INTO students VALUES (%s,%s,%s,%s)",
                    (student_id, name, class_name, phone))

        cur.execute("INSERT INTO parents VALUES (%s,%s)",
                    (parent_id, student_id))

        cur.execute("INSERT INTO users VALUES (%s,'student','student')",
                    (student_id,))

        cur.execute("INSERT INTO users VALUES (%s,'parent','parent')",
                    (parent_id,))

        db.commit()
        flash("Student Added Successfully!")

    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/admin")

# =>ADD TEACHER
@app.route("/admin/add_teacher", methods=["POST"])
def add_teacher():
    if session.get("role") != "admin":
        return redirect("/")

    name = request.form["name"]
    subject = request.form["subject"]

    try:
        cur.execute("""
            SELECT user_id FROM users
            WHERE user_id LIKE 'TCH%'
            ORDER BY CAST(SUBSTRING(user_id,4) AS UNSIGNED) DESC
            LIMIT 1
        """)
        last = cur.fetchone()
        new_number = int(last["user_id"][3:]) + 1 if last else 101

        teacher_id = f"TCH{new_number}"

        cur.execute("INSERT INTO teachers VALUES (%s,%s,%s)",
                    (teacher_id, name, subject))

        cur.execute("INSERT INTO users VALUES (%s,'teacher','teacher')",
                    (teacher_id,))

        db.commit()
        flash("Teacher Added Successfully!")

    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/admin")

# =>PROMOTE
@app.route("/admin/promote", methods=["POST"])
def promote():
    if session.get("role") != "admin":
        return redirect("/")

    from_class = request.form["from_class"]
    to_class = request.form["to_class"]

    cur.execute("UPDATE students SET class=%s WHERE class=%s",
                (to_class, from_class))

    db.commit()
    flash("Students Promoted Successfully!")

    return redirect("/admin")

# ================= TEACHER =================
@app.route("/teacher")
def teacher():
    if session.get("role") != "teacher":
        return redirect("/")

    tid = session["user"]

    cur.execute("SELECT subject FROM teachers WHERE teacher_id=%s", (tid,))
    teacher = cur.fetchone()

    cur.execute("SELECT student_id,name FROM students")
    students = cur.fetchall()

    return render_template("teacher_dashboard.html",
                           teacher_subject=teacher["subject"],
                           students=students)

@app.route("/teacher/add_marks", methods=["POST"])
def add_marks():
    if session.get("role") != "teacher":
        return redirect("/")

    student_id = request.form["student_id"]
    marks = request.form["marks"]

    tid = session["user"]
    cur.execute("SELECT subject FROM teachers WHERE teacher_id=%s", (tid,))
    subject = cur.fetchone()["subject"]

    try:
        cur.execute("""
            INSERT INTO marks(student_id,subject,internal,mid,final)
            VALUES (%s,%s,%s,0,0)
            ON DUPLICATE KEY UPDATE internal=%s
        """, (student_id, subject, marks, marks))

        db.commit()
        flash("Marks Saved Successfully!")

    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/teacher")
# ==> TEACHER UPLOAD NOTES
@app.route("/teacher/upload_notes", methods=["POST"])
def upload_notes():
    if session.get("role") != "teacher":
        return redirect("/")

    class_name = request.form["class_name"]
    subject = request.form["subject"]
    chapter = request.form["chapter"]
    file = request.files["file"]

    if file.filename == "":
        flash("No file selected!")
        return redirect("/teacher")

    filename = secure_filename(file.filename)

    upload_folder = os.path.join("static", "notes")
    os.makedirs(upload_folder, exist_ok=True)

    file.save(os.path.join(upload_folder, filename))

    try:
        cur.execute("""
            INSERT INTO notes(class_name, subject, chapter, file_name)
            VALUES (%s, %s, %s, %s)
        """, (class_name, subject, chapter, filename))
        db.commit()
        flash("Notes Uploaded Successfully!")
    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/teacher")


# ==> TEACHER ADD ATTENDANCE 
@app.route("/teacher/add_attendance", methods=["POST"])
def add_attendance():
    if session.get("role") != "teacher":
        return redirect("/")

    student_id = request.form.get("student_id")
    date = request.form.get("date")
    status = request.form.get("status")

    if not student_id or not date or not status:
        flash("All attendance fields are required!")
        return redirect("/teacher")

    try:
        cur.execute("""
            INSERT INTO attendance(student_id, date, status)
            VALUES (%s, %s, %s)
        """, (student_id, date, status))

        db.commit()
        flash("Attendance Saved Successfully!")

    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/teacher")
# ==> TEACHER SEND ANNOUNCEMENT
@app.route("/teacher/send_announcement", methods=["POST"])
def send_announcement():
    if session.get("role") != "teacher":
        return redirect("/")

    class_name = request.form.get("class_name")
    message = request.form.get("message")

    if not class_name or not message:
        flash("All announcement fields are required!")
        return redirect("/teacher")

    try:
        cur.execute("""
            INSERT INTO announcements(class_name, message)
            VALUES (%s, %s)
        """, (class_name, message))

        db.commit()
        flash("Announcement Sent Successfully!")

    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/teacher")
# ==> TEACHER ADD WEEKLY TEST
@app.route("/teacher/add_weekly_test", methods=["POST"])
def add_weekly_test():
    if session.get("role") != "teacher":
        return redirect("/")

    student_id = request.form["student_id"]
    marks = request.form["marks"]

    tid = session["user"]
    cur.execute("SELECT subject FROM teachers WHERE teacher_id=%s", (tid,))
    subject = cur.fetchone()["subject"]

    try:
        cur.execute("""
            INSERT INTO weekly_tests(student_id, subject, marks)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE marks=%s
        """, (student_id, subject, marks, marks))

        db.commit()
        flash("Weekly Test Marks Saved Successfully!")

    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/teacher")


# ================= STUDENT ===========
@app.route("/student")
def student():
    if session.get("role") != "student":
        return redirect("/")

    sid = session["user"]

    # Student Info
    cur.execute("SELECT * FROM students WHERE student_id=%s", (sid,))
    stu = cur.fetchone()

    # Marks
    cur.execute("""
        SELECT subject, internal, mid, final,
        (internal+mid+final) AS total
        FROM marks WHERE student_id=%s
    """, (sid,))
    marks = cur.fetchall()

    # Attendance %
    cur.execute("SELECT COUNT(*) as total FROM attendance WHERE student_id=%s", (sid,))
    total_days = cur.fetchone()["total"]

    cur.execute("""
        SELECT COUNT(*) as present FROM attendance
        WHERE student_id=%s AND status='Present'
    """, (sid,))
    present_days = cur.fetchone()["present"]

    attendance_percent = round((present_days/total_days)*100, 2) if total_days > 0 else 0

    # Study Materials 
    cur.execute("""
        SELECT subject, chapter, file_name
        FROM notes
        WHERE class_name=%s
    """, (stu["class"],))
    notes = cur.fetchall()

    # Weekly Tests
    cur.execute("""
        SELECT subject, marks
        FROM weekly_tests
        WHERE student_id=%s
    """, (sid,))
    weekly_tests = cur.fetchall()


    # Class + Global announcements
    cur.execute("""
        SELECT message, created_at
        FROM announcements
        WHERE class_name=%s OR class_name='All'
        ORDER BY created_at DESC
    """, (stu["class"],))
    announcements = cur.fetchall()

    # Add holidays inside announcements
    cur.execute("SELECT date, reason FROM holidays")
    holidays = cur.fetchall()

    for h in holidays:
        announcements.append({
            "message": f"Holiday on {h['date']} - {h['reason']}",
            "created_at": h["date"]
        })

    # Sort latest first
    announcements = sorted(
    announcements,
    key=lambda x: str(x["created_at"]),
    reverse=True
)

    # Timetable
    cur.execute("""
        SELECT day, time, subject
        FROM timetable
        WHERE class_name=%s
    """, (stu["class"],))
    timetable = cur.fetchall()

    # Holidays
    cur.execute("SELECT date, reason FROM holidays ORDER BY date DESC")
    holidays = cur.fetchall()

    return render_template("student_dashboard.html",
                           student_name=stu["name"],
                           student_class=stu["class"],
                           marks=marks,
                           attendance_percent=attendance_percent,
                           notes=notes,
                           weekly_tests=weekly_tests,
                           announcements=announcements,
                           timetable=timetable,
                           holidays=holidays)


# ================= PARENT =================
@app.route("/parent")
def parent():
    if session.get("role") != "parent":
        return redirect("/")

    pid = session["user"]

    # Get student ID from parent table
    cur.execute("SELECT student_id FROM parents WHERE parent_id=%s", (pid,))
    parent_data = cur.fetchone()

    if not parent_data:
        return redirect("/logout")

    sid = parent_data["student_id"]

    # Get student info
    cur.execute("SELECT * FROM students WHERE student_id=%s", (sid,))
    stu = cur.fetchone()

    if not stu:
        return redirect("/logout")

    # = MARKS
    cur.execute("""
        SELECT subject,
        (internal + mid + final) AS total
        FROM marks
        WHERE student_id=%s
    """, (sid,))
    marks = cur.fetchall()

    #  ATTENDANCE 
    cur.execute("""
        SELECT COUNT(*) as total,
        SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id=%s
    """, (sid,))
    att = cur.fetchone()

    attendance = 0
    if att and att["total"]:
        present = att["present"] if att["present"] else 0
        attendance = round((present / att["total"]) * 100, 2)

    #  WEEKLY TEST AVG 
    cur.execute("""
        SELECT subject,
        ROUND(AVG(marks),2) as avg_marks
        FROM weekly_tests
        WHERE student_id=%s
        GROUP BY subject
    """, (sid,))
    weekly_avg = cur.fetchall()
    

    #announcements

    cur.execute("""
        SELECT message, created_at
        FROM announcements
        WHERE class_name=%s OR class_name='All'
        ORDER BY created_at DESC
    """, (stu["class"],))
    announcements = cur.fetchall()

    cur.execute("SELECT date, reason FROM holidays")
    holidays = cur.fetchall()

    for h in holidays:
        announcements.append({
            "message": f"Holiday on {h['date']} - {h['reason']}",
            "created_at": h["date"]
        })

    announcements = sorted(
    announcements,
    key=lambda x: str(x["created_at"]),
    reverse=True
)

    return render_template(
        "parent_dashboard.html",
        student_name=stu["name"],
        student_class=stu["class"],
        marks=marks,
        attendance=attendance,
        weekly_avg=weekly_avg,
        announcements=announcements
    )


# ================= PRINCIPAL =================
@app.route("/principal")
def principal():
    if session.get("role") != "principal":
        return redirect("/")

    # Overview
    cur.execute("SELECT COUNT(*) as c FROM students")
    total_students = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM teachers")
    total_teachers = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(DISTINCT class) as c FROM students")
    total_classes = cur.fetchone()["c"]

    # Always show all students 
    cur.execute("SELECT student_id, name, class FROM students")
    students = cur.fetchall()

    # Teachers
    cur.execute("SELECT teacher_id, name, subject FROM teachers")
    teachers = cur.fetchall()

    # Holidays
    cur.execute("SELECT date, reason FROM holidays ORDER BY date DESC")
    holidays = cur.fetchall()

    return render_template(
        "principal_dashboard.html",
        total_students=total_students,
        total_teachers=total_teachers,
        total_classes=total_classes,
        students=students,
        teachers=teachers,
        holidays=holidays
    )

# VIEW STUDENT BY ID

@app.route("/principal/student")
def view_student():
    if session.get("role") != "principal":
        return redirect("/")

    student_id = request.args.get("student_id")

    if not student_id:
        flash("Please enter Student ID")
        return redirect("/principal")

    cur.execute("SELECT student_id, name, class FROM students WHERE student_id=%s",
                (student_id,))
    stu = cur.fetchone()

    if not stu:
        flash("Student Not Found!")
        return redirect("/principal")

    cur.execute("""
        SELECT subject, internal, mid, final,
        (internal + mid + final) AS total
        FROM marks
        WHERE student_id=%s
    """, (student_id,))
    marks = cur.fetchall()

    return render_template(
        "student_dashboard.html",
        student_name=stu["name"],
        student_class=stu["class"],
        marks=marks
    )

# DELETE STUDENT

@app.route("/delete_student/<student_id>")
def delete_student(student_id):
    if session.get("role") != "principal":
        return redirect("/")

    try:
        cur.execute("DELETE FROM students WHERE student_id=%s", (student_id,))
        cur.execute("DELETE FROM users WHERE user_id=%s", (student_id,))
        db.commit()
        flash("Student Deleted Successfully!")
    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/principal")

# ADD TIMETABLE

@app.route("/add_timetable", methods=["POST"])
def add_timetable():
    if session.get("role") != "principal":
        return redirect("/")

    class_name = request.form.get("class")
    day = request.form.get("day")
    time = request.form.get("time")
    subject = request.form.get("subject")

    if not class_name or not day or not time or not subject:
        flash("All timetable fields are required!")
        return redirect("/principal")

    try:
        cur.execute("""
            INSERT INTO timetable(class_name, day, time, subject)
            VALUES (%s, %s, %s, %s)
        """, (class_name, day, time, subject))

        db.commit()
        flash("Timetable Added Successfully!")

    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/principal")


# ADD HOLIDAY

@app.route("/add_holiday", methods=["POST"])
def add_holiday():
    if session.get("role") != "principal":
        return redirect("/")

    date = request.form["date"]
    reason = request.form["reason"]

    try:
        cur.execute("INSERT INTO holidays(date, reason) VALUES (%s, %s)",
                    (date, reason))
        db.commit()
        flash("Holiday Added Successfully!")
    except Exception as e:
        db.rollback()
        return f"Database Error: {str(e)}"

    return redirect("/principal")




if __name__ == "__main__":
    app.run(debug=True)
