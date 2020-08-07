from flask import Flask
import os
webapp = Flask(__name__)
webapp.secret_key = os.urandom(20)

from app import main
