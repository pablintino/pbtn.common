import pathlib

import pytest
from ansible_collections.pbtn.common.tests.unit.module_utils.test_utils import (
    command_mocker,
    file_manager,
)


@pytest.fixture
def test_file_manager(request):
    return file_manager.FileManager(
        request.node.originalname, pathlib.Path(request.module.__file__).parent
    )


@pytest.fixture
def command_mocker_builder(test_file_manager):
    return command_mocker.CommandMockerBuilder(test_file_manager)
