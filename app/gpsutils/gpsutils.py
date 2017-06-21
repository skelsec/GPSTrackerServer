from rdp import rdp
from haversine import distance as gpsdistance


def routefilter(points, epsilon=0.5):
	for point in rdp(points, epsilon=epsilon):
		yield(point)