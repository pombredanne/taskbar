# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User
from taskbar.utils import datetime_difference

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CeleryTasks(models.Model):

    """
    Keeps track of celery Tasks
    """
    # objects = GenericManager()

    task_id = models.CharField(
        'task id', max_length=50, unique=True, db_index=True)
    status = models.CharField(
        'state', max_length=40, default="waiting", db_index=True)
    creation_date = models.DateTimeField('Creation Date', auto_now_add=True)
    start_date = models.DateTimeField('Start Date', null=True)
    end_date = models.DateTimeField('End Date', default=None, null=True)
    user = models.ForeignKey(User, related_name="tasks_of_user")
    key = models.CharField(
        "Task Blocking Key", max_length=50, db_index=True, default="", blank=True)

    @property
    def duration(self):
        if self.end_date:
            try:
                duration = datetime_difference(self.start_date, self.end_date)
            except:
                duration = "Err"
        else:
            duration = "Not finished"

        return duration

    class Meta:
        verbose_name_plural = 'Tasks History'
        verbose_name = 'Task History'

    def __unicode__(self):
        return "%s: %s" % (self.task_id, self.status)
