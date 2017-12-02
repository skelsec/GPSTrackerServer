import os

os.environ['GPSTRACKERCONFIG_FIRSTRUN'] = 'AAAAAA'
os.environ['GPSTRACKERCONFIG'] = 'config.py'
from gpstracker_server import app as application

if __name__ == "__main__":
	if application.config['HOST'] != '127.0.0.1':
		application.logger.info('You are running the web interface including non-localhost! This is dangerous but YOLO!')

	application.run(host = application.config['HOST'], port = application.config['PORT'])
