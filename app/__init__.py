import logging
import logging.handlers
from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore
from flask_security import login_required, current_user

from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_mail import Mail
from pathlib2 import Path, PurePath


p = Path(__file__)
basedir = str(p.parents[1])


pr = PurePath(basedir)
template_dir =str(pr.joinpath('templates'))
app = Flask(__name__, template_folder=template_dir)
app.config.from_pyfile('config.py')
print app.config



#### LOGGING SETUP
handler = logging.handlers.SysLogHandler(address = '/dev/log')
formatter = logging.Formatter('%(module)s.%(funcName)s: %(message)s')
handler.setFormatter(formatter)

if app.config['LOGLEVEL'] == 'DEBUG' or app.debug:
	handler.setLevel(logging.DEBUG)
	app.logger.setLevel(logging.DEBUG)
elif app.config['LOGLEVEL'] == 'INFO':
	handler.setLevel(logging.INFO)
	app.logger.setLevel(logging.INFO)


##########################
###### cross-origin HTTP request settings
CORS(app)
##########################
mail = Mail(app)
api = Api(app)
db = SQLAlchemy(app)

from gpsDB import gpsposition, gpsjsondata, gpstracker, User, Role


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)
	
@app.before_first_request
def seed():
	if not app.config['RESET_APP']:
		return
			
	try:
		print 'Creating DB!'
		db.create_all()
		print 'Setting up administrator user'
		user_datastore.create_role(name='admin')
		user_datastore.create_user(username='skelsec', email='haha@skelsec.com',
						password='supersecret_admin_1', roles=['admin'])
		user_datastore.commit()
		print 'Done setup!'
	except Exception as e:
		print 'Exception when setting up adminn  users! ' + str(e)
		app.logger.exception('a')





from gpsTrackerServer import GPSTracker, GPSTrackerConfig, GPSPosition



api.add_resource(GPSTracker, '/gpstracker')
api.add_resource(GPSTrackerConfig, '/gpstrackerconfig/<string:trackerid>')
api.add_resource(GPSPosition, '/gpsposition','/gpsposition/<string:tracker_name>', '/gpsposition/<string:tracker_name>/<string:start_date>/<string:end_date>')


