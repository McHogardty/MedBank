import models

from lxml import etree
import os
import docx
import cStringIO as StringIO
import zipfile


def generate_document(tb, answer):
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

        body.append(docx.paragraph("Question %d: %s" % (n+1, q.body)))
        [body.append(docx.paragraph(o, style=style_name)) for o in q.options_list()]

        if answer:
            body.append(docx.paragraph("Answer: %s" % q.answer))
            body.append(docx.paragraph(q.explanation))
            body.append(docx.paragraph("%s.%02d Lecture %d: %s" % (q.teaching_activity.block.number, q.teaching_activity.week, q.teaching_activity.position, q.teaching_activity.name)))
            body.append(docx.paragraph(""))

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
    return f
