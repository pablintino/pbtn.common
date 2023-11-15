import os
import pytest
import pathlib

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils.command_mocker import (
    CommandMockerBuilder,
)


@pytest.fixture
def command_mocker_builder(request):
    return CommandMockerBuilder(
        request.node.name, pathlib.Path(request.module.__file__).parent
    )
