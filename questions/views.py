from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse, Http404, HttpResponseServerError
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.core.exceptions import PermissionDenied
import smtplib


import forms
import models
import document

import csv
import json
import datetime


class AllActivitiesView(ListView):
    model = models.TeachingActivity
    template_name = "all2.html"

    def get_latest_teaching_block(self):
        return models.TeachingBlock.objects.filter(start__lte=datetime.datetime.now().date).latest("start")

    def get_queryset(self):
        ta = models.TeachingActivity.objects.filter(block=self.get_latest_teaching_block())
        by_week = {}
        for t in ta:
            l = by_week.setdefault(t.week, [])
            l.append(t)

        for v in by_week.values():
            v.sort(key=lambda t: t.position)
        return [(k, not all(t.question_writer for t in by_week[k]), by_week[k]) for k in by_week]

    def get_context_data(self, **kwargs):
        c = super(AllActivitiesView, self).get_context_data(**kwargs)
        c['teaching_block'] = self.get_latest_teaching_block()
        return c


@permission_required('questions.can_approve')
def admin(request):
    return render_to_response('admin.html', context_instance=RequestContext(request))


def check_ta_perm_for_question(ta_id, u):
    ta = get_object_or_404(models.TeachingActivity, pk=ta_id)

    if not ta.question_writer == u:
        raise PermissionDenied

    return ta


class NewQuestion(CreateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "new.html"

    def dispatch(self, request, *args, **kwargs):
        self.ta = check_ta_perm_for_question(self.kwargs['ta_id'], self.request.user)
        if models.Question.objects.filter(teaching_activity=self.ta, creator=request.user).count() >= settings.QUESTIONS_PER_USER:
            messages.warning(request, "You have already submitted %d questions for this teaching activity." % settings.QUESTIONS_PER_USER)
            return redirect('ta', pk=self.ta.id)

        return super(NewQuestion, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        i = super(NewQuestion, self).get_initial().copy()
        i.update({'teaching_activity': self.ta, 'creator': self.request.user})
        return i

    def get_success_url(self):
        return reverse('view', kwargs={'pk': self.object.id, 'ta_id': self.ta.id})


class UpdateQuestion(UpdateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "new.html"

    def dispatch(self, request, *args, **kwargs):
        check_ta_perm_for_question(self.kwargs['ta_id'], self.request.user)

        return super(UpdateQuestion, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return models.Question.objects.filter(teaching_activity__id=self.kwargs['ta_id'])

    def get_object(self):
        o = super(UpdateQuestion, self).get_object()

        if o.creator != self.request.user:
            raise PermissionDenied

        return o

@login_required
def signup(request, ta_id):
    try:
        ta = models.TeachingActivity.objects.get(id=ta_id)
    except models.TeachingActivity.DoesNotExist:
        if request.is_ajax():
            HttpResponse(
                json.dumps({
                    'result': 'error',
                    'explanation': 'Hmm... this activity could not be found. Please try again.'
                }),
                mimetype="application/json"
            )
        else:
            messages.error(request, "Hmm... that teaching activity could not be found.")
            return redirect("questions.views.home")

    if ta.question_writer and ta.question_writer != request.user:
        if request.is_ajax():
            return HttpResponse(
                json.dumps({
                    'result': 'error',
                    'blurb': 'Taken',
                    'explanation': 'Sorry, this activity is already assigned to somebody else.'
                }),
                mimetype="application/json"
            )
        else:
            messages.error(request, "Sorry, that activity is already assigned to somebody else.")
            return redirect("questions.views.home")

    ta.question_writer = request.user
    ta.save()
    if request.is_ajax():
        return HttpResponse(
            json.dumps({
                'result': 'success',
                'view_url': reverse('ta', kwargs={'pk': int(ta_id)})
            }),
            mimetype="application/json"
        )
    else:
        return redirect("ta", pk=ta_id)


class NewActivity(CreateView):
    model = models.TeachingActivity
    template_name = "new_ta.html"
    form_class = forms.NewTeachingActivityForm


class ViewActivity(DetailView):
    model = models.TeachingActivity

    def get_context_data(self, **kwargs):
        c = super(ViewActivity, self).get_context_data(**kwargs)
        c['max_questions'] = settings.QUESTIONS_PER_USER
        print c
        return c


class ViewQuestion(DetailView):
    model = models.Question

    def get_context_data(self, **kwargs):
        c = super(ViewQuestion, self).get_context_data(**kwargs)
        c['show'] = 'show' in self.request.GET
        return c


@login_required
def view(request, ta_id, q_id):
    try:
        q = models.Question.objects.get(id=q_id)
    except models.Question.DoesNotExist:
        messages.error(request, "Hmm... that question could not be found")

    if q.teaching_activity.id != int(ta_id):
        messages.error(request, "Sorry, an unknown error occurred. Please try again.")
        return redirect('questions.views.home')

    return render_to_response("view.html", {'q': q, 'show': 'show' in request.GET}, context_instance=RequestContext(request))


@permission_required('questions.approve')
def approve(request, ta_id, q_id):
    try:
        q = models.Question.objects.get(id=q_id)
    except models.Question.DoesNotExist:
        messages.error(request, "Hmm... that question could not be found.")
        return redirect('questions.views.home')

    if q.teaching_activity.id != int(ta_id):
        messages.error(request, "Sorry, an unknown error occurred. Please try again.")
        return redirect('questions.views.home')

    if not q.approved():
        q.status = models.Question.APPROVED_STATUS
        q.save()

        messages.success(request, "Question approved.")
    return redirect('view', pk=q_id, ta_id=q.teaching_activity.id)


@permission_required('questions.approve')
def make_pending(request, ta_id, q_id):
    try:
        q = models.Question.objects.get(id=q_id)
    except models.Question.DoesNotExist:
        messages.error(request, "Hmm... that question could not be found.")
        return redirect('questions.views.home')

    if q.teaching_activity.id != int(ta_id):
        messages.error(request, "Sorry, an unknown error occurred. Please try again.")
        return redirect('questions.views.home')

    if not q.pending():
        q.status = models.Question.PENDING_STATUS
        q.save()

        messages.success(request, "Question is now pending.")

    return redirect('view', pk=q_id, ta_id=q.teaching_activity.id)


@permission_required('questions.can_approve')
def download(request, mode):
    tb = models.TeachingBlock.objects.filter(start__lte=datetime.datetime.now().date).latest("start")
    f = document.generate_document(tb, mode == "answer")
    r = HttpResponse(f.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    r['Content-Disposition'] = 'attachment; filename=questions.docx'
    f.close()
    return r


@permission_required('questions.can_approve')
def send(request):
    tb = models.TeachingBlock.objects.filter(
        start__lte=datetime.datetime.now().date
    ).latest("start")

    e = EmailMessage(
        'Questions for %s' % unicode(tb),
        "Hello.",
        "michaelhagarty@gmail.com",
        ["michaelhagarty@gmail.com"],
    )
    e.attach('questions.docx', document.generate_document(tb, False).getvalue())
    e.attach('answers.docx', document.generate_document(tb, True).getvalue())

    e.send()

    return redirect('questions.views.admin')

    print 'Getting connection'
    f = get_connection(False)
    con = smtplib.SMTP(f.host, f.port)
    print "Got connection"
    con.ehlo()
    con.starttls()
    con.ehlo()
    print "TLS Started"
    con.login(f.username, f.password)
    print "Authenticated"

    return redirect('questions.views.admin')


@login_required
def new_ta_upload(request):
    if request.method == "POST":
        if 'id' in request.POST:
            blocks = {}
            y = request.POST.get('year')
            blocks = dict((b.name.lower(), b) for b in models.TeachingBlock.objects.filter(year=y))
            b = request.POST.getlist('new_block')
            i = request.POST.getlist('id')
            r = request.POST.copy()
            for bb in b:
                p = ''.join(e.lower() for e in bb if e.isalnum())
                r.update({'%s-year' % p: y, '%s-name' % p: bb})
                f = forms.NewTeachingBlockForm(
                    r,
                    prefix=p
                )
                if f.is_valid():
                    bb = f.save()
                else:
                    return redirect('questions.views.new_ta_upload')
                blocks[bb.name] = bb
            for ii in i:
                data = {
                    'id': ii,
                    'name': request.POST.get('name_%s' % ii),
                    'block': blocks[request.POST.get('block_%s' % ii)].id,
                    'week': request.POST.get('week_%s' % ii),
                    'position': request.POST.get('position_%s' % ii)
                }
                f = forms.NewTeachingActivityForm(data)
                if f.is_valid():
                    f.save()
                else:
                    return redirect('questions.views.new_ta_upload')
            return redirect('questions.views.home')
        else:
            form = forms.TeachingActivityBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                y = form.cleaned_data['year']
                r = list(csv.reader(form.cleaned_data['ta_file'].read().splitlines()))
                h = [hh.lower() for hh in r[0]]
                by_position = {}
                by_name = {}
                by_block = {}
                already_exist = []
                blocks = list(set(dict(zip(h, row))['block'] for row in r[1:]))
                errors = []
                existing_blocks = dict((b.name.lower(), b) for b in models.TeachingBlock.objects.filter(year=y))
                new_blocks = {}
                b = {}
                for bb in blocks:
                    if bb.lower() in existing_blocks:
                        bb = existing_blocks[bb.lower()]
                    else:
                        d = {'year': y, 'name': bb}
                        f = forms.TeachingBlockValidationForm(d)
                        if f.is_valid():
                            bb = f.save(commit=False)
                        new_blocks[d['name']] = forms.NewTeachingBlockDetailsForm(
                            prefix=''.join(e.lower() for e in d['name'] if e.isalnum())
                        )
                    b[bb.name] = bb
                    by_block[bb] = []
                for row in r[1:]:
                    f = forms.TeachingActivityValidationForm(dict(zip(h, row)))
                    if f.is_valid():
                        ta = f.save(commit=False)
                        l = by_position.setdefault((ta.week, ta.position), [])
                        l.append(ta)
                        l = by_name.setdefault(ta.name.lower(), [])
                        l.append(ta)
                        by_block[b[dict(zip(h, row))['block']]].append(ta)
                    else:
                        if str(f.errors).find("exists"):
                            already_exist.append(dict(zip(h, row)))
                        else:
                            errors.append(dict(zip(h, row)))
                if errors or already_exist:
                    return render_to_response(
                        "upload.html",
                        {'errors': errors, 'already_exist': already_exist},
                        context_instance=RequestContext(request)
                    )
                else:
                    dup_by_position = [v for k, v in by_position.iteritems() if len(v) > 1]
                    dup_by_name = [v for k, v in by_name.iteritems() if len(v) > 1]
                    if dup_by_position or dup_by_name:
                        return render_to_response(
                            "upload.html",
                            {
                                'duplicates': True,
                                'dup_by_position': dup_by_position,
                                'dup_by_name': dup_by_name
                            },
                            context_instance=RequestContext(request)
                        )
                    else:
                        for bb in by_block:
                            by_block[bb].sort(key=lambda ta: (ta.week, ta.position))
                        return render_to_response(
                            "upload.html",
                            {
                                'tab': by_block,
                                'blocks': b.keys(),
                                'year': y,
                                'new_blocks': new_blocks
                            },
                            context_instance=RequestContext(request)
                        )
    else:
        form = forms.TeachingActivityBulkUploadForm()
    return render_to_response("upload.html", {'form': form, }, context_instance=RequestContext(request))
