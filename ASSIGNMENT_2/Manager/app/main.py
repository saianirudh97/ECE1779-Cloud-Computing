from flask import session, request, render_template, redirect, url_for, flash, logging, send_from_directory
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import Form, StringField, PasswordField, SubmitField , IntegerField, DecimalField, TextAreaField, validators
from wtforms.validators import DataRequired, EqualTo, Length ,NumberRange
from app import webapp
import boto3
from datetime import datetime, timedelta
from operator import itemgetter
from .database import connect_to_database,  get_db, teardown_db
import time


AMI_ID = 'ami-080bb209625b6f74f' # new py3.7 AMI created and changed RDS to ece1779a2
KEY_NAME = 'managerdb'
SEC_GRP  = 'launch-wizard-4'
SEC_GRP_ID = 'sg-0734af3e61c07d3da'
INST_TYPE = 't2.micro'
ELB_NAME = 'load1'
S3_BUCKET = 'cloudimage'
S3_KEY = "AKIAJILADA25DFOKCQUQ"
S3_SECRET = "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"
S3_LOCATION = 'http://{}.s3.amazonaws.com/'.format(S3_BUCKET)

#Form = FlaskForm

#Login Form
class LoginForm_Manager(Form):

    username = StringField('Username', validators=[DataRequired(),Length(min=2, max=30)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

#Autoscale form
class Autoscale_Settings(Form):

    max_thresh = DecimalField('Max_Threshold', places=2,render_kw={"placeholder": " Load Balancer Upper Limit"}, validators=[DataRequired(),NumberRange(min=1, max=100)])
    min_thresh = DecimalField('Min_Threshold',places=2,render_kw={"placeholder": " Load Balancer Lower Limit"}, validators=[DataRequired(),NumberRange(min=1, max=100)])
    add_r = DecimalField('Add_Ratio',places=2,render_kw={"placeholder": " Load Balancer Increase Ratio"}, validators=[DataRequired(),NumberRange(min=1, max=10)])
    red_r = DecimalField('Red_Ratio',places=2,render_kw={"placeholder": " Load Balancer Decrease Ratio"}, validators=[DataRequired(),NumberRange(min=1, max=10)])
    

@webapp.route('/',methods=['POST', 'GET'])
def main():
    return redirect(url_for('login'))


# This handles the user logins, and the homepage is served from here
@webapp.route('/login',methods=['POST', 'GET'])
def login():

    form = LoginForm_Manager(request.form)
    if request.method == 'POST':
        
        #Get Form Fields
        username = request.form['username']
        password = request.form['password']

        if username != 'admin' or password != 'pass123':
            error = 'Invalid login'
            return render_template('login.html', error = error)

        else:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
    
    return render_template('login.html')


# Do not allow log out when not logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please log in', 'danger')
            return redirect(url_for('login'))
    return wrap

#Lists all running instances
@webapp.route('/home',methods=['POST', 'GET'])
@is_logged_in
def home(): 

    # create connection to ec2
    ec2 = boto3.resource('ec2')
    #filter =[{'Name': 'instance-state-name', 'Values': ['running','pending','stopping','shutting down']},{'Name': 'image-id', 'Values': [AMI_ID]}]
    #instances = ec2.instances.filter(Filters = [filter])

    instances = ec2.instances.all()

    cnx = get_db()
    cursor = cnx.cursor()
    query = '''SELECT * FROM auto_scale'''
    cursor.execute(query)
    row = cursor.fetchone()

    auto = row[5]

    return render_template("home.html", auto = auto, instances=instances)


#Display details about a specific instance.
@webapp.route('/view/<id>',methods=['GET'])
def ec2_view(id):

    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(id)
    client = boto3.client('cloudwatch')

    metric_name = 'CPUUtilization'


    namespace = 'AWS/EC2'
    statistic = 'Average'



    cpu = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    cpu_stats = []


    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        cpu_stats.append([time,point['Average']])

    cpu_stats = sorted(cpu_stats, key=itemgetter(0))


    
    namespace = 'AWS/ELB'
    statistic = 'Sum'
    metric_name = 'RequestCount'
    

    http_req = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName= metric_name,
        Namespace= namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )


    http_req_stats = []

    for point in http_req['Datapoints']:


        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        http_req_stats.append([time,point[statistic]])

        http_req_stats = sorted(http_req_stats, key=itemgetter(0))
        print("http_req_stats:",http_req_stats)



    return render_template("view.html",title="Instance Info",
                           instance=instance,
                           cpu_stats=cpu_stats,
                           http_req_stats =http_req_stats)

  
@webapp.route('/summary',methods=['GET'])
@is_logged_in
# Display an HTML summary of all ec2 instances
def ec2_summary():
    ec2 = boto3.resource('ec2')
    client = boto3.client('cloudwatch')

    metric_name = 'CPUUtilization'
    namespace = 'AWS/EC2'
    statistic = 'Average'



    cpu = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'ImageId', 'Value': AMI_ID}]
    )

    cpu_stats = []
    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        cpu_stats.append([time,point['Average']])

    cpu_stats = sorted(cpu_stats, key=itemgetter(0))

    namespace = 'AWS/ELB'
    statistic = 'Sum'
    metric_name = 'RequestCount'

    http = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],

    )

    http_req_stats = []
    for point in http['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        http_req_stats.append([time,point['Sum']])

    http_req_stats = sorted(http_req_stats, key=itemgetter(0))


    namespace = 'AWS/ELB'
    statistic = 'Average'
    metric_name = 'UnHealthyHostCount'

    workers = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,
        Statistics=[statistic],
    )

    num_workers_stats = []
    for point in workers['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        num_workers_stats.append([time,point['Average']])

    num_workers_stats = sorted(num_workers_stats, key=itemgetter(0))


    return render_template("summary.html",
                           cpu_stats=cpu_stats,
                           http_req_stats=http_req_stats,
                           num_workers_stats=num_workers_stats)


@webapp.route('/delete/<id>',methods=['POST'])
# Terminate a EC2 instance
def ec2_destroy(id):
    # create connection to ec2
    ec2 = boto3.resource('ec2')
    ec2.instances.filter(InstanceIds=[id]).terminate()

    return redirect(url_for('home'))  

def register_inst_elb(ids):
    # funtion to register newly spun instances to ELB
    elb = boto3.client('elb')
    response = elb.register_instances_with_load_balancer(
        LoadBalancerName = 'load1',
        Instances=ids,)


def deregister_inst_elb(ids):
    # funtion to deregister  instances from ELB
    elb = boto3.client('elb')
    response = elb.deregister_instances_from_load_balancer(
        LoadBalancerName = 'load1',
        Instances=ids,)

# Start a new EC2 instance
@webapp.route('/create',methods=['GET'])
def ec2_create():
    
    ec2 = boto3.resource('ec2')
    ec2.create_instances(
        ImageId = AMI_ID,
        MinCount=1,
        MaxCount=1,
        KeyName = KEY_NAME,
        SecurityGroups = [SEC_GRP,],
        SecurityGroupIds = [SEC_GRP_ID,],
        InstanceType = INST_TYPE,
        Monitoring = {'Enabled': True})

    instances = ec2.instances.filter(Filters=[{'Name': 'image-id', 'Values': [AMI_ID]},
                                         {'Name': 'instance-state-name', 'Values': ['running', 'pending']}, ])
    ids = []
    for instance in instances:
        ids.append({'InstanceId': instance.id})
    register_inst_elb(ids)
    return redirect(url_for('home'))  


#To display and update autoscale settings
@webapp.route('/autoscale',methods=['POST', 'GET'])
def autoscale():


    form =  Autoscale_Settings(request.form)

    #Update autoscale settings
    if request.method == 'POST':
           
        #Get Form Fields
        max_thresh = request.form['max_thresh']
        min_thresh = request.form['min_thresh']
        add_r = request.form['add_r']
        red_r = request.form['red_r']
        
        cnx = get_db()

        query = "UPDATE auto_scale SET max_threshold = %s, min_threshold = %s, add_ratio = %s, red_ratio = %s WHERE id_scaling = 1"
        cnx.cursor().execute(query,(max_thresh, min_thresh, add_r, red_r))
        cnx.commit()

        flash("Autoscale settings updated", "success")
        return render_template('autoscale.html', max_thresh = max_thresh, min_thresh = min_thresh,
                                             add_r = add_r, red_r = red_r)

    #Get current autoscale settings
    cnx = get_db()
    cursor = cnx.cursor()
    query = '''SELECT * FROM auto_scale'''
    cursor.execute(query)
    row = cursor.fetchone()

    max_thresh = row[1]
    min_thresh = row[2]
    add_r = row[3]
    red_r = row[4]

    return render_template('autoscale.html', max_thresh = max_thresh, min_thresh = min_thresh,
                                             add_r = add_r, red_r = red_r)
#Manual mode, no autoscaling
@webapp.route('/manual_mode',methods=['POST', 'GET'])
@is_logged_in
def manual_mode():

    cnx = get_db()

    query = "UPDATE auto_scale SET auto_toggle = 0 WHERE id_scaling = 1"
    cnx.cursor().execute(query)
    cnx.commit()

    flash("Switched to Manual Mode", 'success')
    return redirect(url_for('home'))


#Auto mode, do autoscaling
@webapp.route('/auto_mode',methods=['POST', 'GET'])
@is_logged_in
def auto_mode():

    cnx = get_db()

    query = "UPDATE auto_scale SET auto_toggle = 1 WHERE id_scaling = 1"
    cnx.cursor().execute(query)
    cnx.commit()

    flash("Switched to Auto Mode", 'success')

    return redirect(url_for('home'))



#Delete all data
@webapp.route('/killall',methods=['POST', 'GET'])
@is_logged_in
def killall():

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)
    bucket.objects.all().delete()

    cnx = get_db()

    query1 = "SET FOREIGN_KEY_CHECKS = 0 "
    query2 = "TRUNCATE TABLE user"
    query3 = "TRUNCATE TABLE Images"
    query4 = "SET FOREIGN_KEY_CHECKS = 1"

    cnx.cursor().execute(query1)
    cnx.cursor().execute(query2)
    cnx.cursor().execute(query3)
    cnx.cursor().execute(query4)
   
    cnx.commit()
  

    flash("All S3 Data and RDS data deleted", 'success')
    return redirect(url_for('home'))


#User logout
@webapp.route('/logout',methods=['GET','POST'])
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))
