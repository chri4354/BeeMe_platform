"use strict";

function csrfSafeMethod(method) {
	// these HTTP methods do not require CSRF protection
	return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function getCookie(name) {
	var cookieValue = null;
	if (document.cookie && document.cookie !== '') {
		var cookies = document.cookie.split(';');
		for (var i = 0; i < cookies.length; i++) {
			var cookie = jQuery.trim(cookies[i]);
			// Does this cookie string begin with the name we want?
			if (cookie.substring(0, name.length + 1) === (name + '=')) {
				cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
				break;
			}
		}
	}
	return cookieValue;
}

function getCSRFToken() {
	return getCookie('csrftoken');
}

if (jQuery) {
	jQuery.ajaxSetup({
		beforeSend: function(xhr, settings) {
			if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
				xhr.setRequestHeader( 'X-CSRFToken', getCSRFToken() );
			}
		}
	});
}

if (typeof Vue != 'undefined') if (Vue.http) {
	Vue.http.interceptors.push(function(request) {

		if (!csrfSafeMethod(request.method)) {
			request.headers.set( 'X-CSRFToken', getCSRFToken() );
		}

		request.emulateJSON = true;

	});
}

function TypeWriter(elem) {

	var self = this;
	var idx = 0;
	var speed = 50;

	var text = '';
	var timer = null;

	self.type = function type() {
		if (idx < text.length) {
			elem.innerHTML += text.charAt(idx);
			idx++;
			timer = setTimeout(self.type, speed);
		}
	};

	self.start = function start(msg) {
		idx = 0;
		text = msg;

		elem.innerHTML = '';

		self.type();
	};

}


$(function(){

	var $tos = $('#tos');

	if ( $tos.length > 0 ) {
		$tos.find('.btn-primary').click(function(){
			var url = $tos.attr('data-url');

			jQuery.ajax({
				data: { accept: '1' },
				method: 'POST',
				url: url,

				success: function success(data) {
					$tos.fadeOut();
				}
			});
		});
	}

});
