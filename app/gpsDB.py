#!/usr/bin/env python
from app import db, app
from sqlalchemy.dialects.mysql import DOUBLE, DATETIME as MYSQL_DATETIME
from flask_security import UserMixin, RoleMixin

import datetime
from dateutil.parser import parse
from app.gpsutils.gpsutils import routefilter, GPSdistance

import pytz
import decimal

class UTCDateTime(db.TypeDecorator):
	'''Results returned as aware datetimes, not naive ones.
	'''

	impl = MYSQL_DATETIME(fsp=6)

	def process_result_value(self, value, dialect):
		if value is None:
			return value
		return value.replace(tzinfo=pytz.UTC)

# Create a table to support a many-to-many relationship between Users and Roles
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

guest_trackers_users = db.Table(
	'guest_trackers_users',
	db.Column('id',db.Integer(), primary_key = True),
	db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
	db.Column('gpstracker_id', db.Integer(), db.ForeignKey('gpstracker.id')),
	db.Column('link_time', UTCDateTime, default=datetime.datetime.utcnow)
)

gpsposition_gpsroutesegment = db.Table(
	'gpsposition_gpsroutesegment',
	db.Column('id',db.Integer(), primary_key = True),
	db.Column('gpsposition_id', db.Integer(), db.ForeignKey('gpsposition.id')),
	db.Column('gpsroutesegment_id', db.Integer(), db.ForeignKey('gpsroutesegment.id')),
	db.Column('link_time',UTCDateTime, default=datetime.datetime.utcnow)
)


class Role(db.Model, RoleMixin):
	__tablename__ = "role"
	id 			= db.Column(db.Integer(), primary_key = True)
	name		= db.Column(db.String(1024) , unique = True)
	description	= db.Column(db.String(1024))

class gpstracker(db.Model):
	id 					= db.Column(db.Integer(), primary_key = True)
	userid				= db.Column(db.Integer(), db.ForeignKey('user.id'))
	request_ip			= db.Column(db.String(45) , index = True, nullable=False)  ## 45 is the max length of an IPv6 string
	request_time		= db.Column(UTCDateTime, index = True, nullable=False)
	bootstrap_code		= db.Column(db.String(64) , index = True, nullable=False)
	bootstrapped		= db.Column(db.Boolean, default=False, nullable=False)
	bootstrapped_time	= db.Column(UTCDateTime)
	bootstrapped_ip		= db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	bootstrap_config	= db.Column(db.BLOB(10240))
	tracker_name		= db.Column(db.String(1024) , index = True, nullable=False)
	friendly_name		= db.Column(db.String(1024) , index = True)
	html_color			= db.Column(db.String(7))
	
	owner			= db.relationship('User', backref=db.backref("trackers",lazy='dynamic'))
	trackercert		= db.relationship('gpstrackercert', back_populates="gpstracker")
	
	
	
	sharedto = db.relationship(
        'User',
        secondary=guest_trackers_users,
        backref=db.backref('guestrackers', lazy='dynamic'),
		lazy='dynamic')
		
	db.Index('tracker_id_name_user', 'id', 'tracker_name','userid', unique=True)
	db.Index('tracker_id_name', 'id', 'tracker_name')

	
	def __init__(self, userid, request_ip, request_time, bootstrap_code, tracker_name, bootstrap_config, bootstrapped_time):
		self.userid		= userid
		self.request_ip	= request_ip
		self.request_time	= request_time
		self.bootstrap_code	= bootstrap_code
		self.tracker_name = tracker_name
		self.bootstrap_config = bootstrap_config
		self.bootstrapped_time = bootstrapped_time

class User(db.Model, UserMixin):
	id 				=	db.Column(db.Integer(), primary_key = True)
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
        backref=db.backref('users', lazy='dynamic'))
	
	db.Index('emailpass', 'email', 'password')
	db.Index('userpass', 'username', 'password')
		
		
		
class gpsposition(db.Model):
	id 				= db.Column(db.Integer(), primary_key = True)
	trackerid		= db.Column(db.Integer(), db.ForeignKey('gpstracker.id'))
	gps_latitude	= db.Column(DOUBLE())
	gps_longitude	= db.Column(DOUBLE())
	gps_altitude	= db.Column(DOUBLE())
	gps_speed		= db.Column(DOUBLE())
	gps_time		= db.Column(UTCDateTime) ## IMPORTANT: WHATEVER DB YOU ARE USING IT MUST SUPPORT MILI/MICROSECONDS FOR DATETIME!!!
	gps_ept			= db.Column(DOUBLE())
	gps_epx			= db.Column(DOUBLE())
	gps_epy			= db.Column(DOUBLE())
	gps_epv			= db.Column(DOUBLE())
	gps_track		= db.Column(DOUBLE())
	gps_climb		= db.Column(DOUBLE())
	gps_eps			= db.Column(DOUBLE())
	gps_mode		= db.Column(db.Integer())
	clinet_ip		= db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	upload_time		= db.Column(UTCDateTime, index = True)
	
	gpstracker			= db.relationship('gpstracker', backref=db.backref("gpsposition",lazy='dynamic'))
	
	__table_args__ = (db.Index('gpslookupindx', "gps_mode", "gps_time", "trackerid", "gps_speed"), db.Index('latestposlookupindx', "gps_mode", "gps_time", "trackerid"))
	
	def __init__(self, gpsdata, tracker, client_ip, upload_time):
		### MODE1 data is basically no data!!!!
		### MODE2 = 2D data
		### MODE3 = 3D data
		self.gps_latitude	= gpsdata.get('lat',0)
		self.gps_longitude	= gpsdata.get('lon',0)
		self.gps_altitude	= gpsdata.get('alt',0)
		self.gps_speed		= gpsdata.get('speed',0)
		self.gps_time		= parse(gpsdata.get('time','1990-01-01')).replace(tzinfo=pytz.UTC)
		self.gps_ept		= gpsdata.get('ept',0)
		self.gps_epx		= gpsdata.get('epx',0)
		self.gps_epy		= gpsdata.get('epy',0)
		self.gps_epv		= gpsdata.get('epv',0)
		self.gps_track		= gpsdata.get('track',0)
		self.gps_climb		= gpsdata.get('climb',0)
		self.gps_eps		= gpsdata.get('eps',0)
		self.gps_mode		= gpsdata['mode']
		self.gpstracker		= tracker
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
		
class gpsroutesegment(db.Model):
	id 				= db.Column(db.Integer(), primary_key = True)
	trackerid		= db.Column(db.Integer(), db.ForeignKey('gpstracker.id'))
	gpstracker		= db.relationship('gpstracker', backref=db.backref("gpsroutesegment",lazy='dynamic'))
	routeinfo		= db.relationship("gpsrouteinfo", uselist=False, back_populates="gpsroutesegment")
	start			= db.Column(UTCDateTime, index = True)
	end				= db.Column(UTCDateTime, index = True)
	gpspositions	= db.relationship(
        'gpsposition',
        secondary=gpsposition_gpsroutesegment,
        backref=db.backref('gpsroutesegments', lazy='dynamic'),
		lazy='dynamic')
		
	filtered_route	= db.relationship(
        'gpsposition',
        secondary=gpsposition_gpsroutesegment,
        backref=db.backref('filtered_routes', lazy='dynamic'),
		lazy='dynamic')
	
	def __init__(self, tracker, start_time, end_time):
		self.gpstracker = tracker
		self.start = start_time
		self.end = end_time
		self.routeinfo = gpsrouteinfo()
		self.routeinfo.gpstracker = tracker
		
		for gpspos in self.gpstracker.gpsposition.filter(gpsposition.gps_time.between(self.start, self.end)).all():
			self.gpspositions.append(gpspos)
		
		
	def filter_route(self):
		gpspositions_2D = []
		for temp in self.gpspositions.all():
			gpspositions_2D.append((temp.gps_latitude, temp.gps_longitude))
		
		for gpspos, enabled in zip(self.gpspositions.all(), routefilter(gpspositions_2D,5,0.5)):
			if enabled:
				self.filtered_route.append(gpspos)
		
		
	def finalize(self):
		### filtering out some points to make the path smoother
		self.filter_route()
		
		### calculating routeinfo statistics	
		self.routeinfo.calc()
	
	def toDict(self):
		t = {}
		t['filtered_route'] = self.filtered_route
		t['routeinfo'] = self.routeinfo.toDict()
		
		return t
	
	
	
class gpsrouteinfo(db.Model):
	id 				= db.Column(db.Integer(), primary_key = True)
	trackerid		= db.Column(db.Integer(), db.ForeignKey('gpstracker.id'))
	gpsroutesegmentid	= db.Column(db.Integer(), db.ForeignKey('gpsroutesegment.id'))
	gpsroutesegment 	= db.relationship("gpsroutesegment",  uselist=False, back_populates="routeinfo")
	gpstracker		= db.relationship('gpstracker', backref=db.backref("gpsrouteinfo",lazy='dynamic'))
	
	total_distance_start_stop = db.Column(DOUBLE(), default = 0.0)
	total_distance_traveled = db.Column(DOUBLE(), default = 0.0)
	total_time = db.Column(db.Integer() , default = 0.0)
	max_speed = db.Column(DOUBLE(), default = 0.0)
	avg_speed = db.Column(DOUBLE(), default = 0.0)
	max_elevation = db.Column(DOUBLE(), default = 0.0)
	min_elevation = db.Column(DOUBLE(), default = 0.0)
	
	def calc(self):
		#self.total_distance_start_stop
		start_point = (self.gpsroutesegment.filtered_route[0].gps_latitude, self.gpsroutesegment.filtered_route[0].gps_longitude)
		end_point = (self.gpsroutesegment.filtered_route[-1].gps_latitude, self.gpsroutesegment.filtered_route[-1].gps_longitude)
		self.total_distance_start_stop = GPSdistance(start_point, end_point)
		
		
		#self.total_time
		start_time = self.gpsroutesegment.filtered_route[0].gps_time
		end_time = self.gpsroutesegment.filtered_route[-1].gps_time
		self.total_time = (end_time - start_time).total_seconds()
		
		#self.max_speed #self.max_elevation #self.low_elevation #self.total_distance_travelled
		total_speed = 0.0
		pos_n_1 = self.gpsroutesegment.filtered_route[0]
		self.max_elevation = pos_n_1.gps_altitude
		self.min_elevation = pos_n_1.gps_altitude
		points = 0
		for pos in self.gpsroutesegment.filtered_route[1:]:
			ev = pos.gps_altitude
			dist = GPSdistance((pos_n_1.gps_latitude, pos_n_1.gps_longitude), (pos.gps_latitude, pos.gps_longitude))
			self.total_distance_traveled += float(dist)

			if pos.gps_time == pos_n_1.gps_time:
				app.logger.debug('Two GPS timestamps were found to be equal! This indicates that you are storing the timestamps in a DB that doesnt use the full precision of the GPS timestamps OR you are a timetraveller. Please check the non-existent manual what to do in this situation!')
				continue
			
			speed_m_s = float(dist)/(float( (pos.gps_time - pos_n_1.gps_time).total_seconds()))
			speed = speed_m_s*3.6
			points += 1
			
			total_speed += speed
			if self.max_speed < speed:
				self.max_speed = speed
				
			if self.max_elevation < ev:
				self.max_elevation = ev
			
			if self.min_elevation > ev:
				self.min_elevation = ev
				
			pos_n_1 = pos
			
		#self.avg_speed
		if points != 0:
			self.avg_speed = float(float(total_speed)/float(points))
	
	
	
	def toDict(self):
		t = {}
		t['total_distance_start_stop'] = self.total_distance_start_stop
		t['total_distance_traveled'] = self.total_distance_traveled
		t['total_time'] = str(datetime.timedelta(seconds=self.total_time)) 
		t['max_speed'] = self.max_speed
		t['avg_speed'] = self.avg_speed
		t['max_elevation'] = self.max_elevation
		t['min_elevation'] = self.min_elevation

		return t
	
	

class gpsjsondata(db.Model):
	id 				= db.Column(db.Integer(), primary_key = True)
	trackerid		= db.Column(db.Integer(), db.ForeignKey('gpstracker.id'))
	clinet_ip		= db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	upload_time		= db.Column(UTCDateTime, index = True)
	jsondata		= db.Column(db.JSON())
	gpstracker		= db.relationship('gpstracker', backref=db.backref("gpsjsondata",lazy='dynamic'))
	
	def __init__(self, jsondata, tracker, client_ip, upload_time):
		self.gpstracker		= tracker
		self.clinet_ip		= client_ip
		self.upload_time	= upload_time
		self.jsondata		= jsondata

class gpstrackercert(db.Model):
	id 				= 	db.Column(db.Integer(), primary_key = True)
	trackerid		= 	db.Column(db.Integer(), db.ForeignKey('gpstracker.id'))
	gpstracker		=   db.relationship('gpstracker', back_populates="trackercert")
	cert			=	db.Column(db.BLOB(10240))
	cert_time		=	db.Column(UTCDateTime, index = True)
	pkey			=	db.Column(db.BLOB(10240))
	csr				=	db.Column(db.BLOB(10240))
	csr_time		=	db.Column(UTCDateTime, index = True, nullable=True)
	
	def __init__(self, trackerid, csr, pkey, csr_time = datetime.datetime.utcnow()):
		self.trackerid	= trackerid
		self.csr		= csr
		self.pkey		= pkey
		self.csr_time	= csr_time

		
if __name__ == '__main__':
	print 'Creating DB!'
	db.create_all()
