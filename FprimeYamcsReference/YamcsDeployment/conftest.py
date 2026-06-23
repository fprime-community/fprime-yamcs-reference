import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def chdir_to_test(request):
    original = os.getcwd()
    test_dir = Path(request.fspath).parent
    os.chdir(test_dir)
    yield
    os.chdir(original)
