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


from OpenSSL import crypto
from app.gpsutils.gpsutils import routefilter
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
		
		
	def generate_csr(self, tracker_id):
		
		req = crypto.X509Req()
		req.get_subject().CN = tracker_id
		req.get_subject().countryName = "NZ"
		req.get_subject().stateOrProvinceName = "N/A"
		req.get_subject().localityName = "N/A"
		req.get_subject().organizationName = "GPSTracker"
		req.get_subject().organizationalUnitName = str(tracker_id)
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
		tracker_id = str(tracker.tracker_name)
		#generate CSR
		trackerCsr, certreq_pem, private_key_pem = self.generate_csr(tracker_id)
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
	'''
	GET: gets GPSTracker info
	'''
	
	@login_required	
	def get(self):
		
		return {}, 200
	
	
	
	
	'''
	POST: creates a new tracker
	This method creates a new tracker and generates an OTP for the Tracker device to use with bootstrap
	input: user
	output: bootstrap_code
	
	'''
	@login_required	
	def post(self):
		#tracker id is not known at this point, discard it
		request_ip = getclientIP(request)
		request_time = datetime.datetime.utcnow()
		yesterday = request_time-relativedelta(days=1)
		
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
		with open(app.config['TRACKER_CONFIGURATION_TEMPLATE'],'rb') as f:
			trackerconfig = json.load(f)
			
		
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
	input: user_email and bootstrap_code
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
		
		cf = TrackerCert(app.config['TRACKER_CA_CERT_FILE'], app.config['TRACKER_CA_KEY_FILE'])
		cert, key = cf.create_and_sign(tracker)
		
		try:
			#set , bootsrapped flag, sign 
			
			tracker.bootstrapped = True
			tracker.bootstrapped_time = datetime.datetime.utcnow()
			tracker.bootstrapped_ip = client_ip
			db.session.add(tracker)
			db.session.commit()
			
			return BootstrapResponse(cert, key).toDict(), 200
		
		except Exception as e:
			app.logger.warning('Failed to generate bootstrap data!' + str(e))
			return ErrorResponse('Failed to generate bootstrap data!').toDict()	
			
		
		
			
		
class GPSPosition(Resource):
	'''
	POST: this is where the GPSTracker devices uploading the GPS Position data.
	tracker_name: the name of the GPSTracker (which is in the CN filed of the SSL cert)
	'''
	def post(self):
		############## TODOTODO!!!!!!#############
		#### implement CN name extraction and compare it to the tracker_name!!!!
		app.logger.warning(str(pprint.pformat(request.__dict__, depth=5)))
		tracker_name = request.environ['SSL_CLIENT_S_DN_CN']
		tracker_id = int(request.environ['SSL_CLIENT_S_DN_OU'])
		
		#check if we find the tracker based on the certificate parameters
		tracker = TrackerTable.query.filter_by(id = tracker_id).filter(TrackerTable.tracker_name == tracker_name).first()
		if tracker == None:
			app.logger.warning('Could not find tracker in database')
			return ErrorResponse('Could not find tracker in database').toDict()
			
				
		client_ip = getclientIP(request)
		upload_time = datetime.datetime.utcnow()

		if request.content_length is not None and request.content_length > app.config['POST_DATA_MAX_SIZE']:
			app.logger.warning('Error POST DATA SIZE')
			return ErrorResponse('Content length missing or too large!').toDict()
		try:
			compressedFile = cStringIO.StringIO(request.get_data())
			compressedFile.seek(0)
			decompressedFile = gzip.GzipFile(fileobj=compressedFile, mode='rb')
			for line in decompressedFile:
				line = line.strip()
				try:
					gpsdata = json.loads(line)
					if 'class' not in gpsdata:
						app.loggger.warning('Decompressed data type is not what is expected')
						return 'Error'

					if gpsdata['class'] == 'TPV':
						gpsp = gpsposition(gpsdata, tracker_name, client_ip, upload_time)
						db.session.add(gpsp)

					gpsraw = gpsjsondata(line, tracker_name, client_ip, upload_time)
					db.session.add(gpsraw)
					db.session.commit()
				except Exception as e:
					app.logger.exception('Error parsing client GPS data!')
					return ErrorResponse('Error parsing data!').toDict()

		except:
			#log
			return ErrorResponse('Error decompressing data!').toDict()

		return OKResponse().toDict(), 200

	'''
	GET with start and end date set: gets the GPS positional data in a formatted manner for the time period specified. Filtering will be applied here!
	tracker_name: the name of the GPSTracker (which is in the CN filed of the SSL cert)
	'''
	@login_required	
	def get(self, tracker_name, start_date = '', end_date = ''):
		try:
			#### TODO !!! check if tracker belongs to the user!!!
			client_ip = getclientIP(request)
			
			#check if tracker belongs to the current user
			#if current_user.query.filter(User.trackers.any(tracker_name = tracker_name)).count() == 0:
			#	#user requested a tracker that doesnt belong to him :(
			#	app.logger.warning('user requested a tracker that doesnt belong to him :(')
			#	return ErrorResponse('Tracker not available!').toDict()
			
			try:
				if current_user.query.filter(User.trackers.any(tracker_name = tracker_name)).count() == 0:
					#user requested a tracker that doesnt belong to him :(
					app.logger.warning('user requested a tracker that doesnt belong to him :(')
					return ErrorResponse('Tracker not available!').toDict()
			except Exception as e:
				print 'masik :() ' + str(e)
			
			try:
				current_tracker = current_user.trackers.filter_by(tracker_name = tracker_name).first()
			except Exception as e:
				print 'current_tracker ' + str(e)
			
			posList = []
			rawPosList = []
			filteredPosList = []
			
			if start_date == '' and end_date == '':
				#returning current position
				#### TODO !!! check if tracker belongs to the user!!!
		
				app.logger.debug('Client headers: ' + repr(request.headers))
				client_ip = getclientIP(request)
				
				gpspos = current_tracker.gpsposition.filter(gpsposition.gps_mode != 1).order_by(gpsposition.gps_time.desc()).first()
				#gpspos = gpsposition.query.filter_by(trackerid = tracker_name).filter(gpsposition.gps_mode != 1).order_by(gpsposition.gps_time.desc()).first()
				t = []
				temp = {}
				temp['lat'] = str(gpspos.gps_latitude)
				temp['lng'] = str(gpspos.gps_longitude)
				temp['alt'] = str(gpspos.gps_altitude)
				temp['speed'] = str(gpspos.gps_speed)
				temp['time'] = gpspos.gps_time.isoformat()
				t.append(temp)

				app.logger.debug('Latest position request response:' + repr(t))
				return GPSDataResponse(t).toDict(), 200
				
			if end_date == '':
				end_date = '2999-12-31'
				
			start = parse(start_date)
			end   = parse(end_date)

			#get the first data point, we dont filter this
			temp = current_tracker.gpsposition.filter.filter(gpsposition.gps_mode != 1).filter(gpsposition.gps_time.between(start, end)).order_by(gpsposition.gps_time.desc()).first()
			if temp is None:
				app.logger.warning('No GPS data found in DB for the requested dates')
				return ErrorResponse('No dota found for given dates!').toDict()
			gpspos_start = temp.toDict()


			#get the last data point, we dont filter this
			temp  = current_tracker.gpsposition.filter.filter(gpsposition.gps_mode != 1).filter(gpsposition.gps_time.between(start, end)).order_by(gpsposition.gps_time.asc()).first()
			if temp is None:
				app.logger.warning('No GPS data found in DB for the requested dates')
				return ErrorResponse('No dota found for given dates!').toDict()
			gpspos_end   = temp.toDict()


			for gpspos in current_tracker.gpsposition.filter.filter(gpsposition.gps_mode != 1).filter(gpsposition.gps_speed.between(app.config['GPS_MINIMUM_SPEED'], app.config['GPS_MAX_SPEED'])).filter(gpsposition.gps_time.between(start, end)).order_by(gpsposition.gps_time.asc()).all():
				temp = {}
				temp['lat'] = str(gpspos.gps_latitude)
				temp['lng'] = str(gpspos.gps_longitude)
				temp['alt'] = str(gpspos.gps_altitude)
				temp['speed'] = str(gpspos.gps_speed)
				temp['time'] = gpspos.gps_time.isoformat()
				posList.append(temp)
				rawPosList.append((float(temp['lat']), float(temp['lng'])))

			app.logger.info('Position list data length: %s' % (len(posList),))
			responselist = []
			responselist.append(gpspos_start)
			responselist += list(compress(posList, routefilter(rawPosList,5,0.5)))
			responselist.append(gpspos_end)

			app.logger.debug('Filered position list data length: %s' % (len(responselist)-2,))


			return GPSDataResponse(responselist).toDict(), 200
		except Exception as e:
			print str(e)
			app.logger.exception('Generic exception!')
			
			
class GPSTrackerConfig(Resource):
	
	#@login_required	
	def get(self, trackerid):
		#check if tracker belongs to the current user
		if current_user.query.filter(User.trackers.any(id = trackerid)).count() == 0:
			#user requested a tracker that doesnt belong to him :(
			app.logger.warning('user requested a tracker that doesnt belong to him :(')
			return ErrorResponse('Tracker not available!').toDict()
			
		tracker = TrackerTable.query.get(trackerid)
		
		response = make_response(tracker.bootstrap_config)
		# This is the key: Set the right header for the response
		# to be downloaded, instead of just printed on the browser
		response.headers["Content-Disposition"] = "attachment; filename=config.json"
		
		
		return response
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
	app.logger.warning( response.get_data())
	return response

"""		
# Views
@app.route('/scritps/<path:path>')
def serve_page(path):
	print path
	return send_from_directory(app.config['SCRIPTS_DIR'], path)

@app.route('/', methods=['GET'])
@login_required
def home():
	print 'home'
	return render_template('index.html')

@app.route('/gpstracker.html')
@login_required
def gpstrackerpage():
	return render_template('gpstracker.html')

@app.route('/gpslocation.html')
@login_required	
def gpslocationpage():
	return render_template('gpslocation.html')

	
