import os

import requests
from functools import wraps
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

import datetime
import itertools

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///gradebook.db")

@app.route("/")
@login_required
def index():

    lines = db.execute("SELECT * FROM classes WHERE Id = :Id", Id=session["user_id"])
    count = db.execute("SELECT COUNT(class_name) FROM classes WHERE Id = :Id", Id=session["user_id"])


    counts = count[0]["COUNT(class_name)"]

    student_count = []
    student_counts = []

    for i in range(counts):
        student_count.append(db.execute("SELECT COUNT(student_name) FROM students WHERE Id = :Id AND class_name = :class_name",
                    Id=session["user_id"], class_name=lines[i]["class_name"]))

    for j in range(counts):
        student_counts.append(student_count[j][0]["COUNT(student_name)"])

    return render_template("index.html", lines=lines, student_counts=student_counts, counts=counts)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["Hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["Id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)

        elif not request.form.get("confirmation"):
            return apology("please retype password", 403)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 403)

        elif not request.form.get("subject"):
            return apology("select a subject", 403)

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        if len(rows) == 1:
            return apology("Username already exists", 403)

        Hash = generate_password_hash(request.form.get("password"))

        username = request.form.get("username")

        subject = request.form.get("subject")

        db.execute("INSERT INTO users (username, Hash, subject) VALUES (:username, :Hash, :subject)", username=username, Hash=Hash, subject=subject)

        flash('You were successfully registered')
        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/create_class", methods=["GET", "POST"])
def create_class():
    if request.method == "POST":

        if not request.form.get("class_name"):
            return apology("please enter class name", 403)

        rows = db.execute("SELECT * FROM classes WHERE class_name = :class_name AND Id = :Id",
                class_name=request.form.get("class_name"), Id=session["user_id"])

        if rows != []:
            return apology("class already created", 403)

        db.execute("INSERT INTO classes (Id, class_name) VALUES (:Id, :class_name)",
                class_name=request.form.get("class_name"), Id=session["user_id"])
        flash("Class successfully created")
        return redirect("/")
    else:
        return render_template("create_class.html")

@app.route("/add_students", methods=["GET", "POST"])
def add_students():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology ("select a class", 403)
        if not request.form.get("student_name"):
            return apology("enter a student's name", 403)
        rows = db.execute("SELECT * FROM students WHERE Id = :Id AND student_name = :student_name AND class_name = :class_name",
                Id = session["user_id"], student_name=request.form.get("student_name"), class_name=request.form.get("class_name"))
        if rows != []:
            return apology("student already added to class", 403)
        db.execute("INSERT INTO students (Id, student_name, class_name) VALUES (:Id, :student_name, :class_name)",
                Id=session["user_id"], student_name=request.form.get("student_name"), class_name=request.form.get("class_name"))

        lines = db.execute("SELECT * FROM classes WHERE Id = :Id", Id=session["user_id"])
        flash("Student successfully added!")
        return render_template("class_form.html", lines=lines)

    else:
        lines = db.execute("SELECT * FROM classes WHERE Id = :Id", Id=session["user_id"])
        return render_template("class_form.html", lines=lines)

@app.route("/view", methods=["GET", "POST"])
def view():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology ("select a class", 403)

        rows = db.execute("SELECT * FROM students WHERE Id = :Id AND class_name = :class_name",
                Id=session["user_id"], class_name=request.form.get("class_name"))

        class_name = request.form.get("class_name")

        return render_template("class_view.html", rows=rows, class_name=class_name)


    else:
        lines = db.execute("SELECT * FROM classes WHERE Id = :Id", Id=session["user_id"])
        return render_template("view.html", lines=lines)

@app.route("/remove_students", methods=["GET", "POST"])
def remove_students():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology ("select a class", 403)
        if not request.form.get("student_name"):
            return apology("enter a student's name", 403)
        rows = db.execute("SELECT * FROM students WHERE Id = :Id AND student_name = :student_name AND class_name = :class_name",
                Id = session["user_id"], student_name=request.form.get("student_name"), class_name=request.form.get("class_name"))
        if rows == []:
            return apology("student not in class", 403)

        db.execute("DELETE FROM students WHERE Id = :Id AND student_name = :student_name AND class_name = :class_name",
                Id=session["user_id"], student_name=request.form.get("student_name"), class_name=request.form.get("class_name"))

        db.execute("DELETE FROM grades WHERE Id = :Id AND student_name = :student_name AND class_name = :class_name",
                Id=session["user_id"], student_name=request.form.get("student_name"), class_name=request.form.get("class_name"))

        lines = db.execute("SELECT * FROM classes WHERE Id = :Id", Id=session["user_id"])
        flash("Student successfully removed!")
        return render_template("delete_form.html", lines=lines)
    else:
        lines = db.execute("SELECT * FROM classes WHERE Id = :Id", Id=session["user_id"])
        return render_template("delete_form.html", lines=lines)

@app.route("/create_assignment", methods=["GET", "POST"])
def create_assignment():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology ("select a class", 403)
        if not request.form.get("assignment_type"):
            return apology("select an assignment type", 403)
        if not request.form.get("assignment_title"):
            return apology("enter an assignment title")

        rows = db.execute("SELECT * FROM assignments WHERE class_name = :class_name AND Id = :Id AND assignment_title = :assignment_title",
                class_name=request.form.get("class_name"), Id=session["user_id"], assignment_title=request.form.get("assignment_title"))
        if rows != []:
            return apology("assignment already created", 403)

        db.execute("INSERT INTO assignments (Id, class_name, assignment_type, assignment_title) VALUES (:Id, :class_name, :assignment_type, :assignment_title)",
                Id=session["user_id"], class_name=request.form.get("class_name"), assignment_type=request.form.get("assignment_type"), assignment_title=request.form.get("assignment_title"))

        flash("Assignment Successfully Created")
        return redirect("/")
    else:
        lines = db.execute("SELECT * FROM classes WHERE Id = :Id", Id=session["user_id"])
        return render_template("create_assignment.html", lines=lines)

@app.route("/view_assignments", methods=["GET", "POST"])
def view_assignments():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology ("select a class", 403)

        rows = db.execute("SELECT * FROM assignments WHERE Id = :Id AND class_name = :class_name",
                Id=session["user_id"], class_name=request.form.get("class_name"))

        class_name = request.form.get("class_name")

        return render_template("assignment_view.html", rows=rows, class_name=class_name)


    else:
        lines = db.execute("SELECT DISTINCT(class_name) FROM assignments WHERE Id = :Id", Id=session["user_id"])
        return render_template("view_assignments.html", lines=lines)

@app.route("/delete_assignment", methods=["GET", "POST"])
def delete_assignment():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology ("select a class", 403)
        if not request.form.get("assignment_title"):
            return apology("enter an assignment title", 403)
        if not request.form.get("assignment_type"):
            return apology("select an assignment type", 403)

        rows = db.execute("SELECT * FROM assignments WHERE Id = :Id AND assignment_title = :assignment_title AND class_name = :class_name AND assignment_type = :assignment_type",
                Id = session["user_id"], assignment_title=request.form.get("assignment_title"), class_name=request.form.get("class_name"), assignment_type=request.form.get("assignment_type"))
        if rows == []:
            return apology("assignment does not exist", 403)

        db.execute("DELETE FROM assignments WHERE Id = :Id AND assignment_title = :assignment_title AND class_name = :class_name AND assignment_type = :assignment_type",
                Id=session["user_id"], assignment_title=request.form.get("assignment_title"), class_name=request.form.get("class_name"), assignment_type=request.form.get("assignment_type"))

        db.execute("DELETE FROM grades WHERE Id = :Id AND assignment_title = :assignment_title AND class_name = :class_name AND assignment_type = :assignment_type",
                Id=session["user_id"], assignment_title=request.form.get("assignment_title"), class_name=request.form.get("class_name"), assignment_type=request.form.get("assignment_type"))

        lines = db.execute("SELECT * FROM assignments WHERE Id = :Id", Id=session["user_id"])
        flash("Assignment successfully deleted!")
        return render_template("delete_assignment.html", lines=lines)
    else:
        lines = db.execute("SELECT DISTINCT(class_name) FROM assignments WHERE Id = :Id", Id=session["user_id"])
        assignments = db.execute("SELECT DISTINCT(assignment_title) FROM assignments WHERE Id = :Id",
                Id=session["user_id"])
        return render_template("delete_assignment.html", lines=lines, assignments=assignments)

@app.route("/grades", methods=["GET", "POST"])
def grades():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology ("select a class", 403)
        if not request.form.get("assignment_title"):
            return apology("enter an assignment title", 403)
        if not request.form.get("assignment_type"):
            return apology("select an assignment type", 403)

        lists = db.execute("SELECT * FROM assignments WHERE Id = :Id AND assignment_title = :assignment_title AND class_name = :class_name AND assignment_type = :assignment_type",
                Id = session["user_id"], assignment_title=request.form.get("assignment_title"), class_name=request.form.get("class_name"), assignment_type=request.form.get("assignment_type"))
        if lists == []:
            return apology("assignment does not exist", 403)

        assignment_title = request.form.get("assignment_title")
        class_name = request.form.get("class_name")
        assignment_type = request.form.get("assignment_type")

        session["title"] = assignment_title
        session["class_name"] = class_name
        session["type"] = assignment_type

        rows = db.execute("SELECT * FROM students WHERE Id = :Id AND class_name = :class_name", Id=session["user_id"], class_name=request.form.get("class_name"))

        return render_template("enter_grades.html", assignment_title=assignment_title, rows=rows, class_name=class_name, assignment_type=assignment_type)

    else:
        lines = db.execute("SELECT DISTINCT(class_name) FROM grades WHERE Id = :Id", Id=session["user_id"])
        assignments = db.execute("SELECT DISTINCT(assignment_title) FROM assignments WHERE Id = :Id", Id=session["user_id"])
        return render_template("grades.html", lines=lines, assignments=assignments)

@app.route("/enter_grades", methods=["GET", "POST"])
def enter_grades():
    if request.method == "POST":
        grades_list = request.form.getlist("grade")

        students = db.execute("SELECT student_name FROM students WHERE Id = :Id AND class_name = :class_name", Id=session["user_id"], class_name=session["class_name"])
        student_list = []

        for i in students:
            student_list.append(i["student_name"])

        for i in range(len(grades_list)):
            db.execute("INSERT INTO grades (Id, class_name, student_name, assignment_type, assignment_title, grade) VALUES (:Id, :class_name, :student_name, :assignment_type, :assignment_title, :grade)",
                    Id=session["user_id"], class_name=session["class_name"], student_name=student_list[i], assignment_type=session["type"], assignment_title=session["title"], grade=grades_list[i])
        flash("Grades successfully saved")
        return redirect("/")
    else:
        return render_template("enter_grades.html")

@app.route("/grades_class", methods=["GET", "POST"])
def grades_class():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology("Please select a class", 403)

        class_name = request.form.get("class_name")

        assignments = db.execute("SELECT DISTINCT(assignment_title), assignment_type FROM grades WHERE Id = :Id AND class_name = :class_name",
                Id=session["user_id"], class_name=class_name)

        students = db.execute("SELECT DISTINCT(student_name), grade FROM grades WHERE Id = :Id AND class_name = :class_name",
                Id=session["user_id"], class_name=class_name)

        student = db.execute("SELECT DISTINCT(student_name) FROM grades WHERE Id = :Id AND class_name = :class_name",
                Id=session["user_id"], class_name=class_name)

        a = len(assignments)
        s = len(student)

        grades_raw = []
        grades = []

        if a > 1:
            for i in range(a):
                grades_raw.append(db.execute("SELECT student_name, grade FROM grades WHERE Id = :Id AND assignment_title = :assignment_title",
                        Id=session["user_id"], assignment_title=assignments[i]["assignment_title"]))

            for j in range(a):
                for k in range(s):
                    grades.append(grades_raw[j][k]["grade"])

            grades_split = [grades[i:i + s] for i in range(0, len(grades), s)]
            gs = len(grades_split)

            return render_template("grades_classview.html", assignments=assignments, class_name=class_name,
                    students=students, grades_split=grades_split, s=s, gs=gs)

        elif a == 1:
            return render_template("grades_classview1.html", students=students, class_name=class_name, assignments=assignments)


    else:
        lines = db.execute("SELECT DISTINCT(class_name) FROM grades WHERE Id = :Id", Id=session["user_id"])
        return render_template("grades_class.html", lines=lines)


@app.route("/grades_student", methods=["GET", "POST"])
def grades_student():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology("Please select a class", 403)
        if not request.form.get("student_name"):
            return apology("Please enter a student's name", 403)

        student = db.execute("SELECT * FROM students WHERE student_name = :student_name AND class_name = :class_name AND Id = :Id",
                Id=session["user_id"], student_name=request.form.get("student_name"), class_name=request.form.get("class_name"))

        if student == []:
            return apology("student not in class", 403)

        grades = db.execute("SELECT grade FROM grades WHERE student_name = :student_name AND class_name = :class_name AND Id = :Id",
                Id=session["user_id"], student_name=request.form.get("student_name"), class_name=request.form.get("class_name"))

        if grades == []:
            return apology("no grade for this student yet", 403)

        grade = []

        for i in range(len(grades)):
            grade.append(grades[i]["grade"])

        avg_grade = float(sum(grade)/len(grade))

        assignments = db.execute("SELECT DISTINCT(assignment_title), assignment_type FROM grades WHERE Id = :Id AND class_name = :class_name",
                Id=session["user_id"], class_name=request.form.get("class_name"))

        return render_template("grades_studentview.html", student=student, grades=grades, assignments=assignments, avg_grade=avg_grade)

    else:
        lines = db.execute("SELECT DISTINCT(class_name) FROM grades WHERE Id = :Id", Id=session["user_id"])
        return render_template("grades_student.html", lines=lines)

@app.route("/student_grade", methods=["GET", "POST"])
def student_grade():
    if request.method == "POST":
        if not request.form.get("class_name"):
            return apology("Please select a class", 403)
        if not request.form.get("student_name"):
            return apology("Please enter a student's name", 403)
        if not request.form.get("assignment_title"):
            return apology("enter an assignment title", 403)
        if not request.form.get("assignment_type"):
            return apology("select an assignment type", 403)
        if not request.form.get("grade"):
            return apology("enter a grade", 403)
        check = db.execute("SELECT * FROM grades WHERE Id = :Id AND class_name = :class_name AND student_name = :student_name AND assignment_title = :assignment_title AND assignment_type = :assignment_type",
                Id=session["user_id"], class_name=request.form.get("class_name"), student_name=request.form.get("student_name"), assignment_title=request.form.get("assignment_title"), assignment_type=request.form.get("assignment_type"))

        if check == []:
            db.execute("INSERT INTO grades (Id, class_name, student_name, assignment_title, assignment_type, grade) VALUES (:Id, :class_name, :student_name, :assignment_title, :assignment_type, :grade)",
                Id=session["user_id"], class_name=request.form.get("class_name"), student_name=request.form.get("student_name"), assignment_title=request.form.get("assignment_title"), assignment_type=request.form.get("assignment_type"), grade=request.form.get("grade"))
        else:
            db.execute("UPDATE grades SET grade = :grade WHERE Id = :Id AND student_name = :student_name AND class_name = :class_name AND assignment_title = :assignment_title",
                    grade=request.form.get("grade"), Id=session["user_id"], student_name=request.form.get("student_name"), class_name=request.form.get("class_name"), assignment_title=request.form.get("assignment_title"))

        flash("Grade successfully altered")
        return redirect("/")

    else:
        lines = db.execute("SELECT DISTINCT(class_name) FROM grades WHERE Id = :Id", Id=session["user_id"])
        assignments = db.execute("SELECT DISTINCT(assignment_title) FROM grades WHERE Id = :Id", Id=session["user_id"])
        return render_template("student_grade.html", lines=lines, assignments=assignments)