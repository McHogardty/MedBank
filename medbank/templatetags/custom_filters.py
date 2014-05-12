from django import template

from collections import defaultdict

register = template.Library()


@register.filter
def subtract(value, arg):
    """Subtracts the arg from the value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        try:
            return value - arg
        except Exception:
            return ''


@register.filter
def humanize_list(value):
    if len(value) == 0:
        return ""
    elif len(value) == 1:
        return value[0]

    s = ", ".join(value[:-1])

    if len(value) > 3:
        s += ","

    return "%s and %s" % (s, value[-1])


@register.assignment_tag
def questions_left(user, activity):
    return activity.questions_left_for(user.student)

@register.assignment_tag
def questions_list_by_year(user, activity):
    qq = activity.questions_for(user)
    ret = defaultdict(list)
    for q in qq:
        ret[q.date_created.year].append(q)
    return dict(ret)

@register.filter
def range(value):
    return __builtins__.get('range')(value)