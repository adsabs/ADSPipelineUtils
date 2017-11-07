"""
Contains useful functions and utilities that are not neccessarily only useful
for this module. But are also used in differing modules insidide the same
project, and so do not belong to anything specific.
"""

from __future__ import absolute_import, unicode_literals
from celery import Celery, Task
from celery.exceptions import SoftTimeLimitExceeded
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import load_only as _load_only
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
import sys
import os
import logging
import imp
import sys
import time
from dateutil import parser, tz
from datetime import datetime
import socket
import inspect
from cloghandler import ConcurrentRotatingFileHandler
from kombu.serialization import register, registry
from kombu import Exchange, BrokerConnection
import logmatic
from .serializer import register_args
import random

local_zone = tz.tzlocal()
utc_zone = tz.tzutc()


def _get_proj_home(extra_frames=0):
    """Get the location of the caller module; then go up max_levels until
    finding requirements.txt"""

    frame = inspect.stack()[2+extra_frames]
    module = inspect.getsourcefile(frame[0])
    if not module:
        raise Exception("Sorry, wasnt able to guess your location. Let devs know about this issue.")
    d = os.path.dirname(module)
    x = d
    max_level = 3
    while max_level:
        f = os.path.abspath(os.path.join(x, 'requirements.txt'))
        if os.path.exists(f):
            return x
        x = os.path.abspath(os.path.join(x, '..'))
        max_level -= 1
    sys.stderr.write("Sorry, cant find the proj home; returning the location of the caller: %s\n" % d)
    return d



def get_date(timestr=None):
    """
    Always parses the time to be in the UTC time zone; or returns
    the current date (with UTC timezone specified)

    :param: timestr
    :type: str or None

    :return: datetime object with tzinfo=tzutc()
    """
    if timestr is None:
        return datetime.utcnow().replace(tzinfo=utc_zone)

    if isinstance(timestr, datetime):
        date = timestr
    else:
        date = parser.parse(timestr)

    if 'tzinfo' in repr(date): #hack, around silly None.encode()...
        date = date.astimezone(utc_zone)
    else:
        # this depends on current locale, for the moment when not
        # timezone specified, I'll treat them as UTC (however, it
        # is probably not correct and should work with an offset
        # but to that we would have to know which timezone the
        # was created)

        #local_date = date.replace(tzinfo=local_zone)
        #date = date.astimezone(utc_zone)

        date = date.replace(tzinfo=utc_zone)

    return date


def date2solrstamp(t):
    """
    Received datetime object and returns it formatted the way that
    SOLR likes (variation on the ISO format).
    
    @param t: datetime object (we expect it to be in UTC)
    @return: string
    """
    
    return t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    

def load_config(proj_home=None, extra_frames=0):
    """
    Loads configuration from config.py and also from local_config.py

    :param: proj_home - str, location of the home - we'll always try
        to load config files from there. If the location is empty,
        we'll inspect the caller and derive the location of its parent
        folder.
    :param: extra_frames - int, number of frames to look back; default
        is 2, which is good when the load_config() is called directly,
        but when called from inside classes, we need to add extra more

    :return dictionary
    """
    conf = {}

    if proj_home is not None:
        proj_home = os.path.abspath(proj_home)
        if not os.path.exists(proj_home):
            raise Exception('{proj_home} doesnt exist'.format(proj_home=proj_home))
    else:
        proj_home = _get_proj_home(extra_frames=extra_frames)


    if proj_home not in sys.path:
        sys.path.append(proj_home)

    conf['PROJ_HOME'] = proj_home

    conf.update(load_module(os.path.join(proj_home, 'config.py')))
    conf.update(load_module(os.path.join(proj_home, 'local_config.py')))

    return conf



def load_module(filename):
    """
    Loads module, first from config.py then from local_config.py

    :return dictionary
    """

    filename = os.path.join(filename)
    d = imp.new_module('config')
    d.__file__ = filename
    try:
        with open(filename) as config_file:
            exec(compile(config_file.read(), filename, 'exec'), d.__dict__)
    except IOError as e:
        pass
    res = {}
    from_object(d, res)
    return res


def setup_logging(name_, level=None, proj_home=None):
    """
    Sets up generic logging to file with rotating files on disk

    :param: name_: the name of the logfile (not the destination!)
    :param: level: the level of the logging DEBUG, INFO, WARN
    :param: proj_home: optional, starting dir in which we'll
            check for (and create) 'logs' folder and set the
            logger there
    :return: logging instance
    """

    if level is None:
        config = load_config(extra_frames=1, proj_home=proj_home)
        level = config.get('LOGGING_LEVEL', 'INFO')

    level = getattr(logging, level)
    formatter = logmatic.JsonFormatter(extra={"hostname":socket.gethostname()})
    logging_instance = logging.getLogger(name_)

    if proj_home:
        proj_home = os.path.abspath(proj_home)
        fn_path = os.path.join(proj_home, 'logs')
    else:
        fn_path = os.path.join(_get_proj_home(), 'logs')

    if not os.path.exists(fn_path):
        os.makedirs(fn_path)

    fn = os.path.join(fn_path, '{0}.log'.format(name_.split('.log')[0]))
    rfh = ConcurrentRotatingFileHandler(filename=fn,
                                        maxBytes=10485760,
                                        backupCount=10,
                                        mode='a',
                                        encoding='UTF-8')  # 10MB file
    rfh.setFormatter(formatter)
    logging_instance.handlers = []
    logging_instance.addHandler(rfh)
    logging_instance.setLevel(level)

    return logging_instance


def from_object(from_obj, to_obj):
    """Updates the values from the given object.  An object can be of one
    of the following two types:

    Objects are usually either modules or classes.
    Just the uppercase variables in that object are stored in the config.

    :param obj: an import name or object
    """
    for key in dir(from_obj):
        if key.isupper():
            to_obj[key] = getattr(from_obj, key)


def overrides(interface_class):
    """
    To be used as a decorator, it allows the explicit declaration you are
    overriding the method of class from the one it has inherited. It checks that
     the name you have used matches that in the parent class and returns an
     assertion error if not
    """
    def overrider(method):
        """
        Makes a check that the overrided method now exists in the given class
        :param method: method to override
        :return: the class with the overriden method
        """
        assert(method.__name__ in dir(interface_class))
        return method

    return overrider



class ADSCelery(Celery):
    """ADS Pipeline worker; used by all the pipeline applications.


    This class should be instantiated inside tasks.py:

    app = MyADSPipelineCelery()
    """

    def __init__(self, app_name, *args, **kwargs):
        """
        :param: app_name - string, name of the application (can be anything)
        :keyword: local_config - dict, configuration that should be applied
            over the default config (that is loaded from config.py and local_config.py)
        """
        proj_home = None
        if 'proj_home' in kwargs:
            proj_home = kwargs.pop('proj_home')
        self._config = load_config(extra_frames=1, proj_home=proj_home)

        local_config = None
        if 'local_config' in kwargs and kwargs['local_config']:
            local_config = kwargs.pop('local_config')
            self._config.update(local_config) #our config
        if not proj_home:
            proj_home = self._config.get('PROJ_HOME', None)
        self.logger = setup_logging(app_name, proj_home=proj_home, level=self._config.get('LOGGING_LEVEL', 'INFO'))

        # make sure that few important params are set for celery
        if 'broker' not in kwargs:
            kwargs['broker'] = self._config.get('CELERY_BROKER', 'pyamqp://'),
        if 'include' not in kwargs:
            cm = None
            if 'CELERY_INCLUDE' not in self._config:
                cm = self._get_callers_module()
                parts = cm.split('.')
                parts[-1] = 'tasks'
                cm = '.'.join(parts)
                if '.tasks' not in cm:
                    self.logger.debug('It seems like you are not importing from \'.tasks\': %s', cm)
                self.logger.warn('CELERY_INCLUDE is empty, we have to guess it (correct???): %s', cm)
            kwargs['include'] = self._config.get('CELERY_INCLUDE', [cm])

        Celery.__init__(self, *args, **kwargs)
        self._set_serializer()


        self.conf.update(self._config) #celery's config (devs should be careful to avoid clashes)

        self._engine = self._session = None
        if self._config.get('SQLALCHEMY_URL', None):
            self._engine = create_engine(self._config.get('SQLALCHEMY_URL', 'sqlite:///'),
                                   echo=self._config.get('SQLALCHEMY_ECHO', False))
            self._session_factory = sessionmaker()
            self._session = scoped_session(self._session_factory)
            self._session.configure(bind=self._engine)

        if self._config.get('CELERY_DEFAULT_EXCHANGE_TYPE', 'topic') != 'topic':
            self.logger.warn('The exchange type is not "topic" - ' \
                             'are you sure CELERY_DEFAULT_EXCHANGE_TYPE is set properly? (%s)',
                             self._config.get('CELERY_DEFAULT_EXCHANGE_TYPE', ''))

        self.exchange = Exchange(self._config.get('CELERY_DEFAULT_EXCHANGE', 'ads-pipeline'),
                type=self._config.get('CELERY_DEFAULT_EXCHANGE_TYPE', 'topic'))

        self.forwarding_connection = None
        if self._config.get('OUTPUT_CELERY_BROKER', None):
            # kombu connection is lazy loaded, so it's ok to create now
            self.forwarding_connection = BrokerConnection(self._config['OUTPUT_CELERY_BROKER'])

            if self.conf.get('OUTPUT_TASKNAME', None):

                @self.task(name=self._config['OUTPUT_TASKNAME'],
                     exchange=self._config.get('OUTPUT_EXCHANGE', 'ads-pipeline'),
                     queue=self._config.get('OUTPUT_QUEUE', 'update-record'),
                     routing_key=self._config.get('OUTPUT_QUEUE', 'update-record'))
                def _forward_message(self, *args, **kwargs):
                    """A handler that can be used to forward stuff out of our
                    queue. It does nothing (it doesn't process data)"""
                    self.logger.error('We should have never been called directly! %s' % \
                                      (args, kwargs))
                self._forward_message = _forward_message


    def _set_serializer(self):
        """
        all of our workers should use 'adsmsg' serializer by default; 'json' is backup
        so we'll set the defaults here (local_config.py can still override them)
        """
        if 'adsmsg' not in registry.name_to_type:
            register('adsmsg', *register_args)


        self.conf['CELERY_ACCEPT_CONTENT'] = ['adsmsg', 'json']
        self.conf['CELERY_TASK_SERIALIZER'] = 'adsmsg'
        self.conf['CELERY_RESULT_SERIALIZER'] = 'adsmsg'


    def forward_message(self, *args, **kwargs):
        """Class method that is replaced during initializiton with the real
        implementation (IFF) the OUTPUT_TASKNAME and oother OUTPUT_ parameters
        are specified."""
        if not self.forwarding_connection or not self._forward_message:
            raise NotImplementedError('Sorry, your app is not properly configured.')
        self.logger.debug('Forwarding results out to: %s', self.forwarding_connection)
        return self._forward_message.apply_async(args, kwargs,
                                                 connection=self.forwarding_connection)

    def _get_callers_module(self):
        frame = inspect.stack()[2]
        m = inspect.getmodule(frame[0])
        if m.__name__ == '__main__':
            parts = m.__file__.split(os.path.sep)
            return '%s.%s' % (parts[-2], parts[-1].split('.')[0])
        return m.__name__


    def close_app(self):
        """Closes the app"""
        self._session = self._engine = self._session_factory = None
        self.logger = None


    @contextmanager
    def session_scope(self):
        """Provides a transactional session - ie. the session for the
        current thread/work of unit.

        Use as:

            with session_scope() as session:
                o = ModelObject(...)
                session.add(o)
        """

        if self._session is None:
            raise Exception('DB not initialized properly, check: SQLALCHEMY_URL')

        # create local session (optional step)
        s = self._session()

        try:
            yield s
            s.commit()
        except:
            s.rollback()
            raise
        finally:
            s.close()


    def task(self, *args, **opts):
        """Our modification to the Celery.task."""
        if 'base' not in opts:
            opts['base'] = ADSTask
        if 'max_retries' not in opts:
            opts['max_retries'] = 1
        return Celery.task(self, *args, **opts)


    
    def attempt_recovery(self, task, args=None, kwargs=None, einfo=None, retval=None):
        """Here you can try to recover from errors that Celery couldn't deal with.
        
        Example:
        
        if isinstance(retval, SoftTimeLimitExceeded):
            # half the number of processed objects
            first_half, second_half = args[0][0:len(args[0])/2], args[0][len(args[2]/2):]
            # resubmit
            args[0] = first_half
            task.apply_async(args=args, kwargs=kwargs)
            args[0] = second_half
            task.apply_async(args=args, kwargs=kwargs)
            
        Returns: are ignored
        """
        pass


class ADSTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        
        if self.request.retries < self.max_retries:
            self.app.logger.debug('Retrying %s because of exc=%s', task_id, exc)
            self.retry(countdown=2 ** self.request.retries + random.randint(1, 10), exc=exc)
        
        self.app.logger.error('Task=%s failed.\nargs=%s\nkwargs=%s\ntrace=%s', task_id, args, kwargs, einfo)
        #print 'Task=%s failed.\nargs=%s\nkwargs=%s\ntrace=%s' % (task_id, args, kwargs, einfo)


    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if status == 'FAILURE' and hasattr(self.app, 'attempt_recovery'):
            self.app.attempt_recovery(self, retval=retval, args=args, kwargs=kwargs, einfo=einfo)
            

