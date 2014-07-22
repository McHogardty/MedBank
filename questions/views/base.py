from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test


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
