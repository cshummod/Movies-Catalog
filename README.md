# Movies Catalog v1.0

## Overview
In this project, I built a Flask App that manage a Movies Catalog.
Authenticated users through Google Sign-In can Add Titles to existing categories 
also, they can Edit/Delete their own titles. The application interface designed using 
Bootstrap 4 and Font-Awesome.

## Database Schema
Movies Catalog database has three tables:
- User
  - id -> integer (Primary Key)
  - name -> string
  - email -> string
  - picture -> string

- Category
  - id -> integer (Primary Key)
  - name -> string

- Item
  - id -> integer (Primary Key)
  - title -> string
  - year -> integer
  - poster -> string
  - description -> string
  - dateOfRegistration -> DATETIME
  - category_id -> forign key
  - user_id -> forign key

## Requirements 
1. Python 2/3
2. Flask
3. SQLalchemy
4. OAuth2client

## Setup
1. Download/Clone the repository
2. Install Python 2/3
3. Install the required modules by running the following command
   
   `pip install flask sqlalchemy oauth2client`

4. Inside login.html enter your GOOGLE CLIENT ID
   
5. From your google console page download the client_secrets.json
   and place it inside the project dirctory

6. Setup the database by running the following command

   `python database_setup.py`

7. Seed the database with categories by running the following command

   `python seed.py`

8.  Run the application 
   
   `python application.py`

9. In your web browser open localhost:5000


## API
This project provieds endpoints for:
1. View all categories 

`/api/categories`

2. View specific category 

`/api/categories/<int:category_id>`

3. View category items 

`/api/categories/<int:category_id>/items`

4. View specific item 

`/api/categories/<int:category_id>/items/<int:item_id>`


## Contributors
Mohammed Mahdi Ibrahim

## Support
For any related questions about the tool you can contact me at wmm@hotmail.it
