#import hashlib, uuid, os, operator
from app import webapp
from datetime import timedelta
import sys
import os
from decimal import Decimal
from flask import Flask, jsonify, Response, flash
from functools import wraps
from flask import logging, send_from_directory
from flask import request, render_template, redirect, session, url_for, g
from passlib.hash import sha256_crypt
# from wand.image import Image
import boto3
from boto3.dynamodb.conditions import Key, Attr
from .config import db_config, get_db, s3_config,teardown_db
from wtforms import Form, StringField, PasswordField, TextAreaField, validators
from boto3.dynamodb.conditions import Key
import base64

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

HOME = 'app'
IMG_FOLDER = 'static'
ALLOWED_EXTENSIONS = set(['.png', '.jpg', '.jpeg'])


@webapp.before_request
def make_session_permanent():
    session.permanent = True
    webapp.permanent_session_lifetime = timedelta(hours=48)
    
    
#Function for logging in  
@webapp.route('/login', methods=['GET','POST'])
def login():

   if 'Authenticated' in session:  #Check if already signed-in
         return redirect(url_for('home'))
   msg = ''
   if request.method == 'POST':
       #Get Form Fields
       username = request.form['username']
       password_check = request.form['password']
       table = dynamodb.Table('UserData')

       response = table.get_item(Key = {'username' : username})

       if 'Item' in response:
           
           password = response['Item']['password']

           if sha256_crypt.verify(password_check, password):

               session['logged_in'] = True
               session['username'] = username
               flash('You are now logged in', 'success')
               return redirect(url_for('home'))

           else:
               error = 'Invalid login'
               return render_template('login.html', msg = error)

       else:
           error = 'Username not found'
           return render_template('login.html', msg = error)
            
   return render_template('login.html')

def is_logged_in(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if 'username' not in session or session['username'] == '':
        return redirect(url_for('main'))
    return f(*args, **kwargs)
  return decorated_function

#Function for logging out  
@webapp.route('/logout',methods=['GET','POST'])
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


class RegisterForm(Form):
      username = StringField('Username', [validators.Length(min = 4, max = 25)])
      password = PasswordField('Password', [
      validators.DataRequired(),
      validators.EqualTo('repassword', message = 'Passwords do not match')
       ])
      repassword = PasswordField('Confirm Password')

#Function for registration
@webapp.route('/register',methods =['GET','POST'])
def register():
  form = RegisterForm(request.form)
  if request.method == 'POST' and form.validate():
      username = form.username.data
      password = sha256_crypt.encrypt(str(form.password.data))
      
      table = dynamodb.Table('UserData')
      response = table.put_item(
      Item={
                         'username': username,
                         'password': password,
                         'images': [],
                         'Calories': '0',
                         'labels_list': {},
                         'Timestamp':  'ISO 8601'
                     }
                )
#      putItem_User(username = username, password = password)
      return render_template('login.html',username=username)
      
  return render_template("register.html", form = form)
  
@webapp.route('/api/register', methods=['GET'])
def script():
      return render_template("api_register.html")

  #API:
@webapp.route('/api/register', methods=['POST'])
def api_register():
      rules = [lambda s: any(x.isupper() for x in s),  # must have at least one uppercase
               lambda s: any(x.islower() for x in s),  # must have at least one lowercase
               lambda s: any(x.isdigit() for x in s),  # must have at least one digit
               lambda s: len(s) >= 8,  # must be at least 8 characters
               lambda s: len(s) <= 17  # must be at most 7 characters
               ]
      # Output message if something goes wrong...
      msg = ''
      # Check if "username", "password" and "email" POST requests exist (user submitted form)
      if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
          # check the availability of username
          if check_name(request.form['username']) is not None:
              msg = 'Choose Another  Username Please!'
              return jsonify(status='register-error', msg = msg,state = 406)
          if len(request.form['username']) > 30:
              msg = 'Username is too long!'
              return jsonify(status='register-error', msg = msg, state = 406)
          if not all(rule(request.form['password']) for rule in rules):
              msg = 'Password is not Accepted!'
              return jsonify(status='register-error', msg = msg, state = 406)
          else:
              username = request.form['username']
              password = request.form['password']
              save_reg(username,password)
              msg = 'Successful Registered'
              return jsonify(status='Accepted', msg = msg, state = 200)
      elif request.method == 'POST':
          # Form is empty... (no POST data)
          msg = 'Please fill out the form!'
          return jsonify(status='register-error',msg = msg, state = 406)
# for Zappa
#if __name__ == '__main__':
#    application.run()
