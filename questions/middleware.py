from django.shortcuts import redirect
from django.conf import settings

from .models import Stage

class CurrentStageMiddleware(object):
	def process_view(self, request, view_func, view_args, view_kwargs):
		view_name = ".".join((view_func.__module__, view_func.__name__))

		if request.user.is_authenticated() and not view_name == settings.STAGE_SELECTION_VIEW:
			try:
				request.user.student.get_current_stage()
			except Stage.DoesNotExist:
				return redirect('pick_stage')
