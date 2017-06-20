#!/usr/bin/env python
from app import app, db
from flask import request, send_from_directory
from flask_restful import Resource, Api
from sqlalchemy import text
import json
import gzip
import cStringIO
import datetime

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
			print 'Error POST DATA SIZE'
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
						print 'Strange!'
						return 'Error'

					if gpsdata['class'] == 'TPV':
						gpsp = gpsposition(gpsdata, client_name, client_ip, upload_time)
						db.session.add(gpsp)

					gpsraw = gpsjsondata(line, client_name, client_ip, upload_time)
					db.session.add(gpsraw)
					db.session.commit()
				except Exception as e:
					print 'Error parsing GPS data! Data: '+str(e)
					return ErrorResponse('Error parsing data!').toDict()

		except:
			#log
			return ErrorResponse('Error decompressing data!').toDict()

		return OKResponse().toDict(), 200

class GetLatestPosition(Resource):
	def get(self, client_name):
		print request.headers
		gpspos = gpsposition.query.filter_by(client_name = client_name).filter(gpsposition.gps_mode != 1).order_by(gpsposition.gps_time.desc()).first()
		t = []
		temp = {}
		temp['lat'] = str(gpspos.gps_latitude)
		temp['lng'] = str(gpspos.gps_longitude)
		temp['alt'] = str(gpspos.gps_altitude)
		temp['speed'] = str(gpspos.gps_speed)
		temp['time'] = gpspos.gps_time.isoformat()
		t.append(temp)

		print temp
		return GPSDataResponse(t).toDict(), 200

class GetPosition(Resource):
	def get(self, client_name, start_date, end_date, interval = 10):
		start = parse(start_date)
		end   = parse(end_date)
		posList = []
		query = text(	"SELECT * FROM ("
				" SELECT @row := @row +1 AS rownum, gpsposition.*"
				" FROM ( SELECT @row :=0) r, gpsposition WHERE gps_mode <> 1 AND gps_time BETWEEN :start AND :end) ranked"
				" WHERE rownum %:interval = 1" )

		#for gpspos in gpsposition.query.filter_by(client_name = client_name).filter(gpsposition.gps_time.between(start, end)).order_by(gpsposition.gps_time.desc()):
		#for gpspos in db.engine.execute(query,  all='*' , tablename='gpsposition', start = start.isoformat(), end = end.isoformat(), interval = interval):
		for gpspos in db.engine.execute(query, start = start.isoformat(), end = end.isoformat(), interval = interval):
			temp = {}
			temp['lat'] = str(gpspos.gps_latitude)
			temp['lng'] = str(gpspos.gps_longitude)
			temp['alt'] = str(gpspos.gps_altitude)
			temp['speed'] = str(gpspos.gps_speed)
			temp['time'] = gpspos.gps_time.isoformat()
			posList.append(temp)
		print len(posList)

		return GPSDataResponse(posList).toDict(), 200

@app.route('/scritps/<path:path>')
def serve_page(path):
	print path
	return send_from_directory(app.config['SCRIPTS_DIR'], path)



@app.route('/')
def root():
    return app.send_static_file('index.html')	
	
	
	
	
	
	
	
	
	
	
	
	
