from __future__ import unicode_literals

def add_next_url(request):
    return {'next_url': request.get_full_path()}

def add_impersonator(request):
	d = {}
	if hasattr(request, "impersonator"):
		d['impersonator'] = request.impersonator

	return d