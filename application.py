from oauth2client.client import FlowExchangeError
from oauth2client.client import flow_from_clientsecrets
from flask import session as login_session
from flask import make_response
from database_setup import Base, User, Category, Item
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, asc, desc
import random
import string
import requests
import httplib2
import json
from flask import (Flask, render_template, request,
                   redirect, jsonify, url_for, flash)
from functools import wraps


app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Application"

# Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db',
                       connect_args={'check_same_thread': False}
                       )
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def login_required(f):
    """ Defing a login decrator to avoid checks repetition

    Returns:
        login page with session state object
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            flash("You are not allowed to access there")
            return redirect('/login')
    return decorated_function


@app.route('/login')
def showLogin():
    """ Create anti-forgery state token

    Returns:
        login page with session state object
    """
    state = ''.join(random.choice(
        string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """ Connect the user using Google Sign-in

    Returns:
        a welcome message if the process succeed
    """
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    request.get_data()
    code = request.data.decode('utf-8')
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    flash("you are now logged in as %s" % login_session['username'])
    return output


def createUser(login_session):
    """ Create a new user in the database

    Args:
        login_session: session object with user data

    Returns:
        user id
    """
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserID(email):
    """ Get user id

    Args:
        email: string

    Returns:
        a user id for the given email
    """
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/gdisconnect')
def gdisconnect():
    """ DISCONNECT - Revoke a current user's token and reset their login_session

    Returns:
        OnSuccess: home page
        OnFailure: response message
    """
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'

        return redirect('/categories')
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.'), 400)

        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/api/categories')
def categoriesJSON():
    """ View all categories

    Returns:
        a json object with all categories in the database
    """
    categories = session.query(Category).all()
    return jsonify(categories=[category.serialize for category in categories])


@app.route('/api/categories/<int:category_id>')
def categoryJSON(category_id):
    """ View specific category

    Args:
        category_id : int
    Returns:
        a json object with specific category
    """
    category = session.query(Category).filter_by(id=category_id).one()
    return jsonify(category=category.serialize)


@app.route('/api/categories/<int:category_id>/items')
def categoryItemsJSON(category_id):
    """ View category items

    Args:
        category_id : int
    Returns:
        a json object with specific category items
    """
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(CategoryItems=[item.serialize for item in items])


@app.route('/api/categories/<int:category_id>/items/<int:item_id>')
def categoryItemJSON(category_id, item_id):
    """ View specific categor item

    Args:
        category_id : int
        item_id : int
    Returns:
        a json object with specific category item
    """
    category_item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(category_item=category_item.serialize)


@app.route('/')
@app.route('/index')
@app.route('/categories')
def showCategories():
    """ Show all categories

    Returns:
        a HTML page with all categoris and the lates items add to the database
    """
    categories = session.query(Category).order_by(asc(Category.name))
    items = session.query(Item).order_by(desc(Item.id))
    if 'username' not in login_session:
        return render_template('index.html',
                               categories=categories, items=items)
    name = login_session['username']
    return render_template('index.html',
                           categories=categories, items=items, name=name)


#
@app.route('/categories/<int:category_id>/')
@app.route('/categories/<int:category_id>/items/')
def showItems(category_id):
    """ Show category items

    Args:
        category_id : int
    Returns:
        a HTML page with all category items
    """
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    return render_template('items.html', items=items, category=category)


@app.route('/profile')
@login_required
def showUserProfile():
    """ Show user profile

    Returns:
        OnSuccess: HTML page with user info
        OnFailure: Redirt to login page
    """
    name = login_session['username']
    email = login_session['email']
    picture = login_session['picture']
    user = session.query(User).filter_by(email=email).one()
    items = session.query(Item).filter_by(user_id=user.id).all()

    return render_template('profile.html', name=name,
                           email=email, picture=picture, items=items)


@app.route('/categories/<int:category_id>/items/new/', methods=['GET', 'POST'])
@login_required
def newCategoryItem(category_id):
    """ Create a new category item

    Args:
        category_id : int
    Returns:
        a HTML page to create a new category item
    """
    categories = session.query(Category).all()
    category = session.query(Category).filter_by(id=category_id).one()
    if request.method == 'POST':
        selected_category = session.query(Category).filter_by(
            name=request.form['category']).one()
        user_id = getUserID(login_session["email"])
        newItem = Item(title=request.form['title'],
                       description=request.form['description'],
                       year=request.form['year'],
                       poster=request.form['poster'],
                       category_id=selected_category.id,
                       user_id=user_id)
        session.add(newItem)
        session.commit()
        flash('Title %s Successfully Created' % (newItem.title))
        return redirect(url_for('showItems', category_id=category_id))
    else:
        return render_template('newCategoryitem.html',
                               categories=categories, category_id=category_id)


@app.route('/categories/<int:category_id>/items/<int:item_id>/')
def showCategoryItem(category_id, item_id):
    """ Show specific category item

    Args:
        category_id : int
        item_id : int
    Returns:
        a HTML page that shows specific category item
    """
    category = session.query(Category).filter_by(id=category_id).one()
    item = session.query(Item).filter_by(id=item_id).one()
    creator = login_session["username"]
    return render_template('item.html',
                           category_id=category.id, item=item, creator=creator)


@app.route('/categories/<int:category_id>/items/<int:item_id>/edit',
           methods=['GET', 'POST'])
@login_required
def editCategoryItem(category_id, item_id):
    """ Edit a category item

    Args:
        category_id : int
        item_id : int
    Returns:
        a HTML page to edit specific category item
    """
    editedItem = session.query(Item).filter_by(id=item_id).one()
    category = session.query(Category).filter_by(id=category_id).one()
    if login_session['user_id'] != editedItem.user_id:
        return """
        <script>function myFunction()
        {alert('You are not authorized to edit this title.
        Please create your own title in order to edit.');}
        </script><body onload='myFunction()''>
        """
    if request.method == 'POST':
        if request.form['title']:
            editedItem.title = request.form['title']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['year']:
            editedItem.year = request.form['year']
        if request.form['poster']:
            editedItem.poster = request.form['poster']
        session.add(editedItem)
        session.commit()
        flash('Title %s Successfully Edited' % (editedItem.title))
        return redirect(url_for('showItems',
                                category_id=category_id, item_id=item_id))
    else:
        return render_template('editCategoryitem.html',
                               category_id=category_id, item_id=item_id,
                               item=editedItem)


@app.route('/categories/<int:category_id>/items/<int:item_id>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteCategoryItem(category_id, item_id):
    """ Delete a category item

    Args:
        category_id : int
        item_id : int
    Returns:
        a HTML page to delete specific category item
    """
    category = session.query(Category).filter_by(id=category_id).one()
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] != itemToDelete.user_id:
        return """
        <script>function myFunction() {
        alert('You are not authorized to delete this title .
        Please create your own title in order to delete.');}
        </script><body onload='myFunction()''>
        """
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Title %s Successfully Deleted' % (itemToDelete.title))
        return redirect(url_for('showItems', category_id=category_id))
    else:
        return render_template('deleteCategoryItem.html', item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
