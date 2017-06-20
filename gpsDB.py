#!/usr/bin/env python
from app import db
from sqlalchemy.dialects.mysql import DOUBLE

from dateutil.parser import parse

class gpsposition(db.Model):
	id 				= db.Column(db.Integer, primary_key = True)
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
	client_name		= db.Column(db.String(1024) , index = True)
	clinet_ip		= db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	upload_time		= db.Column(db.DATETIME, index = True)
	db.Index('gpslookupindex', "gps_mode", "gps_time", "client_name")
	
	
	def __init__(self, gpsdata, client_name, client_ip, upload_time):
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
		self.client_name	= client_name
		self.clinet_ip		= client_ip
		self.upload_time	= upload_time
		
class gpsjsondata(db.Model):
	id 				= db.Column(db.Integer, primary_key = True)
	client_name		= db.Column(db.String(1024) , index = True)
	clinet_ip		= db.Column(db.String(45) , index = True)  ## 45 is the max length of an IPv6 string
	upload_time		= db.Column(db.DATETIME, index = True)
	jsondata		= db.Column(db.JSON)
	
	def __init__(self, jsondata, client_name, client_ip, upload_time):
		self.client_name	= client_name
		self.clinet_ip		= client_ip
		self.upload_time	= upload_time
		self.jsondata		= jsondata
		
if __name__ == '__main__':
	print 'Creating DB!'
	db.create_all()
