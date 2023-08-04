[![Python CI actions](https://github.com/adsabs/ADSPipelineUtils/actions/workflows/python_actions.yml/badge.svg)](https://github.com/adsabs/ADSPipelineUtils/actions/workflows/python_actions.yml)
[![Coverage Status](https://coveralls.io/repos/github/adsabs/ADSPipelineUtils/badge.svg?branch=master)](https://coveralls.io/github/adsabs/ADSPipelineUtils?branch=master)

# ADSPipelineUtils

Set of common libraries used by the celery workers.

## Releasing new version to pypi

When a new release is ready, it should be uploaded to pypi. First, try the test environment:

```
python3 -m venv ./venv
source venv/bin/activate
pip install --upgrade setuptools wheel
rm -rf dist/
python3 setup.py sdist
python3 setup.py bdist_wheel --universal
pip install --upgrade twine
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

Verify the [testing pypi repository](https://test.pypi.org/project/adsputils/) and if everything looks good, you can proceed to upload to the [official repository](https://pypi.org/project/adsputils/):

```
twine upload dist/*
```
