from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
import subprocess


from ansible_collections.pbtn.common.plugins.module_utils.module_command_utils import (
    get_module_command_runner,
    CommandRunException,
)


def __get_mocked_module_command_runner_fn(mocker, triplet):
    module_mock = mocker.Mock()
    fn_mock = mocker.Mock(return_value=triplet)
    module_mock.run_command = fn_mock
    return get_module_command_runner(module_mock), fn_mock


def __assert_cmd_call(provided_cmd, provided_triplet, run_command_mock, result):
    assert run_command_mock.call_count == 1
    assert len(run_command_mock.call_args.args) == 1
    assert run_command_mock.call_args.args[0] == provided_cmd
    if isinstance(result, CommandRunException):
        assert result.stdout == provided_triplet[1]
        assert result.stderr == provided_triplet[2]
        assert result.return_code == provided_triplet[0]
        assert result.cmd == provided_cmd
    elif isinstance(result, subprocess.CompletedProcess):
        assert result.stdout == provided_triplet[1]
        assert result.stderr == provided_triplet[2]
        assert result.returncode == provided_triplet[0]
        assert result.args == provided_cmd
    else:
        pytest.fail(f"Unexpected result type {type(result)}")


def test_get_module_command_runner_simple_ok(mocker):
    provided_triplet = (0, "stdout", "stderr")
    runner_fn, run_command_mock = __get_mocked_module_command_runner_fn(
        mocker, provided_triplet
    )
    cmd = ["command", "args"]
    result = runner_fn(cmd)
    __assert_cmd_call(cmd, provided_triplet, run_command_mock, result)


def test_get_module_command_runner_simple_string_ok(mocker):
    provided_triplet = (0, "stdout", "stderr")
    runner_fn, run_command_mock = __get_mocked_module_command_runner_fn(
        mocker, provided_triplet
    )
    cmd = "command"
    result = runner_fn(cmd)
    __assert_cmd_call(cmd, provided_triplet, run_command_mock, result)


def test_get_module_command_runner_simple_err(mocker):
    provided_triplet = (1, "stdout", "stderr")
    runner_fn, run_command_mock = __get_mocked_module_command_runner_fn(
        mocker, provided_triplet
    )
    cmd = ["command"]
    result = runner_fn(cmd, check=False)
    __assert_cmd_call(cmd, provided_triplet, run_command_mock, result)


def test_get_module_command_runner_simple_check_err(mocker):
    provided_triplet = (1, "stdout", "stderr")
    runner_fn, run_command_mock = __get_mocked_module_command_runner_fn(
        mocker, provided_triplet
    )
    cmd = ["command"]
    with pytest.raises(CommandRunException) as exception_info:
        runner_fn(cmd)

    __assert_cmd_call(cmd, provided_triplet, run_command_mock, exception_info.value)
