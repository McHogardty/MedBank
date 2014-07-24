from django import template
import inflect

from collections import defaultdict

PLURAL_ENGINE = inflect.engine()
register = template.Library()


@register.filter
def plural(value, arg):
    # Finds the plural of the arg based on the value of value.
    try:
        value = int(value)
    except ValueError:
        return arg

    arg = arg.split()
    plural_phrase = []
    for word in arg:
        plural_phrase.append(PLURAL_ENGINE.plural(word, value))

    return " ".join(plural_phrase)

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

    value = [str(x) for x in value]

    s = ", ".join(value[:-1])

    if len(value) > 3:
        s += ","

    return "%s and %s" % (s, value[-1])


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
