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
from pathlib2 import Path, PurePath
import datetime
from flask_assets import Environment

current_path = PurePath(__file__)
basedir = PurePath(str(current_path.parents[1])) #if you move config.py to somehwere else then fix this!!

app = Flask(__name__)
app.config.from_pyfile(str(basedir.joinpath('config.py')))

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

from gpsDB import User, Role


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


from app.pages.public.controllers import public
app.register_blueprint(public, template_folder=app.config['TEMPLATES_DIR'])

from app.pages.users.controllers import users
app.register_blueprint(users, template_folder=app.config['TEMPLATES_DIR'])

from app.pages.admin.controllers import admin
app.register_blueprint(admin, template_folder=app.config['TEMPLATES_DIR'])

from app.pages.trackers.controllers import trackers
app.register_blueprint(trackers, template_folder=app.config['TEMPLATES_DIR'])

from app.pages.route.controllers import route
app.register_blueprint(route, template_folder=app.config['TEMPLATES_DIR'])
	
@app.before_first_request
def seed():
	if not app.config['RESET_APP']:
		return
			
	try:
		##########################
		app.logger.info('Deleting DB')
		for table in reversed(db.metadata.sorted_tables):
			try:
				app.logger.info('Deleting table: '+str(table)) 
				db.session.execute(table.delete())
				db.session.commit()
			except:
				app.logger.exception('Could not delete table!')
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




from filters import *
from gpsTrackerServer import *

api.add_resource(GPSTracker, '/gpstracker', '/gpstracker/<string:trackerid>')
api.add_resource(GPSPosition, '/gpsposition','/gpsposition/<string:tracker_id>', '/gpsposition/<string:tracker_id>/<string:start_date>/<string:end_date>', '/gpsposition/<string:tracker_id>/<string:start_date>/<string:end_date>/<string:format>/')


