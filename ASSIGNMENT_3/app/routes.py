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

ACCESS_KEY = 
SECRET_KEY = 

HOME= 'app'
IMG_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

s3_url = 'https://foodcal.s3.amazonaws.com/'

@webapp.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@webapp.route('/upload', methods=['POST','GET'])
@is_logged_in
def upload():
  if request.method == 'POST':
        # check if the post request has the file part
   if 'files' not in request.files:
            return render_template('upload.html', msg='No Image file Selected')

##################
   files = request.files.getlist('files')

   for file in files:
     filename = file.filename
     _, extension = os.path.splitext(filename)
     username = session['username']

#     if extension not in ALLOWED_EXTENSIONS:
#         msg = 'Incorrect extension'
#         return render_template('upload.html', msg=msg)
        
     if file.filename == '':
        return   render_template('upload.html', msg='No Selected File')
    #filename length should be <50
     if len(file.filename) > 50:
        return   render_template('upload.html', msg='Filename is Too Long!')
     
     else:
       local_path = os.path.join('/tmp', filename)
       file.save(local_path)
#
#    # upload images to s3
       s3 = boto3.client(
            's3',
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY
            )
       bucket_resource = s3
#      s3 = boto3.client('s3')
       s3_path = os.path.join(username, filename)
       s3.upload_file(local_path,
                   s3_config['bucket'],
                   s3_path)

       dynamodb = boto3.resource('dynamodb')
       table = dynamodb.Table('UserData')



# rekognition on images
       rekognition = boto3.client('rekognition')
       response = rekognition.detect_labels(Image={"S3Object": {"Bucket": s3_config['bucket'], "Name": s3_path}}, MaxLabels=4,
                                         MinConfidence=85)
       labels = [{'Confidence': Decimal(str(round(label_prediction['Confidence'], 3))),
               'Name': label_prediction['Name']} for label_prediction in response['Labels']]

    # update tag cloud
       response = table.get_item(
          Key={
            'username': username,
          }
         )

       labels_list = response['Item']['labels_list']
       for label in labels:
         if label['Name'] in labels_list:
            labels_list[label['Name']] += int(1)
         else:
            labels_list[label['Name']] = int(1)

     #update table
       table.update_item(
          Key={
            'username': username,
        },
       UpdateExpression="SET images = list_append(images, :val), labels_list = :val2",
       ExpressionAttributeValues={
            ':val': [{
                'path': s3_path,
                'labels': labels,
            }],
            ':val2': labels_list,
        },
       ReturnValues="UPDATED_NEW"
       )
#
       dynamodb = boto3.resource('dynamodb')
       table = dynamodb.Table('Image')
       response = table.put_item(
       Item={
                          'image_path': s3_path,
                          'image_labels': labels,
                          'username':username

                }
       )
       
       response = table.get_item(
             Key={
                 'username': username,
             }
         )
       
       label_score=[]
       
       for image in response['Item']:
            if ('image_labels' not in image) or (s3_path not in 'image_path'):
               continue

            for value in image['image_labels']:
               label_score.append([value['Name'], value['Confidence']])


       image_name= response['Item']['image_path']
         
       food_names = response['Item']['image_labels']
         
       foods = ['Biryani','Burger','Fried Chicken','Hamburger','Milkshake','Pasta','Pizza','Ramen','Shawarma','Steak','Taco']
         
       for food in foods:
         for food_name in food_names:
           if food in food_name['Name']:
       ################Calories####################
            table = dynamodb.Table('FoodData')
            response = table.query(
             KeyConditionExpression=Key('Id').eq(food)
             )
            
            
            calorie_list = response['Items']
            calories = list(map(itemgetter('calorie'),calorie_list))
            calories = calories[0]
            carbohydrate = list(map(itemgetter('carbohydrate'),calorie_list))
            carbohydrate = carbohydrate[0]
            fat = list(map(itemgetter('fat'),calorie_list))
            fat = fat[0]
            protein = list(map(itemgetter('protein'),calorie_list))
            protein = protein[0]
            
           else:
             calories = 'Sorry! Item not in database'

         #Connect to user database to update calories and get image labels and paths
       table3 = dynamodb.Table('UserData')
       response3 = table3.get_item(
             Key={
                 'username': username,
             }
          )
        
          
       table3.update_item(
                Key={
                  'username': username,
              },
             UpdateExpression="SET Calories = :val1 ",
             ExpressionAttributeValues={
                  ':val1': calories,
              },
             ReturnValues="UPDATED_NEW"
             )
         
                  
       
       # remove local images

       
       return redirect(url_for('detail',s3_path=s3_path))
   
  return render_template('upload.html', msg='Please Upload an Image')



#####Function for details
@webapp.route('/detail/<path:s3_path>')
@is_logged_in
def detail(s3_path):

#####Connect to Image database to get labels and image names
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Image')
    username = session["username"]
    response = table.get_item(
        Key={
            'username': username,
        }
    )
    
    label_score=[]
    for image in response['Item']:
       if ('image_labels' not in image) or (s3_path not in 'image_path'):
          continue

       for value in image['image_labels']:
          label_score.append([value['Name'], value['Confidence']])


    image_name= response['Item']['image_path']
    
    food_names = response['Item']['image_labels']
    
    foods = ['Biryani','Burger','Fried Chicken','Hamburger','Milkshake','Pasta','Pizza','Ramen','Shawarma','Steak','Taco']
    
    for food in foods:
     for food_name in food_names:
      if food in food_name['Name']:
  ################Calories####################
       table = dynamodb.Table('FoodData')
       response = table.query(
        KeyConditionExpression=Key('Id').eq(food)
        )
       
       
    #    calories = response['Items']
    
    #Getting all the values from Food database
       calorie_list = response['Items']
       calories = list(map(itemgetter('calorie'),calorie_list))
       calories = calories[0]
       carbohydrate = list(map(itemgetter('carbohydrate'),calorie_list))
       carbohydrate = carbohydrate[0]
       fat = list(map(itemgetter('fat'),calorie_list))
       fat = fat[0]
       protein = list(map(itemgetter('protein'),calorie_list))
       protein = protein[0]
       
       
#      else:
#       calories = 'Sorry! Item not in database'
    

    #Connect to user database to update calories and get image labels and paths
    table3 = dynamodb.Table('UserData')
    response3 = table3.get_item(
        Key={
            'username': username,
        }
     )
    
    for image in response3['Item']['images']:
      if ('labels' not in image) or (s3_path not in image['path']):
        continue

      for value in image['labels']:
        label_score.append([value['Name'], value['Confidence']])
     
        table3.update_item(
           Key={
             'username': username,
         },
        UpdateExpression="SET Calories = :val1 ",
        ExpressionAttributeValues={
             ':val1': calories,
         },
        ReturnValues="UPDATED_NEW"
        )
             
#
      return render_template('detail.html', username=session['username'], image_name=image_name,label_score=label_score,calories=calories, carbohydrate=carbohydrate,fat=fat,protein=protein)



#Function to show and sort tags
@webapp.route('/show_tag/<string:tag>')
@is_logged_in
def show_tag(tag):

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('UserData')
    username = session["username"]

    response = table.get_item(
        Key={
            'username': username,
        }
    )

    labels_list = response['Item']['labels_list']
    labels_list = sorted(labels_list.items(), key=operator.itemgetter(1), reverse=True)

    # group image paths
    images = []
    tmp = []
    count = 1
    for image in response['Item']['images']:

        has_label = False
        for label in image['labels']:
            if label['Name'] == tag:
                has_label = True

        if not has_label:
            continue

        if count == 4:
            count = 1
            tmp.append(['path'])
            images.append(tmp)
            tmp = []
        else:
            tmp.append(image['path'])
            count = count + 1

    if len(tmp) > 0:
        images.append(tmp)


    return render_template('tag.html', username=session['username'], images=images,
                           labels_list=labels_list[:10], tag=tag)




#Function for all tags/images
@webapp.route('/gallery')
@is_logged_in
def gallery():
    """
    A specialized function to display user's homepage with existing images that are already
    stored in the account.

    :return: Rendered home page.
    """

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('UserData')
    username = session["username"]

    response = table.get_item(
        Key={
            'username': username
        }
    )

    labels_list = response['Item']['labels_list']
    labels_list = sorted(labels_list.items(), key=operator.itemgetter(1), reverse=True)
    
#    dynamodb = boto3.resource('dynamodb')
#    table = dynamodb.Table('Image')
#    username = session["username"]
#
#    response = table.get_item(
#        Key={
#            'username': username
#        }
#    )
##
    images = []
    tmp = []
    count = 1
    for image in response['Item']['images']:
        if count == 4:
            count = 1
            tmp.append(['image_path'])
            images.append(tmp)
            tmp = []
        else:
            tmp.append(['image_path'])
            count = count + 1
    if len(tmp) > 0:
        images.append(tmp)
  

    return render_template('gallery.html', username=session['username'], images=images, labels_list=labels_list[:10])




## for Zappa
if __name__ == '__main__':
    webapp.run()

