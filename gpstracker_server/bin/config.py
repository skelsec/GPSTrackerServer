import re

RESET_APP = False
DEBUG = True

###### DEFAULT USERS

DEFAULT_ADMIN_USERS = {}
DEFAULT_ADMIN_USERS['admin@example.com'] = {}
DEFAULT_ADMIN_USERS['admin@example.com']['username'] = 'admin'
DEFAULT_ADMIN_USERS['admin@example.com']['password'] = 'adminspassword'
DEFAULT_ADMIN_USERS['admin@example.com']['roles'] = ['admin']

DEFAULT_USERS = {}
DEFAULT_USERS['user@example.com'] = {}
DEFAULT_USERS['user@example.com']['username'] = 'user'
DEFAULT_USERS['user@example.com']['password'] = 'password'

DEFAULT_USERS['user2@example.com'] = {}
DEFAULT_USERS['user2@example.com']['username'] = 'user2'
DEFAULT_USERS['user2@example.com']['password'] = 'password2'

###### server CONFIG
HOST='0.0.0.0'
PORT=8080


###### LOGGING CONFIG
LOGLEVEL = 'DEBUG'


###### DB CONFIG
SQLALCHEMY_DATABASE_URI        = 'sqlite:///gps.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False



EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+") #https://stackoverflow.com/questions/8022530/python-check-for-valid-email-address

###### GPSTRACKER FUNCTIONALITY CONFIG
TRACKER_SERVER_BASE_URL = 'https://gpstracker.example.com/'
#TRACKER_CONFIGURATION_TEMPLATE = str(basedir.joinpath('trackerconfig','config.json')) # uncomment this is you wish to use your own template
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
MAIL_SERVER   = 'smtp.gmail.com'
MAIL_PORT     = 587
MAIL_USE_SSL  = False
MAIL_USE_TLS  = True
MAIL_USERNAME = 'outgoing@example.com'
MAIL_PASSWORD = 'smtppassword'



###### FLASK-SECURITY CONFIG
SECRET_KEY             = 'super-secret'
SECURITY_PASSWORD_HASH = 'sha512_crypt'
SECURITY_PASSWORD_SALT = 'aaaaaaaaaaaaa'
SECURITY_EMAIL_SENDER  = 'no-reply@localhost'
SECURITY_CONFIRMABLE   = True
SECURITY_REGISTERABLE  = True
SECURITY_RECOVERABLE   = True
SECURITY_TRACKABLE     = True
SECURITY_CHANGEABLE    = True




#DO NOT SPECIFY THE FOLLOWING EVER!!!
"""
SERVER_NAME = ''
"""
