#!/usr/bin/env python
from app import db
from sqlalchemy.dialects.mysql import DOUBLE
from flask_security import UserMixin, RoleMixin

import datetime
from dateutil.parser import parse

# Create a table to support a many-to-many relationship between Users and Roles
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
	__tablename__ = "role"
	id 				=	db.Column(db.Integer, primary_key = True)
	name			= db.Column(db.String(1024) , unique = True)
	description		= db.Column(db.String(1024))

class User(db.Model, UserMixin):
	id 				=	db.Column(db.Integer, primary_key = True)
	email			=	db.Column(db.String(1024) , index = True)
	username		=	db.Column(db.String(1024) , index = True)
	last_login_at		=	db.Column(db.DATETIME)
	current_login_at	=	db.Column(db.DATETIME)
	last_login_ip		=	db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	current_login_ip	=	db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	login_count			=	db.Column(db.Integer)
	tracker_register_daily_quota	=	db.Column(db.Integer, index = True, default=10)
	tracker_bootstrap_daily_quota	=	db.Column(db.Integer, index = True, default=10)
	

	password		=	db.Column(db.String(1024) , index = True)
	active			=	db.Column(db.Boolean, default=False, nullable=False)
	confirmed_at	=	db.Column(db.DATETIME, index = True, nullable=True)
	roles = db.relationship(
        'Role',
        secondary=roles_users,
        backref=db.backref('users', lazy='dynamic')
)


class gpstrackercert(db.Model):
	id 				= 	db.Column(db.Integer, primary_key = True)
	trackerid		= 	db.Column(db.Integer, db.ForeignKey('gpstracker.id'))
	gpstracker		=   db.relationship('gpstracker', back_populates="trackercert")
	cert			=	db.Column(db.BLOB(10240))
	cert_time		=	db.Column(db.DATETIME, index = True)
	pkey			=	db.Column(db.BLOB(10240))
	csr				=	db.Column(db.BLOB(10240))
	csr_time		=	db.Column(db.DATETIME, index = True, nullable=True)
	
	def __init__(self, trackerid, csr, pkey, csr_time = datetime.datetime.utcnow()):
		self.trackerid	= trackerid
		self.csr		= csr
		self.pkey		= pkey
		self.csr_time	= csr_time
	
	

class gpstracker(db.Model):
	id 				= db.Column(db.Integer, primary_key = True)
	userid			= db.Column(db.Integer, db.ForeignKey('user.id'))
	request_ip		= db.Column(db.String(45) , index = True, nullable=False)  ## 45 is the max length of an IPv6 string
	request_time	= db.Column(db.DATETIME, index = True, nullable=False)
	bootstrap_code	= db.Column(db.String(64) , index = True, nullable=False)
	bootstrapped	= db.Column(db.Boolean, default=False, nullable=False)
	bootstrapped_time = db.Column(db.DATETIME)
	bootstrapped_ip = db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	bootstrap_config	=	db.Column(db.BLOB(10240))
	tracker_name	= db.Column(db.String(1024) , index = True, nullable=False, unique = True)
	friendly_name	= db.Column(db.String(1024) , index = True)
	
	owner			= db.relationship('User', backref=db.backref("trackers",lazy='dynamic'))
	trackercert		= db.relationship('gpstrackercert', back_populates="gpstracker")
	
	def __init__(self, userid, request_ip, request_time, bootstrap_code, tracker_name, bootstrap_config, bootstrapped_time):
		self.userid		= userid
		self.request_ip	= request_ip
		self.request_time	= request_time
		self.bootstrap_code	= bootstrap_code
		self.tracker_name = tracker_name
		self.bootstrap_config = bootstrap_config
		self.bootstrapped_time = bootstrapped_time

class gpsposition(db.Model):
	id 				= db.Column(db.Integer, primary_key = True)
	trackerid		= db.Column(db.Integer, db.ForeignKey('gpstracker.id'))
	gps_latitude	= db.Column(DOUBLE())
	gps_longitude	= db.Column(DOUBLE())
	gps_altitude	= db.Column(DOUBLE())
	gps_speed		= db.Column(DOUBLE())
	gps_time		= db.Column(db.DATETIME, index = True)
	gps_ept			= db.Column(DOUBLE())
	gps_epx			= db.Column(DOUBLE())
	gps_epy			= db.Column(DOUBLE())
	gps_epv			= db.Column(DOUBLE())
	gps_track		= db.Column(DOUBLE())
	gps_climb		= db.Column(DOUBLE())
	gps_eps			= db.Column(DOUBLE())
	gps_mode		= db.Column(db.Integer, index = True)
	clinet_ip		= db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	upload_time		= db.Column(db.DATETIME, index = True)
	
	gpstracker		= db.relationship('gpstracker', backref=db.backref("gpsposition",lazy='dynamic'))
	
	db.Index('gpslookupindex', "gps_mode", "gps_time", "trackerid")
	
	
	def __init__(self, gpsdata, trackerid, client_ip, upload_time):
		### MODE1 data is basically no data!!!!
		### MODE2 = 2D data
		### MODE3 = 3D data
		self.gps_latitude	= gpsdata.get('lat',0)
		self.gps_longitude	= gpsdata.get('lon',0)
		self.gps_altitude	= gpsdata.get('alt',0)
		self.gps_speed		= gpsdata.get('speed',0)
		self.gps_time		= parse(gpsdata.get('time','1990-01-01'))
		self.gps_ept		= gpsdata.get('ept',0)
		self.gps_epx		= gpsdata.get('epx',0)
		self.gps_epy		= gpsdata.get('epy',0)
		self.gps_epv		= gpsdata.get('epv',0)
		self.gps_track		= gpsdata.get('track',0)
		self.gps_climb		= gpsdata.get('climb',0)
		self.gps_eps		= gpsdata.get('eps',0)
		self.gps_mode		= gpsdata['mode']
		self.trackerid		= trackerid
		self.clinet_ip		= client_ip
		self.upload_time	= upload_time

	def toDict(self):
		temp = {}
		temp['lat'] = str(self.gps_latitude)
		temp['lng'] = str(self.gps_longitude)
		temp['alt'] = str(self.gps_altitude)
		temp['speed'] = str(self.gps_speed)
		temp['time'] = self.gps_time.isoformat()
		temp['mode'] = str(self.gps_mode)
		return temp


class gpsjsondata(db.Model):
	id 				= db.Column(db.Integer, primary_key = True)
	trackerid		= db.Column(db.Integer, db.ForeignKey('gpstracker.id'))
	clinet_ip		= db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	upload_time		= db.Column(db.DATETIME, index = True)
	jsondata		= db.Column(db.JSON)
	gpstracker		= db.relationship('gpstracker', backref=db.backref("gpsjsondata",lazy='dynamic'))
	
	def __init__(self, jsondata, trackerid, client_ip, upload_time):
		self.trackerid	= trackerid
		self.clinet_ip		= client_ip
		self.upload_time	= upload_time
		self.jsondata		= jsondata
		
if __name__ == '__main__':
	print 'Creating DB!'
	db.create_all()
