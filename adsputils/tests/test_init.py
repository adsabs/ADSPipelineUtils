# -*- coding: utf-8 -*-

import adsputils
import unittest
import os
import json
from StringIO import StringIO
from inspect import currentframe, getframeinfo

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
        # call logger.warn and then capture frame info to get filename and linenumber for testing
        # based on https://stackoverflow.com/questions/3056048/filename-and-line-number-of-python-script
        logger.warn('first')
        frameinfo = getframeinfo(currentframe())
        logger.handlers[0].stream.flush()
        self.assertTrue(os.path.exists(foo_log))
        c = _read_file(foo_log)
        j = json.loads(c)
        self.assertEqual(j['message'], 'first')
        # verify warning has filename and linenumber
        self.assertEqual(os.path.basename(frameinfo.filename), j['filename'])
        self.assertEqual(j['lineno'], frameinfo.lineno - 1)

        # now multiline message, in json it should all be on one line
        logger.warn('second\nthird')
        logger.warn('last')
        # there should be three separate lines of json in the file
        c = _read_file(foo_log)
        buffer = StringIO(c)
        j1 = json.loads(buffer.readline()) 
        j2 = json.loads(buffer.readline())
        j3 = json.loads(buffer.readline())
        self.assertTrue('second\nthird' in j2['message'])
        

if __name__ == '__main__':
    unittest.main()
