import urllib

from flask_wtf import FlaskForm
from wtforms import Form, StringField, PasswordField, SubmitField , IntegerField, DecimalField
from wtforms.validators import DataRequired, EqualTo, Length ,NumberRange
from flask_wtf.file import FileField, FileRequired, FileAllowed
from pathvalidate import sanitize_filename


class LoginForm_Manager(Form):

    # This is the login form which takes a username and password, and has a submit button
    # This login form is displayed on our main page, and in run_man.py the form inputs
    # are tested against our registered user data to authenticate and log them in

	username = StringField('Username', validators=[DataRequired(),Length(min=2, max=30)])
	password = PasswordField('Password', validators=[DataRequired()])
	submit = SubmitField('Sign In')

class Max_Threshold(FlaskForm):
	#This form is used to get maximum threshold value from admin to change the auto scaling policy
	max_thresh = DecimalField('Max_Threshold', places=2,render_kw={"placeholder": " Load Balancer Upper Limit"}, validators=[DataRequired(),NumberRange(min=1, max=100)])
	submit = SubmitField('Update')

class Min_Threshold(FlaskForm):
	#This form is used to get minimum threshold value from admin to change the auto scaling policy
	min_thresh = DecimalField('Min_Threshold',places=2,render_kw={"placeholder": " Load Balancer Lower Limit"}, validators=[DataRequired(),NumberRange(min=1, max=100)])
	submit = SubmitField('Update')

class Add_Ratio(FlaskForm):
	#This form is used to get addition ratio from admin to change the auto scaling policy
	add_r = DecimalField('Add_Ratio',places=2,render_kw={"placeholder": " Load Balancer Increase Ratio"}, validators=[DataRequired(),NumberRange(min=1, max=10)])
	submit = SubmitField('Update')

class Red_Ratio(FlaskForm):
	#This form is used to get reduction ratio from admin to change the auto scaling policy
	red_r = DecimalField('Red_Ratio',places=2,render_kw={"placeholder": " Load Balancer Decrease Ratio"}, validators=[DataRequired(),NumberRange(min=1, max=10)])
	submit = SubmitField('Update')
