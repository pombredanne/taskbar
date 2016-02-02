# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    url(r'^task_api$', 'taskbar.views.task_api', name="task_api"),
)

if settings.DEBUG:
    urlpatterns += patterns('',
                            url(r'^celery_test$',
                                'taskbar.views.celery_test', name="celery_test"),
                            )
