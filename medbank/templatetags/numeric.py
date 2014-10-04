from __future__ import unicode_literals

from django import template

register = template.Library()

@register.filter
def minimum(value):
	return min(value)


@register.filter
def maximum(value):
	return max(value)