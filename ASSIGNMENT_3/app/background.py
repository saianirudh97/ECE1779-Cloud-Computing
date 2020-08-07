from flask import render_template, redirect, url_for, session, request, Response
import os, operator
from app import webapp
from flask import jsonify
from decimal import Decimal
import boto3
from .config import get_db, s3_config
from boto3.dynamodb.conditions import Key, Attr
from .utils import is_logged_in
from operator import itemgetter

@webapp.route('/home')
@is_logged_in
def home():
    username = session['username']
    id = '1';
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('covid')
    response = table.get_item(
             Key={
                 'id': id,
             }
          )

    # list = response['Item']
    conf = response['Item']['conf']
    deaths = response['Item']['deaths']
    recovered = response['Item']['recovered']

    return render_template('home.html', username= username, conf=conf,deaths=deaths,recovered=recovered)
