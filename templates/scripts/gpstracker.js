
var map = '';
var markersDict = {};
var routeSegmentDict = {};
var segmentRouteInfoRowDict = {};

var POSITION_API_URL = "/gpsposition";
var TRACKER_API_URL = "/gpstracker";


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

function shareGPSTracker(tracker_id){
	
	var http = new XMLHttpRequest();
	var URLbase = getBaseURL();
	var url = URLbase + TRACKER_API_URL ;
	var email =  document.getElementById('share_email_'+tracker_id).value;
	
	var params = JSON.stringify({cmd:"share", tracker_id: tracker_id, email: email})
	http.open("POST", url, true);

	//Send the proper header information along with the request
	http.setRequestHeader("Content-Type", "application/json");

	http.onreadystatechange = function() {//Call a function when the state changes.
		if(http.readyState == 4 && http.status == 200) {
			//alert(http.responseText);
			location.reload(true);
		}
	}
	http.send(params);	
}

function unshareGPSTracker(tracker_id, target_email){
	
	var http = new XMLHttpRequest();
	var URLbase = getBaseURL();
	var url = URLbase + TRACKER_API_URL ;
	
	var params = JSON.stringify({cmd:"unshare", tracker_id: tracker_id, email: target_email})
	http.open("POST", url, true);

	//Send the proper header information along with the request
	http.setRequestHeader("Content-Type", "application/json");

	http.onreadystatechange = function() {//Call a function when the state changes.
		if(http.readyState == 4 && http.status == 200) {
			//alert(http.responseText);
			location.reload(true);
		}
	}
	http.send(params);	
}

function addGPSTracker(){
	var http = new XMLHttpRequest();
	var URLbase = getBaseURL();
	var url = URLbase + TRACKER_API_URL ;
	
	var params = JSON.stringify({cmd:"create"})
	http.open("POST", url, true);

	//Send the proper header information along with the request
	http.setRequestHeader("Content-Type", "application/json");

	http.onreadystatechange = function() {//Call a function when the state changes.
		if(http.readyState == 4 && http.status == 200) {
			//alert(http.responseText);
			location.reload(true);
		}
	}
	http.send(params);
	
	
}


function refreshLatestCoordinates(){
	var URLbase = getBaseURL();
	var trackers = document.getElementById('tracker_list').children,
		maxElements = trackers.length,
		counter = 0,
		tmpAttribute;

	for (; counter < maxElements; counter++) {
		tracker = trackers[counter].getAttribute('id');
		var url = URLbase + POSITION_API_URL + '/' + tracker;
	
		getGPSData(url, GPSTrackerPlotLatest);
	}
	
	
	var trackers = document.getElementById('guest_tracker_list').children,
		maxElements = trackers.length,
		counter = 0,
		tmpAttribute;

	for (; counter < maxElements; counter++) {
		tracker = trackers[counter].getAttribute('id');
		var url = URLbase + POSITION_API_URL + '/' + tracker;
	
		getGPSData(url, GPSTrackerPlotLatest);
	}
	
	

}

function refreshRouteTrackerID(){
	//just takes the 
	var tracker_id = window.location.hash.substr(1);
	if (undefined == tracker_id){
		document.getElementById('input_tracker_id').value = '';
	}
	else{
		document.getElementById('input_tracker_id').value = tracker_id;
	}
}

function refreshRoutePath(){
	var URLbase = getBaseURL();
	var tracker = document.getElementById('input_tracker_id').value;
	var startdate = document.getElementById('route_start_datetime_text').value;
	var enddate = document.getElementById('route_end_datetime_text').value;
	
	if (tracker == ''){
		return;
	}
	if (startdate == ''){
		return;
	}
	if (enddate == ''){
		return;
	}
	
	//alert(tracker + "\r\n"+startdate+ "\r\n"+enddate);

	
	var url = URLbase + POSITION_API_URL + '/' + tracker + '/' + startdate + '/' + enddate;
	
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
				
		clearAllMarkers();
		//updateGPSLocationText(jresponse.data.gpsdatalist);
		plotGPSdata(jresponse.data.gpsdatalist);		
		}
	
}

function GPSTrackerPlotRoute(xmlhttp)
{
	if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
				var jresponse = JSON.parse(xmlhttp.responseText);
				if (jresponse.status != 'ok') { return "error"; }
				
				
				plotRouteData(jresponse.data.gpsroute);
				
			}
}

function showRouteInfoSummary(gpsroute){
	document.getElementById('summary_route_total_distance_travelled').innerText  = gpsroute.routeinfo.total_distance_travelled;
	document.getElementById('summary_route_time_travelled').innerText  = gpsroute.routeinfo.total_time;
	document.getElementById('summary_route_max_speed').innerText  = gpsroute.routeinfo.max_speed;
	document.getElementById('summary_route_avg_speed').innerText  = gpsroute.routeinfo.avg_speed;
	document.getElementById('summary_route_max_elev').innerText  = gpsroute.routeinfo.max_elevation;
	document.getElementById('summary_route_min_elev').innerText  = gpsroute.routeinfo.min_elevation;
	
}

function plotRouteData(gpsroute){
	clearAllRouteSegments();
	clearAllSegmentRouteInfo();
	
	showRouteInfoSummary(gpsroute);
	
	var trackerid = gpsroute.tracker_id;
	
	for (var i = 0; i < gpsroute.routesegments.length; i++) {
		var routeSegmentId = trackerid+'_'+i;
		plotRouteSegmentData(gpsroute.routesegments[i], routeSegmentId)
		showSegmentRouteInfo(gpsroute.routesegments[i], routeSegmentId);
	}
	
	
}

function clearSegmentRouteInfo(routeSegmentId){
	// Find a <table> element with id="myTable":
	var routesegmentinfotable = document.getElementById("routesegmentinfotable");

	// Create an empty <tr> element and add it to the 1st position of the table:
	var routeSegmentRowIndex = segmentRouteInfoRowDict[routeSegmentId];
	routesegmentinfotable.deleteRow(routeSegmentRowIndex);
	
}

function clearAllSegmentRouteInfo(){
	var routesegmentinfotable = document.getElementById("routesegmentinfotable");
	
	routesegmentinfotable.getElementsByTagName("tbody")[0].innerHTML = routesegmentinfotable.rows[0].innerHTML;
	segmentRouteInfoRowDict = {};	
}


function showSegmentRouteInfo(segment, routeSegmentId){
	// Find a <table> element with id="myTable":
	var routesegmentinfotable = document.getElementById("routesegmentinfotable");

	// Create an empty <tr> element and add it to the 1st position of the table:
	segmentRouteInfoRowDict[routeSegmentId] = routesegmentinfotable.length;
	var row = routesegmentinfotable.insertRow(routesegmentinfotable.length);
	

	// Insert new cells (<td> elements) at the 1st and 2nd position of the "new" <tr> element:
	var cell_color = row.insertCell(row.length);
	var cell_id = row.insertCell(row.length);
	var cell_total_distance_traveled = row.insertCell(row.length);
	var cell_time_travelled = row.insertCell(row.length);
	var cell_max_speed= row.insertCell(row.length);
	var cell_avg_speed = row.insertCell(row.length);
	var cell_max_elev = row.insertCell(row.length);
	var cell_min_elev = row.insertCell(row.length);
	var cell_enable = row.insertCell(row.length);
	var cell_save = row.insertCell(row.length);
	
	cell_total_distance_traveled.innerHTML = segment.routeinfo.total_distance_travelled;
	cell_color.innerHTML = '<button type="button" class="btn btn-primary btn-sm" style="background-color: '+segment.color+'" id="'+routeSegmentId+'_color">x</button>';
	cell_id.innerHTML = routeSegmentId;
	cell_time_travelled.innerHTML = segment.routeinfo.total_time;
	cell_max_speed.innerHTML = segment.routeinfo.max_speed;
	cell_avg_speed.innerHTML = segment.routeinfo.avg_speed;
	cell_max_elev.innerHTML = segment.routeinfo.max_elevation;
	cell_min_elev.innerHTML = segment.routeinfo.min_elevation;
	cell_enable.innerHTML = '<div class="material-switch pull-right"><input checked id="'+routeSegmentId+'_checkbox" name="'+routeSegmentId+'_showOnMap" type="checkbox" onclick="javascript:checkRouteSegment(\''+routeSegmentId+'\')" /><label for="'+routeSegmentId+'_checkbox" class="label-success"></label></div>';
	
	var URLbase = getBaseURL();
	var tracker = routeSegmentId.split('_')[0];
	var startdate = segment.filtered_route[0]['time'];
	var enddate = segment.filtered_route[segment.filtered_route.length-1]['time'];
	var url = URLbase + POSITION_API_URL + '/' + tracker + '/' + startdate + '/' + enddate+ '/GPX';
	
	cell_save.innerHTML = '<a href="'+url+'" type="button" class="btn btn-primary btn-sm" id="'+routeSegmentId+'_download">GPX</button>';
	
}

function plotRouteSegmentData(segment, routeSegmentId){
	segment['color'] = randomColor(); 
	
	var flightPlanCoordinates = [];
	for (var i = 0; i < segment.filtered_route.length; i++) {
		flightPlanCoordinates.push(
		{	
			lat : parseFloat(segment.filtered_route[i].lat),
			lng : parseFloat(segment.filtered_route[i].lng)
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
	
	markersDict[routeSegmentId+'_start'] = route_start_marker;
	markersDict[routeSegmentId+'_end'] = route_end_marker;
				
				
	var segmentPathBorder = new google.maps.Polyline({
				  path: flightPlanCoordinates,
				  geodesic: true,
				  strokeColor: 'black', // border color
				  strokeOpacity: 1.0,
				  strokeWeight: 7, // You can change the border weight here
				  map : map
	});
	
	var segmentPath = new google.maps.Polyline({
				  path: flightPlanCoordinates,
				  geodesic: true,
				  strokeColor: segment['color'],
				  strokeOpacity: 1.0,
				  strokeWeight: 4,
				  map : map
	});
	
				
	routeSegmentDict[routeSegmentId] = [segmentPath, segmentPathBorder];
}


function plotGPSdata(gpsdatalist) {
	//alert(gpsdatalist);
	
	gpsdatalist.latest_position

	var pinColor = gpsdatalist.html_color
	var pinImage = new google.maps.MarkerImage("http://www.googlemapsmarkers.com/v1/"+pinColor+"/");
	var point = new google.maps.LatLng(
				parseFloat(gpsdatalist.latest_position.lat),
				parseFloat(gpsdatalist.latest_position.lng));
				
	var infocontent = 'Tracker name: '+gpsdatalist.tracker_name + '<br>Latitude: '+gpsdatalist.latest_position.lat + '<br>Logitude: ' + gpsdatalist.latest_position.lng + '<br>Altitude: ' + gpsdatalist.latest_position.alt + '<br>Speed: '+ gpsdatalist.latest_position.speed + '<br>Time: '+ gpsdatalist.latest_position.time;
				
	var info = new google.maps.InfoWindow({
					content: infocontent
				});
	
	var marker = new google.maps.Marker({
		  icon: pinImage,
		  position: point,
		  clickable: true,
		  map : map
		  });
		  
	marker['infowindow'] = info;
				
	google.maps.event.addListener(marker, 'click', function () {
                this['infowindow'].open(map, this);
            });
			
	google.maps.event.addListener(marker, 'mouseover', function() {
        this['infowindow'].open(map, this);
    });
				
	
	markersDict[gpsdatalist.tracker_id] = marker;

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

function checkTracker(tracker_id){
	var checkbox = tracker_id+'_checkbox';
	if (document.getElementById(checkbox).checked){
		enableMarker(tracker_id);
	}
	else{
		disableMarker(tracker_id);
	}
	
}

function checkRouteSegment(routeSegmentId){
	var checkbox = routeSegmentId+'_checkbox';
	if (document.getElementById(checkbox).checked){
		enableRouteSegment(routeSegmentId);
	}
	else{
		disableRouteSegment(routeSegmentId);
	}
	
}

function clearAllMarkers() {
	Object.keys(markersDict).forEach(tracker_id => {
	  let marker = markersDict[tracker_id];
	  marker.setMap(null);
	  
	});
	
	markersDict = {};	
}

function disableMarker(tracker_id) {
	Object.keys(markersDict).forEach(key => {
		if (key == tracker_id){
		  let marker = markersDict[tracker_id];
		  marker.setMap(null);
		}
	  
	});
}

function enableMarker(tracker_id) {
	Object.keys(markersDict).forEach(key => {
		if (key == tracker_id){
		  let marker = markersDict[tracker_id];
		  marker.setMap(map);
		}
	  
	});
}


function clearAllRouteSegments() {
	Object.keys(routeSegmentDict).forEach(routeSegmentId => {
	  let routeSegment = routeSegmentDict[routeSegmentId];
	  routeSegment[0].setMap(null);
	  routeSegment[1].setMap(null);
	  
	});	
	routeSegmentDict = {};
	
	clearAllMarkers();
}

function disableRouteSegment(routeSegmentId) {
	Object.keys(routeSegmentDict).forEach(key => {
		if (key == routeSegmentId){
		  let routeSegment = routeSegmentDict[key];
		  routeSegment[0].setMap(null);
		  routeSegment[1].setMap(null);
		}
	  
	});
	

	disableMarker(routeSegmentId+'_start');
	disableMarker(routeSegmentId+'_end');
}


function enableRouteSegment(routeSegmentId) {
	Object.keys(routeSegmentDict).forEach(key => {
		if (key == routeSegmentId){
		  let routeSegment = routeSegmentDict[key];
		  routeSegment[0].setMap(map);
		  routeSegment[1].setMap(map);
		}
	  
	});
	enableMarker(routeSegmentId+'_start');
	enableMarker(routeSegmentId+'_end');
}

