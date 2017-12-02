
$(function () {
	$('#route_start_datetime').datetimepicker({
		format: 'YYYY-MM-DDTHH:mm:ssZ',
		defaultDate: moment().subtract(1, 'days'),
		useCurrent: false
	});
});
$(function () {
	$('#route_end_datetime').datetimepicker({
		format: 'YYYY-MM-DDTHH:mm:ssZ',
		defaultDate: moment()
	});
});