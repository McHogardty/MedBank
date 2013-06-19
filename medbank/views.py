from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate


def home(request):
    return render_to_response("base.html", context_instance=RequestContext(request))


def create_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            u = authenticate(username=form.cleaned_data['username'],password=form.cleaned_data['password1'])
            login(request, u)
            return redirect("questions.views.home")
    else:
        form = UserCreationForm()

    form.is_horizontal = True
    form.fields['username'].label = u'Unikey'
    form.fields['username'].help_text = u'Please use your Unikey so that we can email you the questions.'
    return render_to_response("user.html", {'form': form}, context_instance=RequestContext(request))


def logout_view(request):
    logout(request)

    return redirect('medbank.views.home')
