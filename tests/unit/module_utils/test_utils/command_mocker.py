import dataclasses
import pathlib
import subprocess
import typing

from ansible_collections.pbtn.common.plugins.module_utils.module_command_utils import (
    CommandRunException,
)

from ansible_collections.pbtn.common.tests.unit.module_utils.test_utils import (
    file_manager,
)


@dataclasses.dataclass
class MockCall:
    cmd: typing.List[str]
    check: bool

    def __eq__(self, other):
        if not isinstance(other, MockCall):
            return NotImplemented

        return self.cmd == other.cmd and self.check == other.check

    def __str__(self):
        return f"cmd: {self.cmd} check: {self.check}"

    def __hash__(self):
        return hash((self.cmd, self.check))


@dataclasses.dataclass
class MockedReturnData:
    stdout: str
    stderr: str
    rc: int
    exception: CommandRunException
    fn: typing.Callable[[typing.List], subprocess.CompletedProcess]


def find_upwards(cwd: pathlib.Path, name: str) -> pathlib.Path | None:
    if cwd == pathlib.Path(cwd.root) or cwd == cwd.parent:
        return None

    fullpath = cwd.joinpath(name)

    return fullpath if fullpath.exists() else find_upwards(cwd.parent, name)


class CommandMocker:
    def __init__(self, file_manager: file_manager.FileManager):
        self.__file_manager = file_manager
        self.__call_stack: typing.List[typing.Tuple[MockCall, MockedReturnData]] = []

    def add_call_definition(
        self,
        expected: MockCall,
        stdout=None,
        stderr=None,
        rc=0,
        exception=None,
        fn: typing.Callable[[typing.List], subprocess.CompletedProcess] = None,
    ):
        stack_entry = (expected, MockedReturnData(stdout, stderr, rc, exception, fn))
        self.__call_stack.append(stack_entry)

    def add_call_definition_with_file(
        self,
        expected: MockCall,
        stdout_file_name=None,
        stderr_file_name=None,
        rc=0,
        exception=None,
        fn: typing.Callable[[typing.List], subprocess.CompletedProcess] = None,
    ):
        stdout = (
            self.__file_manager.get_file_text_content(stdout_file_name)
            if stdout_file_name
            else None
        )
        stderr = (
            self.__file_manager.get_file_text_content(stderr_file_name)
            if stderr_file_name
            else None
        )
        self.add_call_definition(
            expected, stdout=stdout, stderr=stderr, rc=rc, exception=exception, fn=fn
        )

    def run(self, cmd, check=True) -> subprocess.CompletedProcess:
        call = MockCall(cmd, check=check)
        if not self.__call_stack:
            raise AssertionError(
                f"Unexpected call. Not pending calls queued. Call: {call}"
            )
        if self.__call_stack[0][0] != call:
            raise AssertionError(
                f"Unexpected call. Expected: {self.__call_stack[0]}. Call: {call}"
            )
        call_data = self.__call_stack.pop(0)[1]
        if call_data.fn:
            return call_data.fn(cmd, check)
        if call_data.exception:
            raise call_data.exception
        if call_data.rc:
            raise CommandRunException(
                stdout=call_data.stdout,
                stderr=call_data.stderr,
                return_code=call_data.rc,
            )
        return subprocess.CompletedProcess(
            cmd, call_data.rc, call_data.stdout, call_data.stderr
        )


class CommandMockerBuilder:
    def __init__(self, file_manager: file_manager.FileManager):
        self.__file_manager = file_manager

    def build(self):
        return CommandMocker(self.__file_manager)
