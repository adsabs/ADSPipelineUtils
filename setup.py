import os
from subprocess import Popen, PIPE

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    long_description = ""

with open('requirements.txt') as f:
    required = f.read().splitlines()


def get_git_version(default="v0.0.1"):
    try:
        p = Popen(['git', 'describe', '--tags'], stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        line = line.strip()
        return line.decode()
    except:
        return default

setup(
    name='adsputils',
    version=get_git_version(default="v0.0.1"),
    classifiers=['Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.7',
                 "License :: OSI Approved :: MIT License"],
    url='https://github.com/adsabs/ADSPipelineUtils',
    license='MIT',
    license_files=["LICENSE"],
    author="NASA/SAO ADS",
    description='ADS Pipeline Utils',
    long_description=long_description,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=required,
    #entry_points={
    #      'kombu.serializers': [
    #          'adsmsg = adsputils.serializer:register_args'
    #      ]
    #  }
  )
