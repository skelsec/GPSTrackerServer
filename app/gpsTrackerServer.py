#!/usr/bin/env python
from app import app, db
from flask import request, send_from_directory, render_template, make_response
from flask_restful import Resource, Api
from flask_security import login_required, current_user
from sqlalchemy import text
import json
import gzip
import cStringIO
import datetime
from itertools import compress
import os
import pprint
import gpxpy
import gpxpy.gpx 
import pytz



from OpenSSL import crypto
from app.gpsutils.gpsutils import routefilter, GPSdistance
from dateutil.parser import parse
from dateutil.relativedelta import *
from gpsDB import gpsposition, gpsjsondata, gpstracker as TrackerTable, User, Role, gpstrackercert

def getclientIP(request):
	#TODOOOOOOO
	#The original values of REMOTE_ADDR and HTTP_HOST are stored in the WSGI environment as werkzeug.proxy_fix.orig_remote_addr and werkzeug.proxy_fix.orig_http_host.
	#user_ip = request.headers['X-Real-IP']
	#request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
	#ip = request.remote_addr
	#remote_addr = request.headers.getlist("X-Forwarded-For")
	return '127.0.0.1'

class JsonResponse():
	def __init__(self, status, data):
		self.rd = {}
		self.rd['status'] = status
		self.rd['data'] = data
	def toJson(self):
		return json.dumps(self.rd)
	def toDict(self):
		return self.rd

class ErrorResponse(JsonResponse):
	def __init__(self, reason):
		t = {}
		t['errmsg'] = reason
		JsonResponse.__init__(self,'error',t)

class GPSDataResponse(JsonResponse):
	def __init__(self, gpsdataList):
		t = {}
		t['gpsdatalist'] = gpsdataList
		JsonResponse.__init__(self,'ok',t)

class GPSRouteResponse(JsonResponse):
	def __init__(self, route):
		t = {}
		t['gpsroute'] = route
		JsonResponse.__init__(self,'ok',t)		
		
class TrackerRegisterSuccsess(JsonResponse):
	def __init__(self, bootstrap_code):
		t = {}
		t['bootstrap_code'] = bootstrap_code
		JsonResponse.__init__(self,'ok',t)

class OKResponse(JsonResponse):
	def __init__(self):
		JsonResponse.__init__(self, 'ok','')
		
class BootstrapResponse(JsonResponse):
	def __init__(self, cert, key):
		t = {}
		t['cert'] = cert
		t['key']  = key
		JsonResponse.__init__(self,'ok',t)

class TrackerCert():
	def __init__(self, certfile, keyfile, validity = 365*24*60*60, key_size = 2048, digest_algo = "sha256"):
		self.ca_cert_file = certfile
		self.ca_key_file = keyfile
		self.ca_cert = ''
		self.ca_key = ''
		self.key_size = key_size
		self.digest_algo = digest_algo
		self.certificate_validity_period = validity
		
		self.load_ca()
		
	def load_ca(self):
		with open(self.ca_cert_file, 'rb') as f:
			self.ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
		with open(self.ca_key_file, 'rb') as f:
			self.ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, f.read())
		
		
	def generate_csr(self, cn, OU):
		
		req = crypto.X509Req()
		req.get_subject().CN = cn
		req.get_subject().countryName = "NZ"
		req.get_subject().stateOrProvinceName = "N/A"
		req.get_subject().localityName = "N/A"
		req.get_subject().organizationName = "GPSTracker"
		req.get_subject().organizationalUnitName = str(OU)
		# Add in extensions
		base_constraints = ([
			crypto.X509Extension("keyUsage", False, "Digital Signature, Non Repudiation, Key Encipherment"),
			crypto.X509Extension("basicConstraints", False, "CA:FALSE"),
		])
		x509_extensions = base_constraints
		req.add_extensions(x509_extensions)
		key = crypto.PKey()
		key.generate_key(crypto.TYPE_RSA, self.key_size)
		req.set_pubkey(key)

		req.sign(key, self.digest_algo)
		certreq_pem = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
		private_key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
		
		
		return req, certreq_pem, private_key_pem
		
		
	#takes database objects!
	def create_and_sign(self, tracker):
		#generate CSR
		trackerCsr, certreq_pem, private_key_pem = self.generate_csr(tracker.tracker_name, tracker.id)
		#insert CSR into database
		try:
			trackercert = gpstrackercert(tracker.id, certreq_pem, private_key_pem)
			db.session.add(trackercert)
			db.session.commit()
		except Exception as e:
			app.logger.exception('Error registering tracker certificate in DB!')
			raise e
		#get the inserted ID, this wil be the serial used
		#sign the CSR
		cert = crypto.X509()
		cert.set_serial_number(trackercert.id)
		cert.gmtime_adj_notBefore(0)
		cert.gmtime_adj_notAfter(self.certificate_validity_period)
		cert.set_issuer(self.ca_cert.get_subject())
		cert.set_subject(trackerCsr.get_subject())
		cert.set_pubkey(trackerCsr.get_pubkey())
		cert.sign(self.ca_key, self.digest_algo)
		cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
		#
		try:
			trackercert = gpstrackercert.query.get(trackercert.id)
			trackercert.cert = cert_pem
			trackercert.cert_time = datetime.datetime.utcnow()
			
			db.session.add(trackercert)
			db.session.commit()
		except Exception as e:
			app.logger.exception('Error updating gpstrackercert with certificate record!')
			raise e
			
		return cert_pem, private_key_pem
		
		

class GPSTracker(Resource):
	method_decorators = {
			'get': [login_required],
			'post': [login_required],
			'put': []
		}


	'''
	GET: gets GPSTracker config for bootstrapping client
	might be extended in the future...
	'''
	
	def get(self, trackerid):
		app.logger.warning('Requested config for trackerid:' + str(trackerid))
		#check if tracker belongs to the current user
		if current_user.trackers.filter(TrackerTable.id == trackerid).count() == 0:
			#user requested a tracker that doesnt belong to him :(
			app.logger.warning('user requested a tracker that doesnt belong to him :(')
			return ErrorResponse('Tracker not available!').toDict()
			
		tracker = TrackerTable.query.get(trackerid)
		
		response = make_response(tracker.bootstrap_config)
		# This is the key: Set the right header for the response
		# to be downloaded, instead of just printed on the browser
		response.headers["Content-Disposition"] = "attachment; filename=config.json"
		
		
		return response
	
	
	
	
	'''
	POST: creates a new tracker
	This method creates a new tracker and generates an OTP for the Tracker device to use with bootstrap
	input: cmd:
			register: user
			share: dest_email, tracker code
			unshare: dest_email, tracker code
	output: bootstrap_code
	
	'''

	def post(self):
		app.logger.debug('GPSTracker POST called')
		#tracker id is not known at this point, discard it
		request_ip = getclientIP(request)
		request_time = datetime.datetime.utcnow()
		yesterday = request_time-relativedelta(days=1)
		
		client_ip = getclientIP(request)
		request_time = datetime.datetime.utcnow()
		registration_period = request_time + relativedelta(weeks=-1 *  app.config['TRACKER_BOOTSTRAP_REGISTRATION_PERIOD'])
		
		if request.content_length is not None and request.content_length > app.config['POST_DATA_MAX_SIZE']:
			app.logger.warning('Error POST DATA SIZE')
			return ErrorResponse('Content length missing or too large!').toDict()
		
		jdata = ''
		try:
			jdata = json.loads(request.get_data())
			jdata['cmd']
		except Exception as e:
			app.logger.warning('command Parameter missing! '+str(e))
			return ErrorResponse('command Parameter missing!').toDict()
		
		app.logger.debug('GPSTracker POST CMD: ' + jdata['cmd'])
		if jdata['cmd'].lower() == 'share':
			try:
				try:
					tracker_id = jdata['tracker_id']
					email = jdata['email']
				except Exception as e:
					app.logger.warning('Parameter missing! '+str(e))
					return ErrorResponse('Parameter missing!').toDict()
					
				app.logger.debug('GPSTracker SHARE params: ' + tracker_id + ' ' + email)
					
				#check if target user exists
				try:
					target_user = User.query.filter_by(email = email).first()
					if target_user is None:
						raise Exception()
				except Exception as e:
					app.logger.exception('Share command target user doesnt exist!')
					return ErrorResponse('User doesnt exist').toDict()
				
				#check if tracker exists
				try:
					tracker = TrackerTable.query.get(tracker_id)
					if tracker is None:
						raise Exception('Tracker doesnt exist')
				except Exception as e:
					app.logger.exception('Share command tracker doesnt exist!')
					return ErrorResponse('tracker doesnt exist').toDict()
					
				#check if tracker already shared with guest
				if tracker.sharedto.filter(User.id == target_user.id).count() != 0:
					app.logger.warning('Tracker is already shared to target user')
					return ErrorResponse('Tracker is already shared to target user').toDict()
					
				#chek if owner shares tracker with himself
				if tracker.owner.id == target_user.id:
					app.logger.warning('Tracker belongs to the target user itself')
					return ErrorResponse('Tracker belongs to the target user itself').toDict()
				
				#check if tracer belongs to the current user
				if tracker.owner.id != current_user.id:
					app.logger.warning('user requested a tracker that doesnt belong to him :(')
					return ErrorResponse('Tracker not available!').toDict()
				
				#add tracker to shared
				
				try:
					#target_user.guestrackers.append(tracker)
					tracker = TrackerTable.query.get(tracker_id)
					tracker.sharedto.append(target_user)
					#target_user.guestrackers.append(UserGuestTracker(target_user,tracker))
					db.session.add(tracker)
					db.session.commit()
				except Exception as e:
						app.logger.exception('Failed to create share connection!')
						return ErrorResponse('Failed to create share connection').toDict()
						
				app.logger.debug('GPSTracker SHARE completed succsessfully')
			
			except Exception as e:
						app.logger.exception('Failed to create share connection!')
						return ErrorResponse('Failed to create share connection').toDict()
						
		if jdata['cmd'].lower() == 'unshare':
			try:
				try:
					tracker_id = jdata['tracker_id']
					email = jdata['email']
				except Exception as e:
					app.logger.warning('Parameter missing! '+str(e))
					return ErrorResponse('Parameter missing!').toDict()
			
				#check if target user exists
				try:
					target_user = User.query.filter_by(email = email).first()
					if target_user is None:
						raise Exception()
				except Exception as e:
					app.logger.exception('Share command target user doesnt exist!')
					return ErrorResponse('User doesnt exist').toDict()
				
				#check if tracker exists
				try:
					tracker = TrackerTable.query.get(tracker_id)
					if tracker is None:
						raise Exception()
				except Exception as e:
					app.logger.exception('Share command tracker doesnt exist!')
					return ErrorResponse('tracker doesnt exist').toDict()
					
				#check if tracer belongs to the current user
				if tracker.owner.id != current_user.id:
					app.logger.warning('user requested a tracker that doesnt belong to him :(')
					return ErrorResponse('Tracker not available!').toDict()
					
				#check if tracker is shared with guest
				if tracker.sharedto.filter(User.id == target_user.id).count() == 0:
					app.logger.warning('Tracker is not shared to target user')
					return ErrorResponse('Tracker is not shared to target user').toDict()				
				
			
			
				try:
					#target_user.guestrackers.append(tracker)
					tracker = TrackerTable.query.get(tracker_id)
					tracker.sharedto.remove(target_user)
					#target_user.guestrackers.append(UserGuestTracker(target_user,tracker))
					db.session.add(tracker)
					db.session.commit()
				except Exception as e:
						app.logger.exception('Failed to create share connection!')
						return ErrorResponse('Failed to create share connection').toDict()
					
			except Exception as e:
				app.logger.exception('Unshare command failed!')
				return ErrorResponse('Unshare command failed').toDict()
		
		if jdata['cmd'].lower() == 'create':
		
			#check user quota
			#be careful because for the 'between' query one must specify the earliest date as start and the latest one as end, otherwise it doesnt work.
			registers_today_ip = TrackerTable.query.filter_by(userid = current_user.id).filter(TrackerTable.request_time.between(yesterday, request_time)).count()
			if registers_today_ip > current_user.tracker_register_daily_quota:
				return ErrorResponse('Register request quota reached!').toDict()
			
			#if everything is okay, create a new tracker registration option
			bootstrap_code = os.urandom(app.config['TRACKER_BOOTSTRAP_OTP_LENGTH']).encode('hex').lower()
			tracker_name   = os.urandom(app.config['TRACKER_NAME_LENGTH']).encode('hex').lower()
			
			#generating config.json template for the tracker
			trackerconfig = ''	
			
			try:
				with open(app.config['TRACKER_CONFIGURATION_TEMPLATE'],'rb') as f:
					trackerconfig = json.load(f)
			except Exception as e:
				app.logger.exception('Error opening tracker configuration template file')
				return ErrorResponse('Error #33').toDict()
			
			trackerconfig['BOOTSTRAP']["BOOTSTRAP_CODE"] = bootstrap_code
			trackerconfig['BOOTSTRAP']["BOOTSTRAP_EMAIL"] = current_user.email
			trackerconfig['BOOTSTRAP']["BOOTSTRAP_URL"] = app.config["TRACKER_SERVER_BASE_URL"] + 'gpstracker'
			trackerconfig['UPLOADER']["UPLOAD_URL"] = app.config["TRACKER_SERVER_BASE_URL"]
			trackerconfig['UPLOADER']["TRACKER_NAME"] = tracker_name
			
			tc = json.dumps(trackerconfig)
			
			try:
				tracker = TrackerTable(current_user.id, request_ip, request_time, bootstrap_code, tracker_name, tc, '1900-01-01')
				db.session.add(tracker)
				db.session.commit()
			except Exception as e:
				app.logger.exception('Error registering tracker DB!')
				return ErrorResponse('Error registering tracker!').toDict()
			
			return TrackerRegisterSuccsess(bootstrap_code).toDict()
		

	'''
	PUT: bootstraps the GPSTracker
	input: command, 
			bootstrap: user_email and bootstrap_code
				
	output: certificate and key signed for tracker_name
	'''
	def put(self):
		client_ip = getclientIP(request)
		request_time = datetime.datetime.utcnow()
		registration_period = request_time + relativedelta(weeks=-1 *  app.config['TRACKER_BOOTSTRAP_REGISTRATION_PERIOD'])
		
		if request.content_length is not None and request.content_length > app.config['POST_DATA_MAX_SIZE']:
			app.logger.warning('Error POST DATA SIZE')
			return ErrorResponse('Content length missing or too large!').toDict()
		
		
		
		try:
			temp = json.loads(request.get_data())
			bootstrap_code_hex = temp['bootstrap_code']
			email = temp['email']
		except Exception as e:
			app.logger.warning('Parameter missing! '+str(e))
			return ErrorResponse('Parameter missing!').toDict()
		
		print email
		print bootstrap_code_hex
		
		#parse bootstrap code
		try:
			if len(bootstrap_code_hex) != app.config['TRACKER_BOOTSTRAP_OTP_LENGTH']*2:
				raise Exception('length')
			bootstrap_code_hex.decode('hex')
		except Exception as e:
			app.logger.warning('OTP format error!')
			return ErrorResponse('OTP format error!').toDict()
			
		#lookup bootstrap code in the DB, checking if it's already registtered or not
		
		regcount = TrackerTable.query.filter_by(bootstrap_code = bootstrap_code_hex.lower()).filter(TrackerTable.request_time.between(registration_period, request_time)).filter(TrackerTable.bootstrapped == False).filter(TrackerTable.owner.has(email = email)).count()
		
		if regcount == 0:
			app.logger.warning('Client tried to re-register')
			return ErrorResponse('Registration error #2').toDict()
		
		tracker = TrackerTable.query.filter_by(bootstrap_code = bootstrap_code_hex.lower()).filter(TrackerTable.request_time.between(registration_period, request_time)).filter(TrackerTable.bootstrapped == False).filter(TrackerTable.owner.has(email = email)).first()
		
		try:
			cf = TrackerCert(app.config['TRACKER_CA_CERT_FILE'], app.config['TRACKER_CA_KEY_FILE'])
			cert, key = cf.create_and_sign(tracker)
		except Exception as e:
			app.logger.exception('Certificate generation error' + str(e))
			return ErrorResponse('Error #21').toDict()	
		
		try:
			#set , bootsrapped flag, sign 
			
			tracker.bootstrapped = True
			tracker.bootstrapped_time = datetime.datetime.utcnow()
			tracker.bootstrapped_ip = client_ip
			db.session.add(tracker)
			db.session.commit()
			
			return BootstrapResponse(cert, key).toDict(), 200
		
		except Exception as e:
			app.logger.exception('Failed to generate bootstrap data!' + str(e))
			return ErrorResponse('Failed to generate bootstrap data!').toDict()	
			
		
		
			
		
class GPSPosition(Resource):
	method_decorators = {
			'get': [login_required],
			'post': []
		}


	'''
	POST: this is where the GPSTracker devices uploading the GPS Position data.
	tracker_name: the name of the GPSTracker (which is in the CN filed of the SSL cert)
	'''
	def post(self):
		route_name = '[GPSPosition POST request]' 
		############## TODOTODO!!!!!!#############
		#### implement CN name extraction and compare it to the tracker_name!!!!
		#app.logger.warning(str(pprint.pformat(request.__dict__, depth=5)))
		try:
			#app.logger.debug('GPSPosition POST request in')
			tracker_name = request.environ['SSL_CLIENT_S_DN_CN']
			tracker_id = int(request.environ['SSL_CLIENT_S_DN_OU'])
			
			#app.logger.debug('%s tracker_name: %s' %(route_name, tracker_name,))
			#app.logger.debug('%s tracker_id: %s' %(route_name, tracker_id,))
			
			#check if we find the tracker based on the certificate parameters
			current_tracker = TrackerTable.query.filter_by(id = tracker_id).filter(TrackerTable.tracker_name == tracker_name).first()
			if current_tracker == None:
				app.logger.debug('%s Could not find tracker in database' %(route_name,))
				return ErrorResponse('Could not find tracker in database').toDict()
				
					
			client_ip = getclientIP(request)
			upload_time = datetime.datetime.utcnow()

			if request.content_length is not None and request.content_length > app.config['POST_DATA_MAX_SIZE']:
				app.logger.debug('%s request size too large' %(route_name,))
				return ErrorResponse('Content length missing or too large!').toDict()
			

			#app.logger.debug('%s sanity check passed!' %(route_name,))
			try:
				compressedFile = cStringIO.StringIO(request.get_data())
				compressedFile.seek(0)
				decompressedFile = gzip.GzipFile(fileobj=compressedFile, mode='rb')
				#app.logger.debug('%s created decompression object' %(route_name,))
			except:
				app.logger.exception('%s Error decompressing data!' %(route_name,))
				return ErrorResponse('Error decompressing data!').toDict()
			

			try:			
				for line in decompressedFile:
					line = line.strip()
					gpsdata = json.loads(line)
					#app.logger.debug('%s gpsdata: %s' %(route_name,gpsdata))
					if 'class' not in gpsdata:
						app.logger.warning('%s Decompressed data type is not what is expected' %(route_name,))
						return ErrorResponse('Decompressed data type is not what is expected').toDict()
						
					gpsraw = gpsjsondata(line, current_tracker, client_ip, upload_time)
					db.session.add(gpsraw)

					
					if gpsdata['class'] == 'TPV':
						gpsp = gpsposition(gpsdata, current_tracker, client_ip, upload_time)
						current_tracker.gpsposition.append(gpsp)
						db.session.add(gpsp)

				db.session.commit()					
				
				#app.logger.debug('%s Sending OK!' %(route_name,))
				return OKResponse().toDict(), 200

			except:
				app.logger.exception('%s Failed processing decompressed position data' %(route_name,))
				return ErrorResponse('Error decompressing data!').toDict()
				
		except Exception as e:
			app.logger.exception('Generic exception!')
			return ErrorResponse('Error parsing data!').toDict()

		

	'''
	GET with start and end date set: gets the GPS positional data in a formatted manner for the time period specified. Filtering will be applied here!
	tracker_id: the primary key od the tracker
	'''

	def get(self, tracker_id, start_date = '', end_date = '', format = 'ROUTEINFO'):
		try:
			app.logger.debug('GPSPosition GET request')
			client_ip = getclientIP(request)
			
			if format not in app.config['GPS_FILE_FORMATS']:
				app.logger.warning('File format not supported')
				return ErrorResponse('File format not supported!').toDict()
			
			try:
				current_tracker = TrackerTable.query.get(tracker_id)
			except Exception as e:
				app.logger.exception('GPSPosition could not load tracker!')
				return ErrorResponse('Tracker not available!').toDict()
				
			app.logger.debug('GPSPosition GET request current_tracker')
				
			#check if tracker shared with the user OR the user is the owner
			if current_tracker.sharedto.filter(User.id == current_user.id).count() == 0:
				if current_user.id != current_tracker.owner.id:
					app.logger.warning('user requested a tracker that doesnt belong to him :(')
					return ErrorResponse('Tracker not available!').toDict()
			
			app.logger.debug('GPSPosition GET request sanity passed')
			
			posList = []
			rawPosList = []
			filteredPosList = []
			
			if start_date == '' and end_date == '':
				#returning current position
		
				app.logger.debug('Client headers: ' + repr(request.headers))
				client_ip = getclientIP(request)
				
				t = {}
				t['tracker_id'] = str(current_tracker.id)
				t['tracker_name'] = current_tracker.tracker_name
				t['friendly_name'] = current_tracker.friendly_name
				if hasattr(current_tracker, 'html_color') and current_tracker.html_color != None:
					t['html_color'] = current_tracker.html_color
				else:
					t['html_color'] = t['tracker_name'][:6]
				
				
				gpspos = current_tracker.gpsposition.filter(gpsposition.gps_mode != 1).order_by(gpsposition.gps_time.desc()).with_hint(gpsposition, 'USE INDEX(latestposlookupindx)','mysql').first()
				if not gpspos:
					return ErrorResponse('No position data for tracker!').toDict(), 200
					
					
				temp = {}
				temp['lat'] = str(gpspos.gps_latitude)
				temp['lng'] = str(gpspos.gps_longitude)
				temp['alt'] = str(gpspos.gps_altitude)
				temp['speed'] = str(gpspos.gps_speed)
				temp['time'] = gpspos.gps_time.isoformat()
				t['latest_position'] = temp

				app.logger.debug('Latest position request response:' + repr(t))
				return GPSDataResponse(t).toDict(), 200
				
			if end_date == '':
				end_date = '2999-12-31'
				
			try:
				
				start = parse(start_date)
				end   = parse(end_date)
				
			except Exception as e:
				app.logger.exception('Date format not recognized!')
				return ErrorResponse('Date format not recognized!').toDict()
				
			
			app.logger.info('Position requested for tracker %s Between %s and %s' % (current_tracker.id, start.isoformat() , end.isoformat()))
			
			if format == 'ROUTEINFO':
				app.logger.info('Format: ROUTEINFO')
				route = GPSRoute(current_tracker,start,end)
				route.createSegments()
				if len(route.routesegments) == 0:
					app.logger.info('No segments found')
					return ErrorResponse('No points in the time period').toDict()
					
				route.finalize()
				app.logger.info('Returning response')
				return GPSRouteResponse(route.toDict()).toDict(), 200
				
			elif format == 'GPX':			
				gpx = gpxpy.gpx.GPX()
				route = GPSRoute(current_tracker)

				for gpspos in current_tracker.gpsposition.filter(gpsposition.gps_mode != 1).filter(gpsposition.gps_speed.between(app.config['GPS_MINIMUM_SPEED'], app.config['GPS_MAX_SPEED'])).filter(gpsposition.gps_time.between(start, end)).order_by(gpsposition.gps_time.asc()).all():
					route.addPoint(gpspos)

				route.finalize()
				gpx_track = gpxpy.gpx.GPXTrack()
				gpx.tracks.append(gpx_track)
				for segments in route.routesegments:
					gpx_segment = gpxpy.gpx.GPXTrackSegment()
					gpx_track.segments.append(gpx_segment)
					for gpspos in segments.filtered_route:
						gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(float(gpspos['lat']), float(gpspos['lng']), elevation=float(gpspos['alt'])))
				
				
				response = make_response(gpx.to_xml())
				response.headers["Content-Disposition"] = "attachment; filename=route.gpx"
				return response
				
		except Exception as e:
			app.logger.exception('Generic exception!')
			
class GPSRouteInfo():
	
	def __init__(self):
		self.total_distance_start_stop	= 0.0
		self.total_distance_traveled	= 0.0
		self.total_time					= 0
		self.max_speed					= 0.0
		self.avg_speed					= 0.0
		self.max_elevation				= 0.0
		self.min_elevation				= 0.0
		self.max_speed_point			= 0
		self.max_elevation_point		= 0
		self.min_elevation_point		= 0
	
	def calc(self, filtered_route):
		#self.total_distance_start_stop
		
		start_point = (filtered_route[0].gps_latitude, filtered_route[0].gps_longitude)
		end_point = (filtered_route[-1].gps_latitude, filtered_route[-1].gps_longitude)
		self.total_distance_start_stop = GPSdistance(start_point, end_point)
		
		#self.total_time
		start_time = filtered_route[0].gps_time
		end_time = filtered_route[-1].gps_time
		self.total_time = (end_time - start_time).total_seconds()
		
		#self.max_speed #self.max_elevation #self.low_elevation #self.total_distance_travelled
		total_speed = 0.0
		pos_n_1 = filtered_route[0]
		self.max_elevation = pos_n_1.gps_altitude
		self.min_elevation = pos_n_1.gps_altitude
		average_points = 0
		position_points = 1
		for pos in filtered_route[1:]:
			position_points += 1
			ev = pos.gps_altitude
			dist = GPSdistance((pos_n_1.gps_latitude, pos_n_1.gps_longitude), (pos.gps_latitude, pos.gps_longitude))
			self.total_distance_traveled += float(dist)

			if pos.gps_time == pos_n_1.gps_time:
				#app.logger.debug('Two GPS timestamps were found to be equal! This indicates that you are storing the timestamps in a DB that doesnt use the full precision of the GPS timestamps OR you are a timetraveller. Please check the non-existent manual what to do in this situation!')
				continue
			
			speed = float(dist)/(float( (pos.gps_time - pos_n_1.gps_time).total_seconds()))
			average_points += 1
			
			total_speed += speed
			if self.max_speed < speed:
				self.max_speed = speed
				self.max_speed_point = position_points
		
				
			if self.max_elevation < ev:
				self.max_elevation = ev
				self.max_elevation_point = position_points -1
		
			
			if self.min_elevation > ev:
				self.min_elevation = ev
				self.min_elevation_point = position_points -1
				
			pos_n_1 = pos
			
		#self.avg_speed
		if average_points != 0:
			self.avg_speed = float(total_speed/float(average_points))
	
	
	
	def toDict(self):
		t = {}
		t['total_distance_start_stop'] = str(self.total_distance_start_stop)
		t['total_distance_traveled'] = str(self.total_distance_traveled)
		t['total_time'] = self.total_time
		#t['total_time'] = datetime.timedelta(seconds=self.total_time).strftime("%H:%M:%S")
		t['max_speed'] = str(self.max_speed)
		t['avg_speed'] = str(self.avg_speed)
		t['max_elevation'] = str(self.max_elevation)
		t['min_elevation'] = str(self.min_elevation)
		t['max_speed_point'] = self.max_speed_point
		t['max_elevation_point'] = self.max_elevation_point
		t['min_elevation_point'] = self.min_elevation_point
		return t
			
class GPSRouteSegment():
	def __init__(self):
		self.routeinfo = GPSRouteInfo()
		
		self.gpspositions	= []
		self.filtered_route	= []
		
		
	def filter_route(self):
		gpspositions_2D = []
		for temp in self.gpspositions:
			gpspositions_2D.append((temp.gps_latitude, temp.gps_longitude))
		
		for gpspos, enabled in zip(self.gpspositions, routefilter(gpspositions_2D,5,0.5)):
			if enabled:
				self.filtered_route.append(gpspos)
		
		
	def finalize(self):
		### filtering out some points to make the path smoother
		self.filter_route()
		
		### calculating routeinfo statistics	
		self.routeinfo.calc(self.filtered_route)
	
	def toDict(self):
		t = {}
		t['filtered_route'] = []
		for gpspos in self.filtered_route:
			t['filtered_route'].append(gpspos.toDict())
		t['routeinfo'] = self.routeinfo.toDict()
		
		return t
			
class GPSRoute():
	def __init__(self, tracker, start, end):
		self.tracker = tracker
		self.tracker_id = str(tracker.id)
		self.tracker_name = tracker.tracker_name
		self.friendly_name =  tracker.friendly_name
		self.html_color = ''
		self.start = start
		self.end = end
		
		if hasattr(tracker, 'html_color'):
			self.html_color = tracker.html_color
		else:
			self.html_color = self.tracker_name[:6]
			

		self.filtered_route = []
		self.routeinfo = GPSRouteInfo() #this is for the total route!!! (segments have different info)
		self.routesegments = []
		
		self._current_segment = GPSRouteSegment()
		
	def createSegments(self):
		app.logger.debug('createSegments')
		segment_start = ''
		current_time = ''
		
		for gpspos in self.tracker.gpsposition.filter(gpsposition.gps_mode != 1).filter(gpsposition.gps_speed.between(app.config['GPS_MINIMUM_SPEED'], app.config['GPS_MAX_SPEED'])).filter(gpsposition.gps_time.between(self.start, self.end)).order_by(gpsposition.gps_time.asc()).all():
			
			if len(self.routesegments) == 0 and len(self._current_segment.gpspositions) == 0:
				#this is for the very first point only
				segment_start = gpspos.gps_time
				current_time = gpspos.gps_time
				self._current_segment.gpspositions.append(gpspos)
				continue
			
			if (gpspos.gps_time - self._current_segment.gpspositions[-1].gps_time).total_seconds() > app.config['GPS_MAX_STANDING_TIME']:
				app.logger.debug('Creating new segment.')
				self._current_segment.finalize()
				self.routesegments.append(self._current_segment)
				self._current_segment = GPSRouteSegment()
			
			self._current_segment.gpspositions.append(gpspos)
			
	def finalize(self):
		self.calc_total_info()
		
	def calc_total_info(self):
		self.routeinfo.total_distance_start_stop = GPSdistance((self.routesegments[0].gpspositions[0].gps_latitude,self.routesegments[0].gpspositions[0].gps_longitude ), (self.routesegments[-1].gpspositions[-1].gps_latitude,self.routesegments[-1].gpspositions[-1].gps_longitude ))
		
		total_speed  = 0
		points = 0
		for segment in self.routesegments:
			self.routeinfo.total_distance_traveled += segment.routeinfo.total_distance_traveled
			self.routeinfo.total_time += segment.routeinfo.total_time
			if self.routeinfo.max_speed < segment.routeinfo.max_speed:
				self.routeinfo.max_speed = segment.routeinfo.max_speed
			
			if self.routeinfo.max_elevation < segment.routeinfo.max_elevation:
				self.routeinfo.max_elevation = segment.routeinfo.max_elevation
			
			if self.routeinfo.min_elevation > segment.routeinfo.min_elevation:
				self.routeinfo.min_elevation = segment.routeinfo.min_elevation
			
			total_speed += segment.routeinfo.avg_speed
			points += 1
		self.routeinfo.avg_speed = total_speed/points
			
	def toDict(self):
		t = {}
		t['tracker_id'] = self.tracker_id
		t['tracker_name'] = self.tracker_name
		t['friendly_name'] = self.friendly_name
		t['html_color'] = self.html_color
		t['routeinfo'] = self.routeinfo.toDict()
		t['routesegments'] = []
		for segment in self.routesegments:
			t['routesegments'].append(segment.toDict())
		
		return t

"""
@app.before_request
def before():
	# todo with request
	app.logger.warning(str(request.headers) + str(request.environ))
	pass

@app.after_request
def after(response):
	# todo with response
	app.logger.warning( response.status)
	app.logger.warning( response.headers)
	#app.logger.warning( response.get_data())
	return response
"""

# This is for gpstracker.js
@app.route('/bootstrap/<path:path>', methods=['GET'])
def serve_static(path):
	app.logger.warning('Script called!' + str(path))
	return send_from_directory(app.config['STATIC_DIR'], path)
	
# This is for gpstracker.js
@app.route('/scritps/<path:path>', methods=['GET'])
def serve_scripts(path):
	app.logger.warning('Script called!' + str(path))
	return send_from_directory(app.config['SCRIPTS_DIR'], path)

# This is for gpstracker.js
@app.route('/css/<path:path>', methods=['GET'])
def serve_css(path):
	app.logger.warning('Script called!' + str(path))
	return send_from_directory(app.config['CSS_DIR'], path)	
	
	
"""
@app.route('/', methods=['GET'])
@login_required
def home():
	print 'home'
	return render_template('home/index.html')
"""
	
