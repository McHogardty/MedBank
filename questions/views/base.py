from __future__ import unicode_literals

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.http import Http404
from django.http import HttpResponse, Http404
from django.db import transaction

import reversion

import json


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

def user_is_superuser(func):
	decorator = user_passes_test(lambda u: u.is_superuser)
	return decorator(func)


def track_changes(func):
    print "Got here."
    @transaction.atomic()
    @reversion.create_revision()
    def _dec(request, *args, **kwargs):
        if request.user and request.user.is_authenticated():
            reversion.set_user(request.user)
        return func(request, *args, **kwargs)

    _dec.__name__ = func.__name__
    _dec.__doc__ = func.__doc__

    return _dec

class GetObjectMixin(object):
    def get_object(self, queryset=None):
        if not self.model:
            raise ImproperlyConfigured("%(cls)s is missing a model. Define "
                                       "%(cls)s.model or override "
                                       "%(cls)s.get_object()." % {
                                            'cls': self.__class__.__name__
                                    })


        try:
            return self.model.objects.get_from_kwargs(**self.kwargs)
        except ObjectDoesNotExist:
            raise Http404


class JsonResponseMixin(object):
    def render_to_json_response(self, data, **response_kwargs):
        return HttpResponse(json.dumps(data), content_type="application/json", **response_kwargs)
