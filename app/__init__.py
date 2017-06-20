from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api
from flask_cors import CORS
from pathlib2 import Path, PurePath


p = Path(__file__)
basedir = str(p.parents[1])


pr = PurePath(basedir)
static_folder =str(pr.joinpath('static'))

app = Flask(__name__, static_folder = static_folder ,static_url_path='')
app.config.from_pyfile('config.py')
CORS(app)
print app.config
api = Api(app)
db = SQLAlchemy(app)

from gpsTrackerServer import ClientReciever, GetLatestPosition, GetPosition


api.add_resource(ClientReciever, '/gpstracker/upload/<string:client_name>')
api.add_resource(GetLatestPosition, '/gpstracker/position/<string:client_name>/latest')
api.add_resource(GetPosition, '/gpstracker/position/<string:client_name>/<string:start_date>/<string:end_date>/<int:interval>')
