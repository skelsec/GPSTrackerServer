from pathlib2 import Path, PurePath
import re

RESET_APP = False
DEBUG = True

###### DEFAULT USERS

DEFAULT_ADMIN_USERS = {}
DEFAULT_ADMIN_USERS['haha@skelsec.com'] = {}
DEFAULT_ADMIN_USERS['haha@skelsec.com']['username'] = 'skelsec'
DEFAULT_ADMIN_USERS['haha@skelsec.com']['password'] = 'supersecret_admin_1'
DEFAULT_ADMIN_USERS['haha@skelsec.com']['roles'] = ['admin']

DEFAULT_USERS = {}
DEFAULT_USERS['info@skelsec.com'] = {}
DEFAULT_USERS['info@skelsec.com']['username'] = 'info'
DEFAULT_USERS['info@skelsec.com']['password'] = 'almaalma'

DEFAULT_USERS['shopping@skelsec.com'] = {}
DEFAULT_USERS['shopping@skelsec.com']['username'] = 'shopping'
DEFAULT_USERS['shopping@skelsec.com']['password'] = 'almaalma'

###### server CONFIG
HOST='0.0.0.0'
PORT=8080


###### LOGGING CONFIG
LOGLEVEL = 'DEBUG'


###### DB CONFIG
SQLALCHEMY_DATABASE_URI = 'mysql://gps:gpsTrackerP@ssW0rd!@localhost:3306/gps2'
SQLALCHEMY_TRACK_MODIFICATIONS = False

###### FOLDERS CONFIG
current_path = PurePath(__file__)
basedir = PurePath(str(current_path.parents[0])) #if you moce config.py to somehwere else then fix this!!

STATIC_DIR = str(basedir.joinpath('bootstrap'))
TEMPLATES_DIR = str(basedir.joinpath('templates'))
SCRIPTS_DIR = str(basedir.joinpath('templates','scripts'))

CSS_DIR = str(basedir.joinpath('templates','css'))





EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+") #https://stackoverflow.com/questions/8022530/python-check-for-valid-email-address

###### GPSTRACKER FUNCTIONALITY CONFIG
TRACKER_SERVER_BASE_URL = 'https://gpstracker.skelsec.com/'
TRACKER_CONFIGURATION_TEMPLATE = str(basedir.joinpath('trackerconfig','config.json'))
TRACKER_BOOTSTRAP_OTP_LENGTH = 8 #in bytes
TRACKER_BOOTSTRAP_REGISTRATION_PERIOD = 1 #weeks
TRACKER_NAME_LENGTH = 5
TRACKER_CA_CERT_FILE = str(basedir.joinpath('certs','cacert.pem'))
TRACKER_CA_KEY_FILE  = str(basedir.joinpath('certs','cakey.pem'))
GPS_MINIMUM_SPEED = 0.5 #km/h
GPS_MAX_SPEED = 300 #km/h 
GPS_MAX_STANDING_TIME = 15*60 #15 minutes in seconds
GPS_FILE_FORMATS = ['GPX','ROUTEINFO']

ANONYMOUS_BOOTSTRAP_QUOTA_EMAIL = 10
ANONYMOUS_BOOTSTRAP_QUOTA_IP = 10
ANONYMOUS_USER_NAME = '1ANON1'

MAX_CONTENT_LENGTH = 16 * 1024 * 102
POST_DATA_MAX_SIZE = 1 * 1024 * 1024

###### EMAIL CONFIG
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_SSL = False
MAIL_USE_TLS = True
MAIL_USERNAME = 'gpstrackeremail@gmail.com'
MAIL_PASSWORD = 'ZZqmpFxN3Bzftv72UB0u'



###### FLASK-SECURITY CONFIG
SECRET_KEY = 'super-secret2342342efq34gqverv'
SECURITY_PASSWORD_HASH = 'sha512_crypt'
SECURITY_PASSWORD_SALT = 'aaaaaaaaaaaaa'
SECURITY_EMAIL_SENDER = 'no-reply@localhost'
SECURITY_CONFIRMABLE = True
SECURITY_REGISTERABLE = True
SECURITY_RECOVERABLE = True
SECURITY_TRACKABLE = True
SECURITY_CHANGEABLE = True




#DO NOT SPECIFY THE FOLLOWING EVER!!!
"""
SERVER_NAME = ''
"""