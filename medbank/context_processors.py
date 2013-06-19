def add_next_url(request):
    return {'next_url': request.get_full_path()}
