import datetime
import time
import boto3

#from app import webapp
from flask import g
import mysql.connector
from datetime import datetime, timedelta

AMI_ID = 'ami-0f083145b29f27cfe'
KEY_NAME = 'ece1779_users'
SEC_GRP  = 'launch-wizard-2'
SEC_GRP_ID = 'sg-03f8910f1c2b7ed0b'
INST_TYPE = 't2.micro'
ELB_NAME = 'my-load-balancer'
S3_BUCKET = 'ece1779-a2-f2019'

db_config = {'user': 'root',
             'password': 'uoftece1779',
             'host': 'ece1779-db.cdekek3rruh9.us-east-1.rds.amazonaws.com',
             'database': 'ece1779_a2'}

def connect_to_database():
    return mysql.connector.connect(user=db_config['user'],
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   database=db_config['database'])

def get_db():

    db = connect_to_database()

    return db

def register_inst_elb(ids):
    elb = boto3.client('elb')
    response = elb.register_instances_with_load_balancer(
        LoadBalancerName= 'my-load-balancer',Instances=ids,)

    waiter = elb.get_waiter('instance_in_service')
    waiter.wait(LoadBalancerName = 'my-load-balancer',Instances=ids)
    print(response)


def deregister_inst_elb(ids):
    elb = boto3.client('elb')
    response = elb.deregister_instances_from_load_balancer(
        LoadBalancerName = 'my-load-balancer',Instances=ids)
    waiter = elb.get_waiter('instance_deregistered')
    waiter.wait(LoadBalancerName = 'my-load-balancer',Instances=ids)
    print(response)

def spinup_instance(num_worker) :
    #  create the in
    ec2 = boto3.resource('ec2')
    ec2.create_instances(

        ImageId = AMI_ID,
        MinCount=1,
        MaxCount=num_worker,
        KeyName = KEY_NAME,
        SecurityGroups=[SEC_GRP,],
        SecurityGroupIds=[SEC_GRP_ID,],
        InstanceType = INST_TYPE,
        Monitoring={'Enabled': True}
    )

    ids = []
    instances = ec2.instances.filter(Filters=[{'Name': 'image-id', 'Values': 'ami-0f083145b29f27cfe'},
                                              {'Name': 'instance-state-name', 'Values': ['running', 'pending']} ])


    
    for instance in instances:
        print(instance.id)
        ids.append({'InstanceId': instance.id})

    register_inst_elb(ids)
    print("Instance addition success")



def spindown_instance(num_worker):

    ids = []
    ids2 = []

    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'image-id', 'Values': 'ami-0f083145b29f27cfe'},
                                              {'Name': 'instance-state-name', 'Values': ['running']}])

    print("shutdown instances :",instances)
    for idx,instance in enumerate(instances,1):
        ids.append(instance.id)
        ids2.append({'InstanceId': instance.id})
        if idx == num_worker:
            break

    ec2.instances.filter(InstanceIds=ids).terminate()

    deregister_inst_elb(ids2)

    print("Instance removal success")





while True:

    cnx = get_db()
    cursor = cnx.cursor()
    query = '''SELECT * FROM auto_scale'''
    cursor.execute(query)
    row = cursor.fetchone()

    max_thresh = row[1]
    min_thresh = row[2]
    add_r = row[3]
    red_r = row[4]
    auto_toggle = row[5]
 
    if auto_toggle:
        # create connection to ec2
        print("Automatic scaling enabled ")
        ec2 = boto3.resource('ec2')

        instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running','pending']}
            ,{'Name': 'image-id', 'Values': 'ami-0f083145b29f27cfe'}])


        cpu_stats_1 = []
        ids = []

        for instance in instances:

            ids.append(instance.id)
            
            client = boto3.client('cloudwatch')

            # get cpu statistics in 1 minute(60s)

            cpu_1 = client.get_metric_statistics(
                Period=60,
                StartTime=datetime.utcnow() - timedelta(seconds=2 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=1 * 60),
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',  # Unit='Percent',
                Statistics=['Average'],
                Dimensions=[{'Name': 'InstanceId',
                             'Value': instance.id}]
            )

            
            for point in cpu_1['Datapoints']:

                
                load = round(point['Average'], 2)
                cpu_stats_1.append(load)
               
        print("length of ids:::", len(ids))
        num_workers = len(cpu_stats_1)
        print("length of cpu_stats_1:::", num_workers)
        add_instance_num = 0 
        red_instance_num = 0 

        if num_workers != 0 :
            average_load = sum(cpu_stats_1)/num_workers
        else:
            average_load = 0 # need to check this out 

        print(cpu_stats_1)
        print("final avg load",average_load)
        print("num_workers" ,num_workers)

    ######################## Adding instances logic ######################

        if average_load > max_thresh: 
            add_instance_num = int(num_workers * add_r - num_workers)

            print("instances to be added",add_instance_num)

        if (add_instance_num + num_workers) > 10 or (len(ids) + add_instance_num) >10 :
            print("Too many to add")
            add_instance_num = min(max(0,(10 - num_workers)),(10-len(ids)))

        if add_instance_num >0:
            spinup_instance(add_instance_num)
            print("Adding {} Instances".format(add_instance_num))


    ######################## Removing  instances logic ######################    
        if average_load <= min_thresh:
            red_instance_num = int(num_workers - num_workers / red_r )
            print("instance to be reduced", red_instance_num)
            if (num_workers-red_instance_num) <1:
                red_instance_num = num_workers - 1 

        if red_instance_num >0:
            spindown_instance(red_instance_num)
            print("after sanity check number to be reduced", red_instance_num)
    

    else:
        print("Manual mode")

    time.sleep(30)
    cnx.commit() ## to terminate session so that during next iteration we can get updated results

