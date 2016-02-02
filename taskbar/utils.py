# -*- coding: utf-8 -*-
from __future__ import print_function


def datetime_difference(start_time, end_time):
    """
    returns the time difference of two datetime objects in HH:MM:SS format
    """

    l = end_time - start_time

    if l.days < 0:
        return "N/A"

    temp1 = divmod(l.seconds, 60)
    temp2 = divmod(temp1[0], 60)

    hr = temp2[0]
    mn = temp2[1]
    sec = temp1[1]

    # Adding 0 so it shows 01 instead of 0
    if hr < 10:
        hr = "0%s" % hr

    if mn < 10:
        mn = "0%s" % mn

    if sec < 10:
        sec = "0%s" % sec

    return "%s:%s:%s" % (hr, mn, sec)


def decorator_with_args(decorator_to_enhance):
    """
    This function is supposed to be used as a decorator to decorate the decorator allowing it to accept args.

    Example:

    @decorator_with_args
    def decorated_decorator(func, *args, **kwargs):
        def wrapper(function_arg1, function_arg2):
            print "Decorated with", args, kwargs
            return func(function_arg1, function_arg2)
        return wrapper

    # Then you decorate the functions you wish with your brand new decorated decorator.

    @decorated_decorator(42, 404, 1024)
    def decorated_function(function_arg1, function_arg2):
        print "Hello", function_arg1, function_arg2

    decorated_function("Universe and", "everything")
    #outputs:
    #Decorated with (42, 404, 1024) {}
    #Hello Universe and everything

    """

    def decorator_maker(*args, **kwargs):

        def decorator_wrapper(func):

            return decorator_to_enhance(func, *args, **kwargs)

        return decorator_wrapper

    return decorator_maker
