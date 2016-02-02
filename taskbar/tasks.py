# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from time import sleep
import re
from taskbar.models import CeleryTasks

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


LOG_MSG_MAX_LENGTH = getattr(settings, 'LOG_MSG_MAX_LENGTH', None)

# Trying to load celery
try:
    from celery import shared_task, current_task
except ImportError:
    def shared_task(*args, **kwargs):
        return None

    def current_task(*args, **kwargs):
        return None


class celery_progressbar_stat(object):

    """ updates the progress bar info for the task.

        Example usage:
        from celery import current_task
        from taskbar.tasks import celery_progressbar_stat

        c = celery_progressbar_stat(current_task, user_id)
        c.percent=10

        c.msg="FINISHED"

        This will automatically update the progressbar msg.

        During setting percentage and during reporting, we check to see if is_killed flag is set in the cache.
        In that case, we terminate the task.
    """

    def __init__(self, task, user_id, cache_time=3000):
        self.task_id = task.request.id
        # user is used by other code that deal with celery progress bar
        self.user = User.objects.get(id=user_id)
        self.task_stat_id = "celery-stat-%s" % self.task_id
        self.task_kill_id = "celery-kill-%s" % self.task_id
        self.task_msg_all_id = "celery-%s-msg-all" % self.task_id
        self.cache_time = cache_time
        self.result = {'msg': "IN PROGRESS", 'sticky_msg': '', 'progress_percent': 0, 'is_killed': False,
                       'user_id': user_id, 'msg_index': 0, }
        self.last_err = ""
        self.last_err_type = None
        self.fatal = False

        self.msg = ""
        cache.set(self.task_msg_all_id, "", self.cache_time)

        # Normally we want to have created the CeleryTasks object before even the task is run. Reason: if the task is in the queue, we want to know that.
        # In that case these lines are not even run yet! However, we need some delay here before the task is created and the CeleryTasks object created
        # so we can get the object. Otherwise it can't "get" the object and it
        # thinks it doesn't exist

        for j in range(1, 10):
            sleep(.3)
            try:
                self.celery_task_history_obj = CeleryTasks.objects.get(
                    task_id=self.task_id)
                break
            except CeleryTasks.DoesNotExist:
                pass

        if j >= 9:
            raise Exception("Could not get the celery_task_history_obj")

        self.celery_task_history_obj.status = "active"
        self.celery_task_history_obj.start_date = timezone.now()
        self.celery_task_history_obj.save(
            update_fields=["status", "start_date"])
        now = timezone.now()
        try:
            CeleryTasks.objects.filter(creation_date__lte=now - timezone.timedelta(hours=24),
                                       status__in=["active", "waiting"]).update(status="must have failed")
            CeleryTasks.objects.filter(
                creation_date__lte=now - timezone.timedelta(hours=600)).delete()
        except:
            logger.error(
                "Error in cleaning up CeleryTasks History", exc_info=True)

    def __enter__(self):
        return self

    def __exit__(self, exit_type, exit_value, traceback):

        if exit_type == SystemExit:
            self.celery_task_history_obj.status = "killed"
            # killed by error but we still set is_killed to true
            self.is_killed = True
            self.sticky_msg = "%s [Task Terminated]" % self.msg
            logger.error("Task terminated and killed by user or POSSIBLE error: %s, message: %s" % (
                self.last_err, self.msg), exc_info=True)

        elif exit_type:
            self.celery_task_history_obj.status = "error"
            self.sticky_msg = "%s [Task Terminated]" % self.msg
            # killed by error but we still set is_killed to true
            self.is_killed = True
            logger.error("Task terminated in error: %s, message: %s" %
                         (self.last_err, self.msg), exc_info=True)
        else:
            self.celery_task_history_obj.status = "finished"

        self.celery_task_history_obj.end_date = timezone.now()
        self.celery_task_history_obj.save(update_fields=["status", "end_date"])

        # The cache to remain for another minute
        cache.replace(self.task_stat_id, self.result, time=60)
        cache.replace(self.task_msg_all_id, "", time=60)

        # exit should return True once done
        return True

    def get_percent(self):
        return self.result["progress_percent"]

    def set_percent(self, val):
        if self.kill:
            raise SystemExit

        self.result["progress_percent"] = val
        self.set_cache()

    def get_msg(self):
        return self.result["msg"]

    def set_msg(self, val):
        self.result["msg"] = val
        self.set_cache()

    def get_err(self):
        return self.last_err

    def set_err(self, val):
        self.last_err = val
        val = "<hr class='line-seperator'><p>%s</p>" % val
        self.result["msg_index"] += len(val)
        self.set_cache()
        cache.append(self.task_msg_all_id, val)

    def get_sticky_msg(self):
        return self.result["sticky_msg"]

    def set_sticky_msg(self, val):
        self.result["sticky_msg"] = val
        self.set_cache()

    def get_is_killed(self):
        return self.result["is_killed"]

    def set_is_killed(self, val):
        self.result["is_killed"] = val
        self.set_cache()

    def get_kill(self):
        return cache.get(self.task_kill_id)

    # def set_kill(self, val):
    #     cache.set(self.task_kill_id, True, 60 * 5)

    def set_cache(self):
        cache.set(self.task_stat_id, self.result, time=self.cache_time)

    def report(self, msg, e=None, obj=None, field=None, fatal=False, sticky_msg="", log_level="info"):
        # msg is what the user sees. e is the actual error that was raised.
        # We check to see if an error is not already caught. Since we don't want to re-raise the same error up.
        # However you have to raise the error yourself in your code. e is
        # basically Exception as e

        if sticky_msg:
            self.sticky_msg = sticky_msg

        if fatal or self.kill:
            self.msg = msg
            self.last_err = e.message
            raise SystemExit

        # This is to avoid raising the same error again as we raise exception
        # and catching and re-raising it
        if e == self.last_err_type:
            return "The error was just raised"
        else:
            self.last_err_type = e

        self.msg = msg

        if obj and field:
            current_err_fields = getattr(obj, "err_fields")
            field += " "

            if field not in current_err_fields:
                current_err_fields = "%s %s" % (field, current_err_fields)

                try:
                    setattr(obj, "err_fields", current_err_fields)
                    setattr(obj, "is_fine", False)
                    if LOG_MSG_MAX_LENGTH:
                        setattr(obj, "err_msg", msg[:LOG_MSG_MAX_LENGTH])
                    else:
                        setattr(obj, "err_msg", msg)

                    obj.save(
                        update_fields=["err_fields", "is_fine", "err_msg", ])
                except:
                    self.msg = "Unable to set object's error fields. The model is not properly set up."

        if msg[:3].lower() == "err" or msg[:3].lower() == "war":
            self.err = msg

        log_level = log_level.lower()
        getattr(logger, log_level)(
            "taskbar_raiseerr msg: %s, e: %s" % (msg, e))

    def clean_err(self, obj, field, save=True):
        """
        Cleans the error fields on the object
        """
        current_err_fields = getattr(obj, "err_fields")

        if field == "all":
            current_err_fields = ""
        else:
            field += " "
            current_err_fields = current_err_fields.replace(field, "")

        try:
            setattr(obj, "err_fields", current_err_fields)
            setattr(obj, "err_msg", "")
            # It will only remove the is_fine flag if there is no error field
            # left
            if not current_err_fields:
                setattr(obj, "is_fine", True)

            if save:
                obj.save(update_fields=["err_fields", "is_fine", "err_msg", ])
                msg = "obj err fields cleanup and saving obj %s" % obj.pk
                logger.info(msg)
                print(msg)
            else:
                msg = "obj err fields cleanup but NOT saving obj %s" % obj.pk
                logger.info(msg)
                print(msg)

        except:
            self.msg = "Unable to set object's error fields. The model is not properly set up."
            logger.error(self.msg)
            print(self.msg)

    percent = property(get_percent, set_percent,)
    msg = property(get_msg, set_msg,)
    err = property(get_err, set_err,)
    sticky_msg = property(get_sticky_msg, set_sticky_msg,)
    is_killed = property(get_is_killed, set_is_killed,)
    kill = property(get_kill, )


class celery_progressbar_stat_dummy(celery_progressbar_stat):

    """ does not update the progress bar info for the task.
        it is used when testing the task from the command line
    """

    IGNORE_EXCEPTIONS = re.compile('ignore this|ignore that', re.I)

    def __init__(self, task, user_id, cache_time=200):
        self.result = {'msg': "IN PROGRESS", 'sticky_msg': '', 'progress_percent': 0, 'is_killed': False,
                       'user_id': user_id, 'msg_index': 0, }
        self.user = User.objects.get(id=user_id)
        self.last_err = ""
        self.task_id = "test id"
        self.task_msg_all_id = "celery-%s-msg-all" % self.task_id
        self.task_kill_id = "celery-kill-%s" % self.task_id
        self.task_stat_id = "celery-stat-%s" % self.task_id
        self.last_err_type = None
        self.fatal = False

    def __enter__(self):
        return self

    def __exit__(self, exit_type, exit_value, traceback):
        pass

    def set_cache(self):
        pass

    def report(self, msg, e=None, obj=None, field=None, fatal=False, sticky_msg="", log_level="info"):
        import sys
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()

        print("Latest exception:")
        traceback.print_exception(
            exc_type, exc_value, exc_traceback, limit=5, file=sys.stdout)

        print('\nCelery Task raised message:%s' % msg)

        if not self.IGNORE_EXCEPTIONS.search(msg):
            import ipdb
            ipdb.set_trace()


@shared_task
def test_progressbar(user_id=1):
    from time import sleep
    from django.utils.safestring import mark_safe

    with celery_progressbar_stat(current_task, user_id) as c_stat:
        c_stat.msg = "Tesing"

        for i in range(0, 101):

            if c_stat.is_killed:
                c_stat.report("Terminating task", e="test_err3", fatal=True)

            sleep(.3)
            if i == 6:
                logger.info("test progress bar at 6%")
                c_stat.report("Error: This error should show up", e="test_err",
                              sticky_msg=mark_safe("<p>TEST STICKY ERROR.</p><img src='https://cdn0.iconfinder.com/data/icons/cosmo-medicine/40/test-tube_2-128.png'>"))

            if i == 16:
                logger.info("test progress bar at 16%")
                c_stat.report(
                    "Error again: This error should show up too", e="test_err2")

            if i == 22:
                logger.info("test progress bar at 22%")
                c_stat.report(
                    "Error: This error should show NOT up since it is raised before", e="test_err2")

            c_stat.percent = i
