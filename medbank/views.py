from django.shortcuts import render_to_response, redirect
from django.template import RequestContext, loader
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.http import HttpResponseServerError

import forms

def home(request):
    return render_to_response("base.html", context_instance=RequestContext(request))


def server_error(request):
    return HttpResponseServerError(loader.get_template('500.html').render(RequestContext(request)))


def create_user(request):
    if request.method == 'POST':
        form = forms.StudentCreationForm(request.POST)
        if form.is_valid():
            u = form.save(commit=False)
            u.email = "%s@sydney.edu.au" % (u.username, )
            u._stage = form.cleaned_data['stage']
            u.save()
            u = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password1'])
            login(request, u)
            return redirect("activity-mine")
    else:
        form = forms.StudentCreationForm()

    form.is_horizontal = True
    if request.method == 'POST':
        form.fields['username'].help_text = u""
    return render_to_response("user.html", {'form': form}, context_instance=RequestContext(request))


def logout_view(request):
    logout(request)

    return redirect('medbank.views.home')
