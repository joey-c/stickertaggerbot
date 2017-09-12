import pytest


def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previous_failed = item


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        previous_failed = getattr(item.parent, "_previous_failed", None)
        if previous_failed is not None:
            pytest.xfail("previous test failed (%s)" % previous_failed.name)
