# Project 1

With this website it is possible to search for books, to get more information about the books and to post a review.

# This project contains the following files:

#    Static
All style data can be found in this folder (created with the help of scss and converted to css)
#    Templates
All html pages can be found in this folder

#    Application.py
This is the main file. This contains all codes that allow people to log in, log out, search for books, post reviews and so on
#    Helpers.py
This file serves as help for application.py and contains login_required
#    Import.py
With this file it is possible to put the books from the csv file in the database

#    books.csv
This file contains all the books
#    requirements.txt
The required downloads are shown in this file

# Small notes (that can also be found in the codes)
In application.py
Clear session is done as follows:
    session["user_id"] = None
    session["username"] = None
session.clear() did not work

In search.html
It was not possible to add the padding via scss, possibly caused by jinja
