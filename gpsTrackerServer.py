#!/usr/bin/env python
from app import app, db
from flask import request, send_from_directory
from flask_restful import Resource, Api
from sqlalchemy import text
import json
import gzip
import cStringIO
import datetime
from itertools import compress


from app.gpsutils.gpsutils import routefilter
from dateutil.parser import parse
from gpsDB import gpsposition, gpsjsondata

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
class OKResponse(JsonResponse):
	def __init__(self):
		JsonResponse.__init__(self, 'ok','')

class ClientReciever(Resource):
    def post(self, client_name):
		#TODO!
		client_ip = '127.0.0.1'
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
						gpsp = gpsposition(gpsdata, client_name, client_ip, upload_time)
						db.session.add(gpsp)

					gpsraw = gpsjsondata(line, client_name, client_ip, upload_time)
					db.session.add(gpsraw)
					db.session.commit()
				except Exception as e:
					app.logger.exception('Error parsing client GPS data!')
					return ErrorResponse('Error parsing data!').toDict()

		except:
			#log
			return ErrorResponse('Error decompressing data!').toDict()

		return OKResponse().toDict(), 200

class GetLatestPosition(Resource):
	def get(self, client_name):
		app.logger.debug('Client headers: ' + repr(request.headers))
		gpspos = gpsposition.query.filter_by(client_name = client_name).filter(gpsposition.gps_mode != 1).order_by(gpsposition.gps_time.desc()).first()
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

class GetPosition(Resource):
	def get(self, client_name, start_date, end_date, interval = 1):
		try:
			### TODO!!!
			interval = 1
			GPS_MINIMUM_SPEED = 2 #km/h
			GPS_MAX_SPEED = 300 #km/h 
			#########

			start = parse(start_date)
			end   = parse(end_date)
			posList = []
			rawPosList = []
			filteredPosList = []

			#get the first data point, we dont filter this
			temp = gpsposition.query.filter_by(client_name = client_name).filter(gpsposition.gps_mode != 1).filter(gpsposition.gps_time.between(start, end)).order_by(gpsposition.gps_time.desc()).first()
			if temp is None:
				app.logger.warning('No GPS data found in DB for the requested dates')
				return ErrorResponse('No dota found for given dates!').toDict()
			gpspos_start = temp.toDict()


			#get the last data point, we dont filter this
			temp  = gpsposition.query.filter_by(client_name = client_name).filter(gpsposition.gps_mode != 1).filter(gpsposition.gps_time.between(start, end)).order_by(gpsposition.gps_time.asc()).first()
			if temp is None:
				app.logger.warning('No GPS data found in DB for the requested dates')
				return ErrorResponse('No dota found for given dates!').toDict()
			gpspos_end   = temp.toDict()


			#query = text(	"SELECT * FROM ("
			#		" SELECT @row := @row +1 AS rownum, gpsposition.*"
			#		" FROM ( SELECT @row :=0) r, gpsposition WHERE gps_mode <> 1 AND gps_time BETWEEN :start AND :end) ranked"
			#		" WHERE rownum %:interval = 1" )

			for gpspos in gpsposition.query.filter_by(client_name = client_name).filter(gpsposition.gps_mode != 1).filter(gpsposition.gps_speed.between(GPS_MINIMUM_SPEED, GPS_MAX_SPEED)).filter(gpsposition.gps_time.between(start, end)).order_by(gpsposition.gps_time.asc()).all():
			#for gpspos in db.engine.execute(query,  all='*' , tablename='gpsposition', start = start.isoformat(), end = end.isoformat(), interval = interval):
			#for gpspos in db.engine.execute(query, start = start.isoformat(), end = end.isoformat(), interval = interval):
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

@app.route('/scritps/<path:path>')
def serve_page(path):
	print path
	return send_from_directory(app.config['SCRIPTS_DIR'], path)



@app.route('/')
def root():
    return app.send_static_file('index.html')

