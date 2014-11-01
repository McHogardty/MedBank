from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import View, DetailView, ListView, FormView
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from .base import class_view_decorator, user_is_superuser, GetObjectMixin

import document
from questions import models, forms

import datetime, csv, math


@class_view_decorator(login_required)
class AllBlocksView(ListView):
    model = models.TeachingBlockYear
    template_name = "block/list.html"

    def get_queryset(self):
        stages = self.request.user.student.get_all_stages()
        current_stage = self.request.user.student.get_current_stage()

        block_type = self.request.GET.get("type")
        if block_type == "open":
            block_years = models.TeachingBlockYear.objects.get_open_blocks_for_year_and_date_and_stages(datetime.datetime.now().year, datetime.datetime.now(), [current_stage, ])
        elif 'pending' in self.request.GET:
            block_years = models.TeachingBlockYear.objects.get_blocks_with_pending_questions_for_stages(stages)
        elif 'flagged' in self.request.GET:
            block_years = models.TeachingBlockYear.objects.get_blocks_with_flagged_questions_for_stages(stages)
        else:
            block_years = models.TeachingBlockYear.objects.get_open_blocks_for_year_and_date_and_stages(datetime.datetime.now().year, datetime.datetime.now(), stages)

        return block_years.order_by('year', 'block')

    def get_context_data(self, **kwargs):
        c = super(AllBlocksView, self).get_context_data(**kwargs)
        c.update({'flagged': 'flagged' in self.request.GET})
        return c


class OpenBlocksView(ListView):
    template_name = "block/list.html"

    def get_queryset(self):
        return models.TeachingBlockYear.objects.get_open_blocks_for_year_and_date_and_student(datetime.datetime.now().year, datetime.datetime.now(), self.request.user.student)


@class_view_decorator(login_required)
class ReleasedBlocksView(ListView):
    template_name = "block/list.html"

    def get_queryset(self):
        return models.TeachingBlockYear.objects.get_released_block_years_for_student(self.request.user.student)


@class_view_decorator(permission_required("questions.can_approve"))
class PendingBlocksForApprovalView(ListView):
    template_name = "approval/list.html"

    def get_queryset(self):
        return models.TeachingBlockYear.objects.get_blocks_requiring_approval_for_student(self.request.user.student)


@class_view_decorator(login_required)
class BlockActivitiesView(GetObjectMixin, DetailView):
    model = models.TeachingBlockYear
    template_name = "block/activities.html"

    def dispatch(self, request, *args, **kwargs):
        r = super(BlockActivitiesView, self).dispatch(request, *args, **kwargs)

        if not self.object.block.is_viewable_by(self.request.user.student):
            messages.warning(self.request, "Unfortunately, you are unable to view that block right now.")
            return redirect("dashboard")

        return r

    def get_context_data(self, **kwargs):
        c = super(BlockActivitiesView, self).get_context_data(**kwargs)
        c["teaching_block"] = self.object.block
        c["teaching_block_year"] = self.object
        c["weeks"] = self.object.get_activities_as_weeks()
        return c


@class_view_decorator(user_is_superuser)
class NewBlock(CreateView):
    model = models.TeachingBlockYear
    template_name = "block/new.html"
    form_class = forms.NewTeachingBlockYearForm

    def get_context_data(self, **kwargs):
        c = super(NewBlock, self).get_context_data(**kwargs)
        c['heading'] = "block"
        return c

    def form_valid(self, form):
        c = form.cleaned_data
        b = form.save()
        if c['sign_up_mode'] == models.TeachingBlockYear.WEEK_MODE:
            for w in range(1, c['weeks'] + 1):
                a = models.TeachingActivity()
                a.name = "Week %d" % w
                a.activity_type = models.TeachingActivity.WEEK_TYPE
                a.save()
                tay = models.TeachingActivityYear()
                tay.week = w
                tay.position = 1
                tay.block_year = b
                tay.teaching_activity = a
                tay.save()

        return redirect('admin')

    def get_success_url(self):
        return reverse('admin')


@class_view_decorator(user_is_superuser)
class EditBlock(GetObjectMixin, UpdateView):
    model = models.TeachingBlockYear
    template_name = "block/new.html"
    form_class = forms.NewTeachingBlockYearForm

    def get_context_data(self, **kwargs):
        c = super(EditBlock, self).get_context_data(**kwargs)
        c['heading'] = "block"
        return c

    def get_success_url(self):
        return self.object.get_admin_url()


@class_view_decorator(user_is_superuser)
class ReleaseBlockView(RedirectView):
    permanent = False
    def get_redirect_url(self, code, year):
        try:
            block =  models.TeachingBlockYear.objects.get_from_kwargs(**{'year':year, 'code':code})
        except models.TeachingBlockYear.DoesNotExist:
            messages.error(self.request, "That block does not exist.")
        else:
            if not block.questions_pending_count():
                if datetime.datetime.now().date() >= block.close:                
                    block.release_date = datetime.datetime.now().date()
                    block.save()
                    messages.success(self.request, "The block %s has been released to students." % (block.name, ))
                else:
                    messages.error(self.request, "Students are still able to write questions for %s. This block needs to be closed before you can release questions to students." % (block.name, ))
            else:
                messages.error(self.request, "The block %s still has questions pending, so it cannot be released to students." % (block.name, ))
        return reverse('block-admin', kwargs={'year': year, 'code': code})


@class_view_decorator(login_required)
class DownloadView(FormView):
    form_class = forms.TeachingBlockDownloadForm
    template_name = "block/download.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.teaching_block_year = models.TeachingBlockYear.objects.get_from_kwargs(**kwargs)
        except models.TeachingBlock.DoesNotExist:
            raise Http404

        self.teaching_block = self.teaching_block_year.block

        if not self.teaching_block.is_available_for_download_by(request.user.student):
            messages.warning(request, "Unfortunately you are unable to download questions for that block right now.")
            return redirect('dashboard')

        return super(DownloadView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        k = super(DownloadView, self).get_form_kwargs()
        k['teaching_block'] = self.teaching_block
        return k

    def get_context_data(self, **kwargs):
        c = super(DownloadView, self).get_context_data(**kwargs)
        c['teaching_block'] = self.teaching_block
        c['teaching_block_year'] = self.teaching_block_year
        return c

    def build_answer_table(self, data, number_of_columns=3):
        table_data = []
        number_of_rows = int(math.ceil(len(data)/float(number_of_columns)))

        for i in range(number_of_columns):
            for j, d in enumerate(data[i*number_of_rows:(i+1)*number_of_rows]):
                ll = []
                try:
                    ll = table_data[j]
                except:
                    table_data.insert(j, ll)

                ll += [unicode(j + 1 + i*number_of_rows), d.answer]

        header = []
        for i in range(number_of_columns):
            header += ["Question", "Answer"]
        table_data.insert(0, header)
        return table_data

    def form_valid(self, form):
        show_answers = form.cleaned_data['document_type'] == form.ANSWER_TYPE
        years = form.cleaned_data['years']

        questions = list(models.Question.objects.get_approved_questions_for_block_and_years(self.teaching_block, years))
        questions = sorted(questions, key=lambda x: x.unicode_body().strip()[:-1][::-1] if x.unicode_body().strip()[-1] in "?:." else x.unicode_body().strip()[::-1])

        doc = document.WordDocument()
        doc.add_heading(self.teaching_block.name)
        if show_answers:
            doc.add_heading("Answer grid")
            doc.add_table(self.build_answer_table(questions), has_heading_row=False)
            doc.insert_pagebreak(break_type='page', orientation='portrait')
            doc.add_heading("Questions and explanations")

        for question_number, question in enumerate(questions):
            doc.add_paragraph("Question %s: %s" % (question_number + 1, question.unicode_body()))
            doc.add_list(question.unicode_options_list())

            if show_answers:
                doc.add_paragraph("Answer: %s" % question.answer)
                doc.add_paragraph("The following explanations were provided:")
                doc.add_list(question.unicode_explanation_list())
                doc.add_paragraph("%s.%02d Lecture %d: %s" % (self.teaching_block.code, question.teaching_activity_year.week, question.teaching_activity_year.position, question.teaching_activity_year.name))

                p = doc.add_paragraph("To view this question online, click ")
                url = self.request.build_absolute_uri(question.get_absolute_url())
                p.add_hyperlink("here", url)

                doc.add_paragraph("")


        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        response['Content-Disposition'] = 'attachment; filename=%sQuestions%s.docx' % (self.teaching_block.filename(), "Answers" if show_answers else "")
        doc.save(response)
        return response


@class_view_decorator(user_is_superuser)
class ChangeAdminYear(FormView):
    form_class = forms.YearSelectionForm
    template_name = "block/change_year.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.teaching_block = models.TeachingBlock.objects.get_from_kwargs(**kwargs)
        except models.TeachingBlock.DoesNotExist:
            raise Http404

        return super(ChangeAdminYear, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ChangeAdminYear, self).get_form_kwargs()
        kwargs['teaching_block'] = self.teaching_block
        return kwargs

    def get_context_data(self, **kwargs):
        c = super(ChangeAdminYear, self).get_context_data(**kwargs)
        c['teaching_block'] = self.teaching_block
        return c

    def form_valid(self, form):
        return redirect(form.cleaned_data['year'].get_admin_url())


@class_view_decorator(user_is_superuser)
class StartUploadForTeachingBlock(FormView):
    form_class = forms.TeachingBlockActivityUploadForm
    template_name = "block/upload_activities.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.teaching_block_year = models.TeachingBlockYear.objects.get_from_kwargs(**kwargs)
        except models.TeachingBlockYear.DoesNotExist:
            raise Http404

        r = super(StartUploadForTeachingBlock, self).dispatch(request, *args, **kwargs)

        return r

    def get_context_data(self, **kwargs):
        c = super(StartUploadForTeachingBlock, self).get_context_data(**kwargs)
        c['teaching_block_year'] = self.teaching_block_year
        c['accepted_types'] = models.TeachingActivity.accepted_types().keys()
        c['form_submit_url'] = self.teaching_block_year.get_activity_upload_submit_url()
        return c


@class_view_decorator(user_is_superuser)
class UploadForTeachingBlock(FormView):
    form_class = forms.TeachingBlockActivityUploadForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.teaching_block_year = models.TeachingBlockYear.objects.get_from_kwargs(**kwargs)
        except models.TeachingBlockYear.DoesNotExist:
            raise Http404

        return super(UploadForTeachingBlock, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        c = super(UploadForTeachingBlock, self).get_context_data(**kwargs)
        c['teaching_block_year'] = self.teaching_block_year
        c['new_activity_years'] = self.new_activity_years
        c['errors'] = self.errors
        return c

    def get_template_names(self):
        if any(self.errors.values()):
            return "block/upload_errors.html"

        return "block/upload_activities_confirm.html"

    def form_valid(self, form):
        upload_file = form.cleaned_data['upload_file']

        rows = list(csv.reader(upload_file.read().splitlines()))
        column_titles = [title.lower().replace(" ", "_") for title in rows[0]]
        content_rows = rows[1:]

        # Keeps track of errors so that we can present all of them at once instead of
        # presenting them individually.
        self.errors = {}
        bad_activity_types = self.errors.setdefault('bad_activity_type', [])
        bad_reference_id = self.errors.setdefault('bad_reference_id', [])
        bad_teaching_activity = self.errors.setdefault('bad_teaching_activity', [])
        bad_activity_year = self.errors.setdefault("bad_activity_year", [])
        duplicated_by_position = self.errors.setdefault("duplicated_by_position", [])
        duplicated_by_name = self.errors.setdefault("duplicated_by_name", [])

        # Create a mapping from reference ID to teaching activity so that we can identify
        # teaching activities which already exist.
        existing_teaching_activities = models.TeachingActivity.objects.filter(years__block_year__block=self.teaching_block_year.block)
        existing_teaching_activities_by_referenceID = dict((activity.reference_id, activity) for activity in existing_teaching_activities)
        # Lists for the new teaching activity years.
        self.new_activity_years = {}
        new_activity_years_old_activity = self.new_activity_years.setdefault('old_activity', [])
        new_activity_years_new_activity = self.new_activity_years.setdefault('new_activity', [])

        # Mappings to check for duplicated activity years.
        new_activity_years_by_position = {}
        new_activity_years_by_name = {}

        for title, pretty_name in {'reference_id': "Reference ID", 'name': "Name", 'activity_type': "Activity type", 'week': "Week", 'position': "Position"}.items():
            if title not in column_titles:
                messages.error(self.request, 'That CSV file does not contain a column named "%s". Please try again.' % pretty_name)
                return redirect(self.teaching_block_year.get_activity_upload_url())

        for row in content_rows:
            # Creates a mapping from column heading to row value for that particular column.
            column_to_value = dict(zip(column_titles, row))
            # This will be the data we pass to the validation form.
            data = {}

            activity_type = column_to_value['activity_type']
            try:
                activity_type = models.TeachingActivity.get_type_value_from_name(activity_type)
            except ValueError:
                bad_activity_types.append(column_to_value)
                continue

            referenceID = column_to_value['reference_id']
            try:
                referenceID = int(referenceID)
            except ValueError:
                bad_reference_id.append(column_to_value)
                continue

            if referenceID in existing_teaching_activities_by_referenceID:
                activity = existing_teaching_activities_by_referenceID[referenceID]
                new_activity_year_list = new_activity_years_old_activity
            else:
                data = {
                    'activity_type': activity_type,
                    'reference_id': referenceID,
                    'name': column_to_value['name']
                }
                activity_form = forms.TeachingActivityValidationForm(data)
                if activity_form.is_valid():
                    activity = activity_form.save(commit=False)
                    new_activity_year_list = new_activity_years_new_activity
                else:
                    bad_teaching_activity.append(column_to_value)
                    continue

            data = {
                'week': column_to_value['week'],
                'position': column_to_value['position'],
            }

            activity_year_form = forms.TeachingActivityYearValidationForm(data)
            if activity_year_form.is_valid():
                activity_year = activity_year_form.save(commit=False)
                activity_year.teaching_activity = activity

                # Keeps track to check that there are no two activities with the same position.
                activity_year_position = (activity_year.week, activity_year.position, activity.activity_type)
                activities_with_same_position = new_activity_years_by_position.setdefault(activity_year_position, [])
                activities_with_same_position.append(activity_year)

                # Keeps track to check that we haven't made a mistake and there are no two activities with the same name.
                activities_with_same_name = new_activity_years_by_name.setdefault(activity.name.lower(), [])
                activities_with_same_name.append(activity_year)

                new_activity_year_list.append(activity_year)
            else:
                bad_activity_year.append(column_to_value)

        for activities_with_same_position in new_activity_years_by_position.values():
            if len(activities_with_same_position) > 1:
                duplicated_by_position += activities_with_same_position

        for activities_with_same_name in new_activity_years_by_name.values():
            if len(activities_with_same_name) > 1:
                duplicated_by_name += activities_with_same_name

        for activity_list in self.new_activity_years.values():
            activity_list.sort(key=lambda a: (a.week, a.position))

        return self.get(self.request)


@class_view_decorator(user_is_superuser)
class ConfirmUploadForTeachingBlock(View):
    def post(self, request, *args, **kwargs):
        post = request.POST
        try:
            self.teaching_block_year = models.TeachingBlockYear.objects.get_from_kwargs(**kwargs)
        except models.TeachingBlockYear.DoesNotExist:
            raise Http404

        existing_teaching_activities = models.TeachingActivity.objects.filter(years__block_year__block=self.teaching_block_year.block)
        existing_teaching_activities_by_referenceID = dict((activity.reference_id, activity) for activity in existing_teaching_activities)

        every_referenceID = post.getlist('reference_id')

        for referenceID in every_referenceID:
            try:
                referenceID = int(referenceID)
            except ValueError:
                messages.error(request, "An unexpected error has occurred.")
                return redirect(self.teaching_block_year.get_activity_upload_url())

            # Build up the data required to create a teaching activity.
            if referenceID in existing_teaching_activities_by_referenceID:
                activity = existing_teaching_activities_by_referenceID[referenceID]
            else:
                data = {
                    'reference_id': referenceID,
                    'name': post.get("name_%s" % referenceID),
                    'activity_type': post.get("activity_type_%s" % referenceID),
                }
                activity_form = forms.NewTeachingActivityForm(data)
                if activity_form.is_valid():
                    activity = activity_form.save(commit=False)
                else:
                    messages.error(request, "An unexpected error has occurred.")
                    return redirect(self.teaching_block_year.get_activity_upload_url())

            # Now build up data to create a teaching activity year.
            data = {
                'block_year': self.teaching_block_year.id,
                'week': post.get('week_%s' % referenceID),
                'position': post.get('position_%s' % referenceID),
            }

            activity_year_form = forms.NewTeachingActivityYearForm(data)
            if activity_year_form.is_valid():
                activity_year = activity_year_form.save(commit=False)
                activity.save()
                activity_year.teaching_activity = activity
                activity_year.save()
            else:
                messages.error(request, "An unexpected error has occurred.")
                return redirect(self.teaching_block_year.get_activity_upload_url())

        return redirect(self.teaching_block_year.get_admin_url())
