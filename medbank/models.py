from __future__ import unicode_literals

from django.db import models


class SettingsManager(models.Manager):
    def get_queryset(self):
    	qs = super(SettingsManager, self).get_queryset()
    	if self.model.__name__ == "Setting":
    		return qs

        return qs.filter(class_name=self.model.__name__)


class Setting(models.Model):
	class_name = models.CharField(max_length=100, editable=False)
	name = models.CharField(max_length=100, editable=False)
	verbose_name = models.CharField(max_length=100)
	description = models.TextField(null=True, blank=True)
	value = models.TextField(null=True, blank=True)
	last_modified_by = models.ForeignKey('questions.Student', related_name="modified_settings", editable=False)
	last_modified_date = models.DateTimeField(auto_now=True)

	objects = SettingsManager()

	def __init__(self, *args, **kwargs):
		super(Setting, self).__init__(*args, **kwargs)
		if not self.id:
			self.class_name = self.__class__.__name__

	def save(self, *args, **kwargs):
		if not self.id and not self.verbose_name:
			self.verbose_name = " ".join(self.name.split("_")).capitalize()

		return super(Setting, self).save(*args, **kwargs)

	def __unicode__(self):
		return "%s.%s" % (self.class_name, self.name)

	class Meta:
		unique_together = ['class_name', 'name']


