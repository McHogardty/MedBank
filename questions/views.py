from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.conf import settings


import forms
import models

import csv
import json
import datetime
import docx
from lxml import etree
import zipfile
import os
import cStringIO as StringIO


@login_required
def home(request):
    if request.user.has_perm('questions.can_approve'):
        return redirect('questions.views.admin')
    ta_sorted = {}
    max_position = None
    columns = []
    try:
        tb = models.TeachingBlock.objects.filter(start__lte=datetime.datetime.now().date).latest("start")
    except models.TeachingBlock.DoesNotExist:
        tb = None
    else:
        ta = models.TeachingActivity.objects.filter(block=tb)

        if ta:
            for t in ta:
                l = ta_sorted.setdefault(t.week, [])
                l.append(t)

            max_position = max(len(l) for l in ta_sorted.values())

            for k in ta_sorted:
                ta_sorted[k].sort(key=lambda t: t.position)
                diff = max_position - len(ta_sorted[k])
                ta_sorted[k] += ([""] * diff)

            columns = range(1, max_position + 1)

    return render_to_response(
        "all.html",
        {
            'activities': ta_sorted,
            'max_position': max_position,
            'columns': columns,
            'teaching_block': tb,
        },
        context_instance=RequestContext(request)
    )


@permission_required('questions.can_approve')
def admin(request):
    return render_to_response('admin.html', context_instance=RequestContext(request))


@login_required
def new(request, ta_id, q_id=None):
    try:
        ta = models.TeachingActivity.objects.get(id=ta_id)
    except models.TeachingActivity.DoesNotExist:
        messages.error(request, "Hmm... that teaching activity could not be found.")
        return redirect('questions.views.home')

    initial = {'teaching_activity': ta, 'creator': request.user}

    if q_id:
        try:
            q = models.Question.objects.get(id=q_id)
        except models.Question.DoesNotExist:
            messages.error(request, "Hmm... that question could not be found.")

    if request.method == "POST":
        if ta.id != int(request.POST.get('teaching_activity')):
            return redirect('questions.views.new', ta_id=int(ta_id))
        if q_id:
            form = forms.NewQuestionForm(request.POST, instance=q)
        else:
            form = forms.NewQuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.creator = request.user
            q.save()

            return redirect('questions.views.view_ta', ta_id=ta_id)
    else:
        if q_id:
            form = forms.NewQuestionForm(initial=initial, instance=q)
        else:
            form = forms.NewQuestionForm(initial=initial)

    return render_to_response("new.html", {'form': form, }, context_instance=RequestContext(request))


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
                'view_url': reverse('questions.views.view_ta', kwargs={'ta_id': int(ta_id)})
            }),
            mimetype="application/json"
        )
    else:
        return redirect("questions.views.view_ta", ta_id=ta_id)


@login_required
def new_ta(request):
    if request.method == "POST":
        form = forms.NewTeachingActivityForm(request.POST)
        if form.is_valid():
            pass
    else:
        form = forms.NewTeachingActivityForm()

    return render_to_response("new_ta.html", {'form': form, }, context_instance=RequestContext(request))


@login_required
def view_ta(request, ta_id):
    try:
        ta = models.TeachingActivity.objects.get(id=ta_id)
    except models.TeachingActivity.DoesNotExist:
        messages.error(request, "That teaching activity could not be found.")
        return redirect("questions.views.home")

    return render_to_response("view_ta.html", {'t': ta, 'max_questions': settings.QUESTIONS_PER_USER}, context_instance=RequestContext(request))


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
    return redirect('questions.views.view', q_id=q_id, ta_id=q.teaching_activity.id)


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

    return redirect('questions.views.view', q_id=q_id, ta_id=q.teaching_activity.id)


@login_required
def download(request):
    tb = models.TeachingBlock.objects.filter(start__lte=datetime.datetime.now().date).latest("start")
    document = docx.newdocument()
    body = document.xpath('/w:document/w:body', namespaces=docx.nsprefixes)[0]

    body.append(docx.heading("%s - Questions" % (tb), 1))
    qq = models.Question.objects.filter(teaching_activity__block=tb)
    style_file = os.path.join(docx.template_dir, 'word/stylesBase.xml')
    style_tree = etree.parse(style_file)
    style_outfile = open(os.path.join(docx.template_dir, 'word/styles.xml'), 'w')
    numbering_file = os.path.join(docx.template_dir, 'word/numberingBase.xml')
    numbering_tree = etree.parse(numbering_file)
    numbering_outfile = open(os.path.join(docx.template_dir, 'word/numbering.xml'), 'w')

    namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xhtml_namespace = "{%s}" % namespace

    s = style_tree.getroot()
    nt = numbering_tree.getroot()

    for n, q in enumerate(qq):
        style_name = 'ListUpperLetter%d' % n
        numid = 14 + n
        abstract_numid = 12 + n

        body.append(docx.paragraph(q.body))
        [body.append(docx.paragraph(o, style=style_name)) for o in q.options_list()]

    for n in range(len(qq)):
        abstract_numid = 12 + n
        # Add an abstractNum element to the numbering.xml file
        a = etree.SubElement(nt, "%sabstractNum" % xhtml_namespace)
        a.attrib["%sabstractNumId" % xhtml_namespace] = str(abstract_numid)
        b = etree.SubElement(a, "%slvl" % xhtml_namespace)
        b.attrib['%silvl' % xhtml_namespace] = "0"
        c = etree.SubElement(b, "%sstart" % xhtml_namespace)
        c.attrib["%sval" % xhtml_namespace] = "1"
        c = etree.SubElement(b, "%snumFmt" % xhtml_namespace)
        c.attrib["%sval" % xhtml_namespace] = "upperLetter"
        c = etree.SubElement(b, "%slvlText" % xhtml_namespace)
        c.attrib["%sval" % xhtml_namespace] = "%1."
        c = etree.SubElement(b, "%slvlJc" % xhtml_namespace)
        c.attrib["%sval" % xhtml_namespace] = "left"
        c = etree.SubElement(b, "%spPr" % xhtml_namespace)
        d = etree.SubElement(c, "%stabs" % xhtml_namespace)
        e = etree.SubElement(d, "%stab" % xhtml_namespace)
        e.attrib["%sval" % xhtml_namespace] = "num"
        e.attrib["%spos" % xhtml_namespace] = "360"
        f = etree.SubElement(c, "%sind" % xhtml_namespace)
        f.attrib["%sleft" % xhtml_namespace] = "360"
        f.attrib["%shanging" % xhtml_namespace] = "360"

    for n in range(len(qq)):
        numid = 14 + n
        abstract_numid = 12 + n        # Add a num element to the numbering.xml file
        a = etree.SubElement(nt, "%snum" % xhtml_namespace)
        a.attrib["%snumId" % xhtml_namespace] = str(numid)
        b = etree.SubElement(a, "%sabstractNumId" % xhtml_namespace)
        b.attrib["%sval" % xhtml_namespace] = str(abstract_numid)

    for n in range(len(qq)):
        style_name = 'ListUpperLetter%d' % n
        numid = 14 + n
        # Add a style element to the style.xml file
        a = etree.SubElement(s, "%sstyle" % xhtml_namespace)
        a.attrib['%sstyleId' % xhtml_namespace] = style_name
        a.attrib['%stype' % xhtml_namespace] = "paragraph"
        b = etree.SubElement(a, "%spPr" % xhtml_namespace)
        c = etree.SubElement(b, "%snumPr" % xhtml_namespace)
        d = etree.SubElement(c, "%snumId" % xhtml_namespace)
        d.attrib['%sval' % xhtml_namespace] = str(numid)
        etree.SubElement(b, "%scontextualSpacing" % xhtml_namespace)

    style_tree.write(style_outfile)
    numbering_tree.write(numbering_outfile)
    style_outfile.close()
    numbering_outfile.close()

    title = 'Questions'
    subject = 'A set of peer-reviewed MCQ questions for this block.'
    creator = 'Michael Hagarty'
    coreprops = docx.coreproperties(title=title, subject=subject, creator=creator, keywords=[])
    appprops = docx.appproperties()
    contenttypes = docx.contenttypes()
    websettings = docx.websettings()
    relationships = docx.relationshiplist()
    wordrelationships = docx.wordrelationships(relationships)
    docx.savedocx(document, coreprops, appprops, contenttypes, websettings, wordrelationships, 'hello.docx')

    f = StringIO.StringIO()
    docxfile = zipfile.ZipFile(f, mode='w', compression=zipfile.ZIP_DEFLATED)
    treesandfiles = {
        document: 'word/document.xml',
        coreprops: 'docProps/core.xml',
        appprops: 'docProps/app.xml',
        contenttypes: '[Content_Types].xml',
        websettings: 'word/webSettings.xml',
        wordrelationships: 'word/_rels/document.xml.rels'
    }
    for tree in treesandfiles:
        treestring = etree.tostring(tree, pretty_print=True)
        docxfile.writestr(treesandfiles[tree], treestring)

    files_to_ignore = ['.DS_Store', 'stylesBase.xml', 'numberingBase.xml']
    for dirpath, dirnames, filenames in os.walk(docx.template_dir):
        for filename in filenames:
            if filename in files_to_ignore:
                continue
            templatefile = os.path.join(dirpath, filename)
            archivename = templatefile.replace(docx.template_dir, '')[1:]
            docxfile.write(templatefile, archivename)

    docxfile.close()
    r = HttpResponse(f.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    r['Content-Disposition'] = 'attachment; filename=questions.docx'
    f.close()
    return r


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
