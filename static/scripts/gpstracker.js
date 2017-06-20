
var map = '';
var markersArray = [];
var flightPathArray = [];

var POSITION_API_URL = "/gpstracker/position/";
var POSITION_API_URL_LATEST = "/latest";


function initMap() {
    var centepoint = {lat: 50, lng: 0};
	
    map = new google.maps.Map(document.getElementById('map'), {
      zoom: 4,
      center: centepoint
    });
}

function getBaseURL(){
	
	var pathArray = location.href.split( '/' );
	var protocol = pathArray[0];
	var host = pathArray[2];
	var url = protocol + '//' + host;
	return url;
	
}


function refreshLatestCoordinate(){
	var URLbase = getBaseURL();
	var client = document.getElementById('client').value;
	var url = URLbase + POSITION_API_URL + client + POSITION_API_URL_LATEST;
	
	getGPSData(url, GPSTrackerPlotLatest);

}

function refreshRoutePath(){
	var URLbase = getBaseURL();
	var client = document.getElementById('client').value;
	var startdate = document.getElementById('startdate').value;
	var enddate = document.getElementById('enddate').value;
	var interval = document.getElementById('interval').value;

	
	var url = URLbase + POSITION_API_URL + client + '/' + startdate + '/' + enddate +'/'+interval;
	
	getGPSData(url, GPSTrackerPlotRoute);
}


function getGPSData(url, callback) {
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
		if (this.readyState == 4 && this.status == 200) {
		  callback(this);
		}
	 };
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
}

function GPSTrackerPlotLatest(xmlhttp){
	
	if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
		var jresponse = JSON.parse(xmlhttp.responseText);
		if (jresponse.status != 'ok') { return "error"; }
				
		clearMarkers();
		updateGPSLocationText(jresponse.data.gpsdatalist);
		plotGPSdata(jresponse.data.gpsdatalist);		
		}
	
}

function GPSTrackerPlotRoute(xmlhttp)
{
	if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
				var jresponse = JSON.parse(xmlhttp.responseText);
				if (jresponse.status != 'ok') { return "error"; }
				
				clearMarkers();
				clearFlightPath();
				plotRouteData(jresponse.data.gpsdatalist);		
			}
}

function plotRouteData(gpsdatalist){
	var flightPlanCoordinates = [];
	for (var i = 0; i < gpsdatalist.length; i++) {
		flightPlanCoordinates.push(
		{	
			lat : parseFloat(gpsdatalist[i].lat),
			lng : parseFloat(gpsdatalist[i].lng)
		});
	}
				
	var route_start_marker = new google.maps.Marker({
						position: flightPlanCoordinates[0],
						map : map
	});
				  
	var route_end_marker = new google.maps.Marker({
						position: flightPlanCoordinates[flightPlanCoordinates.length - 1],
						map : map
	});
				  
	markersArray.push(route_start_marker);
	markersArray.push(route_end_marker);
				
				
	var flightPath = new google.maps.Polyline({
				  path: flightPlanCoordinates,
				  geodesic: true,
				  strokeColor: '#FF0000',
				  strokeOpacity: 1.0,
				  strokeWeight: 2,
				  map : map
	});
				
	flightPathArray.push(flightPath);	
}


function plotGPSdata(gpsdatalist) {
	
	for (var i = 0; i < gpsdatalist.length; i++) {
			var point = new google.maps.LatLng(
				parseFloat(gpsdatalist[i].lat),
				parseFloat(gpsdatalist[i].lng));
				
			var marker = new google.maps.Marker({
			  position: point,
			  map : map
			  });
			 markersArray.push(marker);
		}	
}
function updateGPSLocationText(gpsdatalist){
	
	for (var i = 0; i < gpsdatalist.length; i++) {
			document.getElementById('gpslat').value = gpsdatalist[i].lat;
			document.getElementById('gpslng').value = gpsdatalist[i].lng;
			document.getElementById('gpselv').value = gpsdatalist[i].elv;
			document.getElementById('gpsspeed').value = gpsdatalist[i].speed;
			document.getElementById('gpstime').value = gpsdatalist[i].time;
		}
}

function clearMarkers() {
	while(markersArray.length) { markersArray.pop().setMap(null); }
}

function clearFlightPath() {
		while(flightPathArray.length) { flightPathArray.pop().setMap(null); }
	}

































