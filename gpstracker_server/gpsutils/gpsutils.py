from rdp import rdp
from geopy.distance import vincenty

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

def routefilter(rawpoints, slicesize = 10, epsilon=0.5):

	for points in chunks(rawpoints, slicesize):
		for point in rdp(points, epsilon=epsilon, return_mask=True):
			yield(point)
			
			
def GPSdistance(origin, destination):
	return vincenty(origin, destination).meters