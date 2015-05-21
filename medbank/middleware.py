from __future__ import unicode_literals

class ExtraErrorEmailInfoMiddleware(object):
	def process_exception(self, request, exception):
		try:
			if request.user.is_authenticated():
				request.META['USER_USERNAME'] = str(request.user.username)
		except:
			pass
