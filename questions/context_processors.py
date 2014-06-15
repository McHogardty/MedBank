def add_student(request):
	student = {}
	try:
		student['student'] = request.user.student
	except AttributeError:
		pass

	return student


def add_query_string(request):
    query_string = {}
    allowed = ['show', 'approve', 'flagged', 'assigned']
    allowed_with_parameters = ['total', 'progress']
    g = request.GET.keys()

    params = [k for k in g if k in allowed]
    params += ["%s=%s" % (k, request.GET[k]) for k in g if k in allowed_with_parameters]
    query_string['approval_query_string'] = "?%s" % ("&".join(params)) if params else ""

    if 'show' in params:
        idx = params.index('show')
        del params[idx]
    else:
        params.append('show')

    query_string['approval_query_string_show_inverted'] = "?%s" % ("&".join(params)) if params else ""
    return query_string