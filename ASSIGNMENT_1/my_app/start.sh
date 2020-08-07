#./venv/bin/gunicorn --bind 0.0.0.0:5000 --workers=1 --access-logfile access.log --error-logfile error.log app:webapp
#. start.sh
#source start.sh

cd
cd ./Desktop/my_app
source ./venv/bin/activate
sudo ufw allow 5000
gunicorn --bind 0.0.0.0:5000 wsgi:webapp
#  Compiler reads one source file from command line argument
#  Output to standard output



