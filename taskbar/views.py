# -*- coding: utf-8 -*-
import json
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.db import IntegrityError
from functools import wraps    # deals with decorats shpinx documentation

from taskbar import tasks
from taskbar.models import CeleryTasks
from taskbar.utils import decorator_with_args

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@decorator_with_args
def progressbarit(fn, task_key="", only_staff=True):
    @wraps(fn)
    def wrapped(*args, **kwargs):

        request = args[0]

        if only_staff:
            if not request.user.is_staff:
                raise PermissionDenied

        elif not request.user.is_active:
            raise PermissionDenied

        if task_key and CeleryTasks.objects.filter(key=task_key, status__in=["waiting", "active"]):

            json_data = json.dumps("Error: %s Task is already running" % task_key)
            return HttpResponse(json_data, content_type='application/json')

        try:
            task_id = fn(*args, **kwargs)
        except:
            json_data = json.dumps("Error: %s Task failed to run" % task_key)
            return HttpResponse(json_data, content_type='application/json')

        try:
            CeleryTasks.objects.create(task_id=task_id, user=request.user, key=task_key)
        except IntegrityError:
            # We don't want to have 2 tasks with the same ID
            logger.critical("There ware 2 tasks with the same ID. Trying to terminate the task.", exc_info=True)
            from celery.task.control import revoke
            revoke(task_id, terminate=True)
            raise

        json_data = json.dumps(task_id)

        return HttpResponse(json_data, content_type='application/json')

    return wrapped


def task_api(request):
    """ A view to report the progress to the user """

    if not request.user.is_active:
        raise PermissionDenied

    if request.method == "GET":
        task_id = request.GET.get('id', False)
        terminate = request.GET.get('terminate', False)
        msg_index_client = request.GET.get('msg_index_client', False)
    elif request.method == "POST":
        task_id = request.POST.get('id', False)
        terminate = request.POST.get('terminate', False)
        msg_index_client = request.POST.get('msg_index_client', False)
    else:
        task_id = False
        terminate = False
        msg_index_client = False

    if task_id:
        task_key = "celery-stat-%s" % task_id
        task_stat = cache.get(task_key)
        try:
            if task_stat['user_id'] != request.user.id:
                return HttpResponse('Unauthorized', status=401)
        except TypeError:
            return HttpResponse('Unauthorized', status=401)

        else:
            # logger.info("msg_index_client: %s   task_stat['msg_index']: %s" % (msg_index_client, task_stat['msg_index']))
            try:
                msg_index_client = int(msg_index_client)
            except:
                task_stat['msg_chunk'] = "Error in pointer index server call"
            else:
                if msg_index_client is not False and msg_index_client < task_stat['msg_index']:
                    whole_msg = cache.get("celery-%s-msg-all" % task_id)
                    task_stat['msg_chunk'] = whole_msg[msg_index_client:]
    else:
        task_stat = None

    if task_stat and terminate == "1":
        cache.set("celery-kill-%s" % task_id, True, 60 * 5)

    return HttpResponse(json.dumps(task_stat), content_type='application/json')


@progressbarit(only_staff=False)
def celery_test(request):
    """ Tests celery and celery progress bar """

    # you need to always specify user_id with kwargs and NOT args

    job = tasks.test_progressbar.delay(user_id=request.user.id)

    return job.id


@decorator_with_args
def logined_json(fn, only_staff=True):
    @wraps(fn)
    def wrapped(*args, **kwargs):

        request = args[0]

        if only_staff:
            if not request.user.is_staff:
                raise PermissionDenied

        elif not request.user.is_active:
            raise PermissionDenied

        data = fn(*args, **kwargs)

        json_data = json.dumps(data)

        return HttpResponse(json_data, content_type='application/json')

    return wrapped
