from functools import wraps
from flask import g, session, redirect, url_for
from app import webapp

db_config = {'user': 'root',
             'password': 'Myrules123',
             'host': 'user.conjtasju4z8.us-east-1.rds.amazonaws.com',
             'database': 'userdb'}

def connect_to_database():
    return mysql.connector.connect(
        user=db_config['user'],
        password=db_config['password'],
        host=db_config['host'],
        database=db_config['database'])


def get_db():
    if 'db' not in g:
        g.db = connect_to_database()
    return g.db
                
             
s3_config = {
    'bucket': 'foodcal',
    'url': 'https://foodcal.s3.amazonaws.com/'
}

@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
