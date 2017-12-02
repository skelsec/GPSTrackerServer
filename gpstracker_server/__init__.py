import os
import platform
import logging
import logging.handlers
import jinja2
from flask_bootstrap import Bootstrap

from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore
from flask_security import login_required, current_user
from flask_security.utils import encrypt_password

from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_mail import Mail
import datetime
from flask_assets import Environment
from pathlib2 import Path, PurePath


app = Flask(__name__)
app.config.from_envvar('GPSTRACKERCONFIG')


###### FOLDERS CONFIG
current_path = PurePath(__file__)
basedir = PurePath(str(current_path.parents[0]))

###### API CONFIG
if 'TRACKER_CONFIGURATION_TEMPLATE' not in app.config:
	app.config['TRACKER_CONFIGURATION_TEMPLATE'] = str(basedir.joinpath('trackerconfig','config.json'))
TEMPLATES_DIR = str(basedir.joinpath('templates'))
SCRIPTS_DIR = str(basedir.joinpath('templates').joinpath('scripts'))
CSS_DIR = str(basedir.joinpath('templates').joinpath('css'))

app.config.update(
    PLATFORM_OS     = platform.system(),
    TEMPLATES_DIR   = TEMPLATES_DIR,
    SCRIPTS_DIR     = SCRIPTS_DIR,
    CSS_DIR         = CSS_DIR

)

# Assets

assets = Environment(app)


#This is to get the templates directory from the config file
my_loader = jinja2.ChoiceLoader([
    app.jinja_loader,
    jinja2.FileSystemLoader(app.config['TEMPLATES_DIR']),
])
app.jinja_loader = my_loader




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


app.logger.info(app.config)    

##########################
###### cross-origin HTTP request settings
CORS(app)
##########################
mail = Mail(app)
api = Api(app)
db = SQLAlchemy(app)
Bootstrap(app)

#setting up tables, users for first run
if 'GPSTRACKERSERVER_FIRSTRUN' in os.environ:		
	try:
		with app.app_context():
			from gpsDB import *
			##########################
			app.logger.info('Creating DB') 
			db.create_all()
			##########################
			app.logger.info('Setting up administrator user')  
			user_datastore.create_role(name='admin')
			if app.config['DEFAULT_ADMIN_USERS'] is not None:
				for email in app.config['DEFAULT_ADMIN_USERS']:
					user_datastore.create_user(username=app.config['DEFAULT_ADMIN_USERS'][email]['username'], email=email,
							password=encrypt_password(app.config['DEFAULT_ADMIN_USERS'][email]['password']), roles=app.config['DEFAULT_ADMIN_USERS'][email]['roles'])
					user_datastore.commit()	
			
			if app.config['DEFAULT_USERS'] is not None:
				for email in app.config['DEFAULT_USERS']:
					user_datastore.create_user(username=app.config['DEFAULT_USERS'][email]['username'], email=email,
							password=encrypt_password(app.config['DEFAULT_USERS'][email]['password']), confirmed_at=datetime.datetime.utcnow())
					user_datastore.commit()	
			
			app.logger.info('Done setup!')    
	except Exception as e:
		print 'Exception when setting up adminn  users! ' + str(e)
		app.logger.exception('a')


from gpsDB import User, Role


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


from .pages.public.controllers import public
app.register_blueprint(public, template_folder=app.config['TEMPLATES_DIR'])

from .pages.users.controllers import users
app.register_blueprint(users, template_folder=app.config['TEMPLATES_DIR'])

from .pages.admin.controllers import admin
app.register_blueprint(admin, template_folder=app.config['TEMPLATES_DIR'])

from .pages.trackers.controllers import trackers
app.register_blueprint(trackers, template_folder=app.config['TEMPLATES_DIR'])

from .pages.route.controllers import route
app.register_blueprint(route, template_folder=app.config['TEMPLATES_DIR'])
	





from filters import *
from .gpsTrackerServer import *

api.add_resource(GPSTracker, '/gpstracker', '/gpstracker/<string:trackerid>')
api.add_resource(GPSPosition, '/gpsposition','/gpsposition/<string:tracker_id>', '/gpsposition/<string:tracker_id>/<string:start_date>/<string:end_date>', '/gpsposition/<string:tracker_id>/<string:start_date>/<string:end_date>/<string:format>/')


