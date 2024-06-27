# -*- coding: utf-8 -*-

import adsputils
import unittest
import os
import json
import time
from inspect import currentframe, getframeinfo
from adsputils.exceptions import UnicodeHandlerError

def _read_file(fpath):
    with open(fpath, 'r') as fi:
        return fi.read()

class TestInit(unittest.TestCase):

    def test_logging(self):
        logdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs'))
        foo_log = logdir + '/foo.bar.log'
        if os.path.exists(foo_log):
            os.remove(foo_log)
        logger = adsputils.setup_logging('foo.bar')
        logger.warning('first')
        frameinfo = getframeinfo(currentframe())

        #print foo_log
        self.assertTrue(os.path.exists(foo_log))
        c = _read_file(foo_log)
        j = json.loads(c)

        self.assertEqual(j['message'], 'first')
        self.assertTrue('hostname' in j)

        # verify warning has filename and linenumber
        self.assertEqual(os.path.basename(frameinfo.filename), j['filename'])
        self.assertEqual(j['lineno'], frameinfo.lineno - 1)

        time.sleep(0.01)
        # now multiline message
        logger.warning(u'second\nthird')
        logger.warning('last')
        c = _read_file(foo_log)

        found = False
        msecs = False
        for x in c.strip().split('\n'):
            j = json.loads(x)
            self.assertTrue(j)
            if j['message'] == u'second\nthird':
                found = True
            t = adsputils.get_date(j['asctime'])
            if t.microsecond > 0:
                msecs = True

        self.assertTrue(found)
        self.assertTrue(msecs)

    def test_u2asc(self):

        input1 = 'benìtez, n'
        input2 = u'izzet, sakallı'

        output1 = adsputils.u2asc(input1)
        output2 = adsputils.u2asc(input2)

        self.assertEqual(output1,'benitez, n')
        self.assertEqual(output2,u'izzet, sakalli')

        input3 = input2.encode('utf16')
        self.assertRaises(UnicodeHandlerError, adsputils.u2asc, input3)

class TestCelery(unittest.TestCase):

    def test_forward_message_single(self):
        app = adsputils.ADSCelery('test',local_config={
            'OUTPUT_CELERY_BROKER': 'testbroker',
            'OUTPUT_TASKNAME': 'testtaskname'
            })

        self.assertIn('default',app.forward_message_dict.keys())
        self.assertEqual(app.forward_message_dict['default'].get('broker'), 'testbroker')

    def test_forward_message_multiple(self):
        app = adsputils.ADSCelery('test', local_config={
            'FORWARD_MSG_DICT': [{'OUTPUT_PIPELINE': 'augment',
                                  'OUTPUT_CELERY_BROKER': 'testbroker',
                                  'OUTPUT_TASKNAME': 'testtaskname'},
                                 {'OUTPUT_PIPELINE': 'classifier',
                                  'OUTPUT_CELERY_BROKER': 'testbroker2',
                                  'OUTPUT_TASKNAME': 'testtaskname2'}]
        })

        self.assertEqual(len(app.forward_message_dict.keys()), 2)
        self.assertIn('augment', app.forward_message_dict.keys())
        self.assertIn('classifier', app.forward_message_dict.keys())
        self.assertIn('broker', app.forward_message_dict['augment'].keys())
        self.assertEqual(app.forward_message_dict['augment']['broker'], 'testbroker')

if __name__ == '__main__':
    unittest.main()
