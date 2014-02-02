def add_student(request):
	student = {}
	try:
		student['student'] = request.user.student
	except AttributeError:
		pass

	return student