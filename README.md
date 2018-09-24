[![Build Status](https://travis-ci.org/adsabs/ADSPipelineUtils.svg?branch=master)](https://travis-ci.org/adsabs/ADSPipelineUtils)
[![Coverage Status](https://coveralls.io/repos/github/adsabs/ADSPipelineUtils/badge.svg?branch=master)](https://coveralls.io/github/adsabs/ADSPipelineUtils?branch=master)

# ADSPipelineUtils

Set of common libraries used by the celery workers.

## Releasing new version to pypi

When a new release is ready, it should be uploaded to pypi. First, try the test environment:

```
virtualenv python
source python/bin/activate
pip install --upgrade setuptools wheel
python setup.py sdist bdist_wheel
pip install --upgrade twine
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

Verify the [testing pypi repository](https://test.pypi.org/project/adsputils/) and if everything looks good, you can proceed to upload to the [official repository](https://pypi.org/project/adsputils/):

```
twine upload dist/*
```

