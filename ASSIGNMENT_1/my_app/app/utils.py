import hashlib, uuid
from datetime import timedelta
from app import webapp
import os
from flask import session
from mysql.connector import Error
from mysql.connector import errorcode
from .obj import object_detection
from .obj.thumbnails import thumbnails
from .database import connect_to_database,  get_db, teardown_db

#User is logged in only 48 hours(User logged in for at least 24 hours)
@webapp.before_request
def make_session_permanent():
    session.permanent = True
    webapp.permanent_session_lifetime = timedelta(hours=48)

#hashfunction for password
def hashed_password(word, salt):
    password = hashlib.sha512(word.encode('utf-8') + salt.encode('utf-8')).hexdigest()
    return password

#save username and password to database
def save_reg(username,password):
    salt = uuid.uuid4().hex
    hashpswd = hashed_password(password, salt)
	
 #connect to database
    cnx = get_db()
    try:
        query = ''' INSERT INTO user (username,password,salt) VALUES (%s, %s, %s)'''
        cnx.cursor().execute(query,(username, hashpswd, salt))
        cnx.commit()
    except mysql.connector.Error as error:
        cnx.rollback()
        return 'Failed to Save'

    #making a user dictionary as part of registration
    ROOT_PATH = os.path.join(os.path.dirname(__file__),'static') #Save in static folder
    PATH_USER = os.path.join(ROOT_PATH,username) #Save user details
    os.mkdir(PATH_USER) #Separate folder for user
    PATH_USER_THUMBNAILS = os.path.join(PATH_USER, 'thumbnails')
    PATH_USER_ORIGINAL = os.path.join(PATH_USER, 'original') #Save uploaded image
    PATH_USER_OBJ = os.path.join(PATH_USER, 'obj') #Objection-detected image
    os.mkdir(PATH_USER_OBJ)
    os.mkdir(PATH_USER_ORIGINAL)
    os.mkdir(PATH_USER_THUMBNAILS)
    return 'Registered successfully'

#Check username from database while logging in	
def check_name(username):
    # Create variables for easy access
    cnx = get_db()
    cursor = cnx.cursor()
    #Get username from database
    query = '''SELECT * FROM user WHERE username = %s'''
    cursor.execute(query, (username,))
    row = cursor.fetchone()
    return row

#Checking password while logging in
def check_password(username, password):
    # Create variables for easy access
    cnx = get_db()
    cursor = cnx.cursor()

     # Check if account exists using MySQL
    query = 'SELECT salt FROM user WHERE (username) = %s'
    cursor.execute(query, (username,))
    salts = cursor.fetchone()
    true_password = hashed_password(password, salts[0])

    query = 'SELECT * FROM user WHERE username = %s AND password = %s'
    cursor.execute(query, (username, true_password))
    # Fetch one record and return result
    return cursor.fetchone()

#Validate login credentials
def validator(username, password):
    if check_name(username) is None:
        return 'Username/Password is Invalidated'
    if check_password(username,password) is None:
        return 'Username/Password is Invalidated'

# If user details exist in database then:
#Function to save uploaded images
def save_file(username, file, filename):
    #save original file
    app_path = os.path.dirname(__file__)
    stat_path = os.path.join(app_path, 'static')
    USER_PATH = os.path.join(stat_path, username)

    ROOT_PATH = os.path.join(USER_PATH, 'original')
    ORIGINAL_PATH = os.path.join(ROOT_PATH,filename)
    file.save(ORIGINAL_PATH)

    #save object-detected file
    OBJ_PATH = os.path.join(USER_PATH, 'obj')
    OBJ_PATH = os.path.join(OBJ_PATH,filename)
   # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>.
    detection_img = object_detection.ap()
    detection_img.img = ORIGINAL_PATH
    detection_img.path = OBJ_PATH
    detection_img.rectangle_image()

    #save thumbnail file
    THUMBNAILS_PATH = os.path.join(USER_PATH, 'thumbnails')
    THUMBNAILS_PATH = os.path.join(THUMBNAILS_PATH, filename)
    thumbnails(ORIGINAL_PATH, THUMBNAILS_PATH)

    # Save file to database
    cnx = get_db()
    cursor = cnx.cursor()
    query = 'SELECT id FROM user WHERE (username) = %s'
    cursor.execute(query, (username,))
    row = cursor.fetchone()
    user_id = int(row[0])

    try:
        query = '''INSERT INTO images (id, imagename, original,obj,thumbnails) VALUES (%s,%s,%s, %s, %s)'''
        cnx.rollback()
        return 'Uploaded successfully'
    except mysql.connector.Error as error:
        cnx.rollback()
        return 'Failed to Save'
    return 'Successfully Uploaded'
