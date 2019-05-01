import os
import requests

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

app = Flask(__name__)


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config['JSON_SORT_KEYS'] = False
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    # Forget any user_id
    session["user_id"] = None
    session["username"] = None

    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session["user_id"] = None
    session["username"] = None

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        hash = generate_password_hash(request.form.get("password"))

        # Check if email is available
        user = db.execute("SELECT email FROM users WHERE email = :email",
               {"email": email}).fetchone()

        # New user
        if user is None:
            db.execute("INSERT INTO users (username, email, hash) VALUES (:username, :email, :hash)",
            {"username": username, "email": email, "hash": hash})
            db.commit()
            flash('You have been succesfully registered')
            return render_template ("login.html")
        # Not a new user
        else:
            flash('An account with this mailadress already exists')
            return render_template("register.html")

        # Make sure the user puts in the right information
        if not request.form.get("username"):
            flash('You must provide an username')
            return render_template("register.html")
        elif not request.form.get("password") or not request.form.get("confirmation"):
            flash('You must provide a password and/or confirm it')
            return render_template("register.html")
        elif request.form.get("password") != request.form.get("confirmation"):
            flash('Your password and confirmation should be the same')
            return render_template("register.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """"Log user in"""

    # Forget any user_id
    session["user_id"] = None
    session["username"] = None

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        email = request.form.get("email")

        # Check if login is valid
        user = db.execute("SELECT * FROM users WHERE email = :email",
               {"email": email}).fetchone()

        # Check if email is valid
        if user is None:
            flash('Please provide an existing email')
            return render_template("login.html")

        # Check if password is valid
        hash = check_password_hash(user.hash, request.form.get("password"))
        if hash == False:
            flash('Please provide the right email and password')
            return render_template("login.html")
        elif hash == True:
            flash('You have been succesfully logged in')
            session["user_id"] = user.user_id
            session["username"] = user.username
            return render_template("search.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session["user_id"] = None
    session["username"] = None

    # Redirect user to homepage
    return render_template("index.html")

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # User can search when logged in
        search = request.form.get("search")
        book_search = '%' + search + '%'

        # Give user an overview of found books
        books = db.execute("SELECT * FROM books WHERE isbn LIKE :book_search OR title LIKE :book_search OR author LIKE :book_search",
                {"book_search": book_search}).fetchall()

        return render_template("search.html", no_books=(len(books) == 0), books=books, search=True)

    else:
        return render_template("search.html", no_books=True, search=False)

@app.route("/book/<int:book_id>", methods=["GET", "POST"])
@login_required
def book(book_id):

    # Check if book exists in database
    book = db.execute("SELECT * FROM books WHERE id = :book_id",
           {"book_id": book_id}).fetchone()

    # Get all reviews from users
    reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id",
              {"book_id": book_id}).fetchall()

    # Get API for additional reviews
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
          params={"key": "kOMuwaYPj5W6YH5YMEeRrw", "isbns": book.isbn}).json()["books"][0]

    # Use API json data
    work_ratings_count = res["work_ratings_count"]
    average_rating = res["average_rating"]

    # User submitted a review
    if request.method == "POST":
        # Get review input
        review = request.form.get("review")
        rating = request.form.get("rating")

        # Check if user has reviewed this book
        user = db.execute("SELECT user_id FROM reviews WHERE user_id = :id AND book_id= :book_id",
               {"id": session['user_id'], "book_id": book_id}).fetchone()

        # If no: Add review to reviews
        if user is None:
            db.execute("INSERT INTO reviews (review, rating, book_id, user_id, username) VALUES (:review, :rating, :book_id, :user_id, :username)",
            {"review": review, "rating": rating, "book_id": book_id, "user_id": session['user_id'], "username": session['username']})
            db.commit()
        # If yes: Don't add review to reviews
        else:
            flash ("You already rated this book and you are not able to alter your decision")
            return render_template("book.html", reviews=reviews, book=book, work_ratings_count=work_ratings_count, average_rating=average_rating, username=session["username"])

        # Render reviews
        flash ("You have succesfully rated this book")
        reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id",
                  {"book_id": book_id}).fetchall()
        return render_template("book.html", reviews=reviews, book=book, work_ratings_count=work_ratings_count, average_rating=average_rating, username=session["username"])

    else:
        # User reached route via GET (as by clicking a link or via redirect)
        return render_template("book.html", reviews=reviews, book=book, work_ratings_count=work_ratings_count, average_rating=average_rating, username=session["username"])

@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):

    # Check if book exists in database
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn",
           {"isbn": isbn}).fetchone()
    if book is None:
        return jsonify({"error": "Your input could not be found in our database"})

    # Get API for additional information
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
          params={"key": "kOMuwaYPj5W6YH5YMEeRrw", "isbns": book.isbn}).json()["books"][0]

    # Use API json data
    work_ratings_count = res["work_ratings_count"]
    average_rating = res["average_rating"]

    # Return information about the book
    return jsonify(
    {
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
        "review_count": work_ratings_count,
        "average_score": float(average_rating)
    })
