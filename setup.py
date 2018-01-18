try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import os


# hack: we can't use github in the install_requires section; so until we have an official 
# release of ADSPipelineMsg package available, this has to suffice... 
os.system('pip install --upgrade git+https://github.com/adsabs/ADSPipelineMsg.git@master')

setup(name='adsputils',
      version='0.0.2',
      packages=['adsputils'],
      install_requires=[
          'ConcurrentLogHandler==0.9.1',
          'python-dateutil==2.6.0',
          'DateTime==4.1.1',
          'celery>=4.1.0',
          #'ADSPipelineMsg==1.0.0',
          'SQLAlchemy==1.1.6',
          'setuptools>=36.5.0',
          'six>=1.11.0',
          'python-json-logger==0.1.8',
          'unidecode==0.04.21'
      ],
      #entry_points={
      #      'kombu.serializers': [
      #          'adsmsg = adsputils.serializer:register_args'
      #      ]
      #  }
  )
