# -*- coding: utf-8 -*-

# stdlib imports
# third-party imports
import pytz
# django imports
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


# middleware

class RemoteAddrMiddleware(MiddlewareMixin):
	"""
	Middleware that sets REMOTE_ADDR based on HTTP_X_FORWARDED_FOR, if the
	latter is set. This is useful if you're sitting behind a reverse proxy that
	causes each request's REMOTE_ADDR to be set to 127.0.0.1.

	Note that this does NOT validate HTTP_X_FORWARDED_FOR. If you're not behind
	a reverse proxy that sets HTTP_X_FORWARDED_FOR automatically, do not use
	this middleware. Anybody can spoof the value of HTTP_X_FORWARDED_FOR, and
	because this sets REMOTE_ADDR based on HTTP_X_FORWARDED_FOR, that means
	anybody can "fake" their IP address. Only use this when you can absolutely
	trust the value of HTTP_X_FORWARDED_FOR.
	"""

	class InvalidRemoteAddr(ValueError):
		pass

	def process_request(self, request):
		# choose header field
		real_ip_header = getattr(settings, 'REAL_IP_HEADER', 'HTTP_X_REAL_IP')

		# get header value
		real_ip = request.META.get(real_ip_header)

		# ensure we have something
		if real_ip is None: return

		# split from commas
		real_ip_parts = real_ip.split(',')
		real_ip_parts = [p.strip() for p in real_ip_parts if p and p.strip()]
		real_ip = real_ip_parts[0]

		try:
			validate_ipv46_address(real_ip)
		except ValidationError:
			raise RemoteAddrMiddleware.InvalidRemoteAddr('invalid IP address: ' + str(real_ip))

		# if we made it this far, set the REMOTE_ADDR
		request.META['REMOTE_ADDR'] = real_ip
		pass

	pass
