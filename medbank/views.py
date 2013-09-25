from django.shortcuts import render_to_response, redirect
from django.template import RequestContext, loader
from django.contrib.auth import logout
from django.contrib.auth import login, authenticate
from django.http import HttpResponseServerError
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.core import signing
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator


import forms
import queue
from questions import tasks


def class_view_decorator(function_decorator):
    """Convert a function based decorator into a class based decorator usable
    on class based Views.

    Can't subclass the `View` as it breaks inheritance (super in particular),
    so we monkey-patch instead.
    """

    def simple_decorator(View):
        View.dispatch = method_decorator(function_decorator)(View.dispatch)
        return View

    return simple_decorator


def home(request):
    return render_to_response("base-no-nav.html", {'next_url': reverse('activity-mine')}, context_instance=RequestContext(request))


def test(request, name):
    return render_to_response("%s.html" % name, context_instance=RequestContext(request))


def server_error(request):
    return HttpResponseServerError(loader.get_template('500.html').render(RequestContext(request)))


def create_user(request):
    if request.method == 'POST':
        form = forms.StudentCreationForm(request.POST)
        if form.is_valid():
            u = form.save(commit=False)
            u.email = "%s@uni.sydney.edu.au" % (u.username, )
            u._stage = form.cleaned_data['stage']
            u.save()
            u = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password1'])
            login(request, u)
            return redirect("activity-mine")
    else:
        form = forms.StudentCreationForm()

    form.is_horizontal = True
#    if request.method == 'POST':
#        form.fields['username'].help_text = u""
    return render_to_response("user.html", {'form': form}, context_instance=RequestContext(request))


def logout_view(request):
    logout(request)

    return redirect('medbank.views.home')

RESET_SALT = "asaltforpasswordrecovery123456789"

class ResetPassword(FormView):
    time_to_reset = 3600 * 24 * 2
    form_class = forms.PasswordResetForm
    template_name="password/reset.html"
    
    def get_success_url(self):
        return reverse('reset_password_success')

    def dispatch(self, request, *args, **kwargs):
        try:
            pk = signing.loads(kwargs['token'], salt=RESET_SALT, max_age=self.time_to_reset)
        except signing.BadSignature:
            return redirect('home')

        try:
            self.user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise PermissionDenied()

        return super(ResetPassword, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.user.set_password(form.cleaned_data['password1'])
        self.user.save()
        return super(ResetPassword, self).form_valid(form)

class ResetPasswordRequest(FormView):
    time_to_reset = 3600 * 24 * 2
    template_name = "password/reset_request.html"
    form_class = forms.PasswordResetRequestForm

    def get_success_url(self):
        return reverse('reset_password_sent')

    def send_email(self):
        token = signing.dumps(self.user.pk, salt=RESET_SALT)
        c = {
            'user': self.user,
            'reset_url': self.request.build_absolute_uri(reverse('reset_password', kwargs={'token': token}))
        }

        body = loader.render_to_string('password/email.html', c)

        from .tasks import ChangePasswordEmailTask
        t = ChangePasswordEmailTask(body, self.user.email)
        queue.add_task(t)

    def form_valid(self, form):
        self.user = form.cleaned_data['user']
        self.send_email()
        return super(ResetPasswordRequest, self).form_valid(form)


@class_view_decorator(login_required)
class FeedbackView(FormView):
    template_name = "feedback.html"
    form_class = forms.FeedbackForm

    def form_valid(self, form):
        c = form.cleaned_data
        t = tasks.EmailTask(
            "[MedBank] Feedback received from %s" % self.request.user.username,
            c['feedback'],
            ['michaelhagarty@gmail.com',],
        )

        queue.add_task(t)
        messages.success(self.request, "Your email has been sent successfully.")
        return redirect('medbank.views.home')
