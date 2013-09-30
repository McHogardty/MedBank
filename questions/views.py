from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse, Http404, HttpResponseServerError
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django import db
import smtplib


import forms
import models
import document
import queue
import tasks

import csv
import json
import datetime
import collections


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


@class_view_decorator(login_required)
class AllBlocksView(ListView):
    model = models.TeachingBlock
    template_name = "choose.html"

    def get_queryset(self):
        bb = models.TeachingBlock.objects.filter(year=datetime.datetime.now().year, stage=self.request.user.student.get_current_stage())

        if 'pending' in self.request.GET:
            bb = bb.filter(activities__questions__status=models.Question.PENDING_STATUS).distinct()
        elif 'flagged' in self.request.GET:
            bb = bb.filter(activities__questions__status=models.Question.FLAGGED_STATUS).distinct()
        return bb

    def get_context_data(self, **kwargs):
        c = super(AllBlocksView, self).get_context_data(**kwargs)
        c.update({'flagged': 'flagged' in self.request.GET})
        return c


@class_view_decorator(login_required)
class MyActivitiesView(ListView):
    model = models.TeachingActivity
    template_name = "mine.html"

    def get_queryset(self):
        ret = {}
        ta = models.TeachingActivity.objects.filter(question_writers=self.request.user).order_by('week', 'position')
        for t in ta:
            l = ret.setdefault(t.current_block(), [])
            l.append(t)
        ret = ret.items()
        ret.sort(key=lambda a: a[0].number)
        return ret


@class_view_decorator(login_required)
class AllActivitiesView(ListView):
    model = models.TeachingActivity
    template_name = "all2.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(AllActivitiesView, self).dispatch(request, *args, **kwargs)
        b = self.teaching_block
        s = self.request.user.student
        if not b.stage == s.get_current_stage() and not b.question_count_for_student(s):
            raise Http404
        if not b.can_write_questions or b.email_sent:
            messages.error(request, "That block cannot be accessed right now.")
            return redirect('block-list')
        return r

    def get_teaching_block(self):
        tb = models.TeachingBlock.objects.get(number=self.kwargs['number'], year=self.kwargs['year'])
        self.teaching_block = tb
        return tb

    def get_queryset(self):
        ta = models.TeachingActivity.objects.filter(block__number=self.kwargs['number'], block__year=self.kwargs['year'])
        by_week = {}
        for t in ta:
            l = by_week.setdefault(t.week, [])
            l.append(t)

        for v in by_week.values():
            v.sort(key=lambda t: (t.activity_type, t.position))
        return [(k, not all(t.enough_writers() for t in by_week[k]), by_week[k]) for k in by_week]

    def get_context_data(self, **kwargs):
        c = super(AllActivitiesView, self).get_context_data(**kwargs)
        c['teaching_block'] = self.get_teaching_block()
        return c


@class_view_decorator(permission_required('questions.can_approve'))
class AdminView(TemplateView):
    template_name = 'admin.html'

    def get_context_data(self, **kwargs):
        c = super(AdminView, self).get_context_data(**kwargs)
        tb = models.TeachingBlock.objects.order_by('stage')
        questions_pending = any(b.questions_need_approval() for b in tb)
        questions_flagged = any(b.questions_flagged_count() for b in tb)
        c.update({'blocks': tb, 'questions_pending': questions_pending, 'questions_flagged': questions_flagged,})
        return c


class QueryStringMixin(object):
    def query_string(self):
        allowed = ['show', 'approve', 'flagged']
        g = self.request.GET.keys()
        if not g:
            return ""
        params = [k for k in g if k in allowed]
        return "?%s" % ("&".join(params))


@class_view_decorator(permission_required('questions.can_approve'))
class StartApprovalView(QueryStringMixin, RedirectView):
    permanent = False

    def query_string(self, initial):
        if initial:
            qs =  "?show&approve"
            if 'flagged' in self.request.GET:
                qs += "&flagged"
            return qs
        else:
            return super(StartApprovalView, self).query_string()

    def get_redirect_url(self, pk, q_id=None):
        try:
            b = models.TeachingBlock.objects.get(pk=pk)
        except models.TeachingBlock.DoesNotExist:
            messages.error(self.request, "That teaching block does not exist.")
            return reverse('admin')
        tb = models.TeachingBlock.objects.filter(start__lte=datetime.datetime.now().date).latest("start")

        previous_q = None
        try:
            previous_q = models.Question.objects.get(pk=q_id)
        except models.Question.DoesNotExist:
            pass
        if 'flagged' in self.request.GET:
            s = models.Question.FLAGGED_STATUS
        else:
            s = models.Question.PENDING_STATUS
        q = models.Question.objects.filter(teaching_activity__block=b).filter(
                db.models.Q(status=s) | db.models.Q(pk=q_id)
            )
        try:
            if previous_q:
                q = q.filter(date_created__gte=previous_q.date_created).order_by('date_created')[1:2].get()
            else:
                q = q.order_by('date_created')[:1].get()
        except models.Question.DoesNotExist:
            m = 'All questions for that block have been approved'
            if 'flagged' in self.request.GET:
                m = 'There are no more flagged questions in that block.'
            messages.success(self.request, m)
            return reverse('admin')
        return "%s%s" % (reverse('view', kwargs={'pk': q.id, 'ta_id': q.teaching_activity.id}), self.query_string(previous_q == None))


@class_view_decorator(permission_required('questions.can_approve'))
class ApproveQuestionsView(ListView):
    model = models.Question
    template_name = "approve.html"

    def get_query_set(self):
        return models.Question.objects.filter(teaching_activity__block=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        c = super(ApproveQuestionsView, self).get_context_data(**kwargs)
        c['questions'] = self.get_queryset()
        return c


def check_ta_perm_for_question(ta_id, u):
    ta = get_object_or_404(models.TeachingActivity, pk=ta_id)

    if not u.student in ta.question_writers.all() and not u.has_perm("questions.can_approve"):
        raise PermissionDenied

    return ta


@class_view_decorator(login_required)
class NewQuestion(CreateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "new.html"

    def dispatch(self, request, *args, **kwargs):
        self.ta = check_ta_perm_for_question(self.kwargs['ta_id'], self.request.user)
        if not self.ta.current_block().can_write_questions:
            messages.warning(request, "You are not currently able to write questions for this teaching activity.")
            return redirect('ta', pk=self.ta.id)
        if models.Question.objects.filter(teaching_activity=self.ta, creator=request.user.student).exclude(status=models.Question.DELETED_STATUS).count() >= settings.QUESTIONS_PER_USER:
            messages.warning(request, "You have already submitted %d questions for this teaching activity." % settings.QUESTIONS_PER_USER)
            return redirect('ta', pk=self.ta.id)
        return super(NewQuestion, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        i = super(NewQuestion, self).get_initial().copy()
        i.update({'teaching_activity': self.ta, 'creator': self.request.user.student})
        return i

    def get_success_url(self):
        return reverse('view', kwargs={'pk': self.object.id, 'ta_id': self.ta.id})


@class_view_decorator(login_required)
class UpdateQuestion(QueryStringMixin, UpdateView):
    model = models.Question
    form_class = forms.NewQuestionForm
    template_name = "new.html"

    def dispatch(self, request, *args, **kwargs):
        self.ta = check_ta_perm_for_question(self.kwargs['ta_id'], self.request.user)
        return super(UpdateQuestion, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return models.Question.objects.filter(teaching_activity__id=self.kwargs['ta_id'])

    def get_object(self):
        o = super(UpdateQuestion, self).get_object()

        if o.creator != self.request.user.student and not self.request.user.has_perm('questions.can_approve'):
            raise PermissionDenied

        return o

    def get_form_kwargs(self):
        k = super(UpdateView, self).get_form_kwargs()
        if self.request.user.has_perm("questions.can_approve") and self.get_object().creator != self.request.user:
            k.update({'admin': True})
        return k

    def form_valid(self, form):
        o = self.get_object()
        if self.request.user.has_perm("questions.can_approve") and o.creator != self.request.user:
            c = form.cleaned_data
            if c['reason']:
                r = models.Reason()
                r.body = c['reason']
                r.creator = self.request.user.student
                r.question = o
                r.save()
        return super(UpdateQuestion, self).form_valid(form)


    def get_success_url(self):
        return "%s%s" % (reverse('view', kwargs={'pk': self.object.id, 'ta_id': self.ta.id}), self.query_string())


@class_view_decorator(login_required)
class UnassignView(RedirectView):
    permanent = False

    def get_redirect_url(self, pk):
        try:
            ta = models.TeachingActivity.objects.get(pk=pk)
        except models.TeachingActivity.DoesNotExist:
            return reverse('medbank.views.home')
        if not ta.question_writers.filter(user=self.request.user).count():
            messages.warning(self.request, "You weren't signed up to that activity")
            return reverse('ta', kwargs={'pk': pk})

        if ta.questions_for(self.request.user).count():
            messages.error(self.request, "Once you have started writing questions for an activity, you can't unassign yourself from it.")
            return reverse('ta', kwargs={'pk': pk})

        ta.question_writers.remove(self.request.user.student)
        messages.success(self.request, "You have been unassigned from that activity")
        return reverse('ta', kwargs={'pk': pk})


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

    already_assigned = request.user.student in ta.question_writers.all()

    if not already_assigned:
        if ta.enough_writers():
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

        ta.question_writers.add(request.user.student)
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


@class_view_decorator(login_required)
class NewActivity(CreateView):
    model = models.TeachingActivity
    template_name = "new_ta.html"
    form_class = forms.NewTeachingActivityForm

    def get_context_data(self, **kwargs):
        c = super(NewActivity, self).get_context_data(**kwargs)
        c['heading'] = "activity"
        return c


@class_view_decorator(login_required)
class NewBlock(CreateView):
    model = models.TeachingBlock
    template_name = "new_ta.html"
    form_class = forms.NewTeachingBlockForm

    def get_context_data(self, **kwargs):
        c = super(NewBlock, self).get_context_data(**kwargs)
        c['heading'] = "block"
        return c

    def get_success_url(self):
        return reverse('admin')


@class_view_decorator(login_required)
class ViewActivity(DetailView):
    model = models.TeachingActivity


@class_view_decorator(login_required)
class ViewQuestion(DetailView):
    model = models.Question

    def dispatch(self, request, *args, **kwargs):
        r = super(ViewQuestion, self).dispatch(request, *args, **kwargs)

        if self.object.pending and not self.object.user_is_creator(self.request.user):
            raise Http404
        if self.object.deleted and not self.request.user.has_perm("can_approve"):
            raise Http404

        return r

    def get_context_data(self, **kwargs):
        c = super(ViewQuestion, self).get_context_data(**kwargs)
        c['show'] = 'show' in self.request.GET
        c['approval_mode'] = 'approve' in self.request.GET
        c['flagged_mode'] = 'flagged' in self.request.GET
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


@class_view_decorator(permission_required("questions.can_approve"))
class ChangeStatus(RedirectView):
    permanent = False

    def query_string(self):
        g = self.request.GET
        if not g:
            return ""
        qs = "?"
        if 'show' in g:
            qs += 'show'
            if 'approve' in g:
                qs += "&"
        if 'approve' in g:
            qs += "approve"

        return qs

    def get_redirect_url(self, ta_id, q_id, action):
        print "Using status change view"
        actions_to_props = {
            'approve': 'approved',
            'pending': 'pending',
            'delete': 'deleted',
            'flag': 'flagged'
        }
        try:
            q = models.Question.objects.get(id=q_id)
        except models.Question.DoesNotExist:
            messages.error(self.request, "Hmm... that question could not be found.")
            return redirect('questions.views.home')

        if q.teaching_activity.id != int(ta_id):
            messages.error(self.request, "Sorry, an unknown error occurred. Please try again.")
            return redirect('questions.views.home')

        print getattr(q, actions_to_props[action])
        if not getattr(q, actions_to_props[action]):
            print getattr(models.Question, '%s_STATUS' % actions_to_props[action].upper())
            q.status = getattr(models.Question, '%s_STATUS' % actions_to_props[action].upper())
            q.approver = self.request.user.student
            q.save()

        r = "%s%%s"
        if 'approve' in self.request.GET:
            r = r % reverse('admin-approve', kwargs={'pk': q.teaching_activity.current_block().id, 'q_id': q.id})
        else:
            r = r % reverse('view', kwargs={'pk': q_id, 'ta_id': q.teaching_activity.id})
        r = r % self.query_string()
        return r


@permission_required('questions.can_approve')
def download(request, pk, mode):
    try:
        tb = models.TeachingBlock.objects.get(pk=pk)
    except models.TeachingBlock.DoesNotExist:
        messages.error(request, 'That block does not exist.')
        return redirect('admin')
    f = document.generate_document(tb, mode == "answer")
    r = HttpResponse(f.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    r['Content-Disposition'] = 'attachment; filename=questions.docx'
    f.close()
    return r


@permission_required('questions.can_approve')
def send(request, pk):
    t = tasks.DocumentEmailTask(pk=pk)
    queue.add_task(t)
    messages.success(request, "The email was successfully queued to be sent!")
    return redirect('questions.views.admin')


@class_view_decorator(permission_required('questions.can_approve'))
class EmailView(FormView):
    template_name = "email.html"
    form_class = forms.EmailForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.tb = models.TeachingBlock.objects.get(number=self.kwargs['pk'], year=self.kwargs['year'])
        except models.TeachingBlock.DoesNotExist:
            messages.error(request, "That teaching block does not exist.")
            return redirect("questions.views.admin")

        r = super(EmailView, self).dispatch(request, *args, **kwargs)
        return r

    def get_context_data(self, **kwargs):
        c = super(EmailView, self).get_context_data(**kwargs)
        c.update({'tb': self.tb, 'recipients': models.Student.objects.filter(teachingactivity__block=self.tb).distinct()
})
        return c

    def get_initial(self):
        i = super(EmailView,self).get_initial()
        i.update({ 'block': self.tb, })
        if 'document' in self.request.GET:
            i.update({'email' : "Link to questions document: %s\nLink to document with answers: %s" % (
                self.request.build_absolute_uri(reverse('questions.views.download', kwargs={'pk': self.tb.pk, 'mode': 'question'})),
                self.request.build_absolute_uri(reverse('questions.views.download', kwargs={'pk': self.tb.pk, 'mode': 'answer'})),
            )})
        return i

    def form_valid(self, form):
        c = form.cleaned_data
        recipients = models.Student.objects.filter(teachingactivity__block=self.tb).distinct()
        recipients = [s.user.email for s in recipients]
        if self.request.user.email not in recipients:
            recipients.append(self.request.user.email)

        t = tasks.EmailTask(
            "[MedBank] %s" % c['subject'],
            c['email'],
            ['michaelhagarty@gmail.com',],
        )

        queue.add_task(t)

        return redirect('questions.views.admin')


def copy_block(block):
    b = models.TeachingBlock()

    b.name = block.name
    b.year = block.year
    b.stage = block.stage
    b.number = block.number
    b.start = block.start
    b.end = block.end

    return b


@login_required
def new_ta_upload(request):
    accepted_types = collections.defaultdict(None)
    if not models.TeachingBlock.objects.count():
        messages.error(request, "You can't upload teaching activities without first having created a teaching block.")
        return redirect('admin')
    for k, v in models.TeachingActivity.TYPE_CHOICES:
        accepted_types[v] = k
    if request.method == "POST":
        if 'id' in request.POST:
            y = request.POST.get('year')
            i = request.POST.getlist('id')
            r = request.POST.copy()
            blocks = dict((b.number, b) for b in models.TeachingBlock.objects.filter(year=y))
            new_blocks = request.POST.getlist('new_block')
            for bb in new_blocks:
                data = {
                    'number': bb,
                    'name': request.POST.get('new_block_%d_name' % bb),
                    'year': request.POST.get('new_block_%d_year' % bb),
                    'stage': request.POST.get('new_block_%d_stage' % bb),
                    'start': request.POST.get('new_block_%d_start' % bb),
                    'end': request.POST.get('new_block_%d_end' % bb),
                }
                f = forms.NewTeachingBlockForm(data)
                if f.is_valid():
                    bb = f.save()
                    blocks[bb.number] = bb
                else:
                    raise
            for ii in i:
                data = {
                    'id': ii,
                    'name': request.POST.get('name_%s' % ii),
                    'block': [blocks[int(request.POST.get('block_%s' % ii))].id],
                    'week': request.POST.get('week_%s' % ii),
                    'position': request.POST.get('position_%s' % ii),
                    'activity_type': request.POST.get('activity_type_%s' % ii),
                }
                f = forms.NewTeachingActivityForm(data)
                if f.is_valid():
                    f.save()
                else:
                    return redirect('activity-upload')
            return redirect('admin')
        else:
            form = forms.TeachingActivityBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                y = form.cleaned_data['year']
                r = list(csv.reader(form.cleaned_data['ta_file'].read().splitlines()))
                h = [hh.lower().replace(" ", "_") for hh in r[0]]
                by_position = {}
                by_name = {}
                by_block = {}
                already_exist = []
                blocks = list(set(dict(zip(h, row))['block'] for row in r[1:]))
                errors = []
                new_blocks = []
                existing_blocks = models.TeachingBlock.objects.filter(number__in=blocks)
                b = {}
                for bb in existing_blocks:
                    d = b.setdefault(bb.number, {})
                    d[bb.year] = bb
                for bb in blocks:
                    try:
                        bb = int(bb)
                    except:
                        errors.append("%s is not a number" % bb)
                    if bb in b:
                        if y in b[bb]:
                            bb = b[bb][y]
                        else:
                            bb = copy_block(b[bb][max(b[bb].keys())])
                            bb.year = y
                            bb.start.year = y
                            bb.end.year = y
                            b[bb.number][y] = bb
                            new_blocks.append(bb)
                        by_block[bb] = []
                    else:
                        errors.append("Block %s was not found" % bb)
                if errors:
                    return render_to_response("upload.html", {
                        'block_errors': errors
                    }, context_instance=RequestContext(request))
                for row in r[1:]:
                    hr = dict(zip(h, row))
                    hr['activity_type'] = accepted_types[hr['teaching_activity_type']]
                    f = forms.TeachingActivityValidationForm(hr)
                    if f.is_valid():
                        ta = f.save(commit=False)
                        l = by_position.setdefault((ta.week, ta.position, ta.activity_type), [])
                        l.append(ta)
                        l = by_name.setdefault(ta.name.lower(), [])
                        l.append(ta)
                        by_block[b[int(hr['block'])][y]].append(ta)
                    else:
                        if str(f.errors).find("exists"):
                            already_exist.append(hr)
                        else:
                            errors.append(hr)
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
                                'new_blocks': new_blocks,
                                'accepted_types': accepted_types.keys(),
                            },
                            context_instance=RequestContext(request)
                        )
    else:
        form = forms.TeachingActivityBulkUploadForm()
    return render_to_response(
        "upload.html",
        {
            'form': form,
            'accepted_types': accepted_types.keys(),
        },
        context_instance=RequestContext(request)
    )
