import dataclasses
import os.path
import pathlib
import subprocess
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.module_command_utils import (
    CommandRunException,
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
    def __init__(self, test_name, base_path: pathlib.Path, test_dir: pathlib.Path):
        self.__base_path = base_path
        self.__test_dir = test_dir
        self.__call_stack: typing.List[typing.Tuple[MockCall, MockedReturnData]] = []
        self.__test_files_dirs: typing.List[pathlib.Path] = self.__find_dirs_upwards(
            self.__test_dir,
            [
                os.path.join(
                    "test_files",
                    test_name,
                ),
                "test_files",
            ],
        )

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
        stdout = self.__load_from_file(stdout_file_name) if stdout_file_name else None
        stderr = self.__load_from_file(stderr_file_name) if stderr_file_name else None
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

    def __load_from_file(self, file_name) -> str:
        for path in self.__test_files_dirs:
            target_path = path.joinpath(file_name)
            if target_path.is_file():
                return target_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"{file_name} not found")

    def __find_dirs_upwards(
        self,
        cwd: pathlib.Path,
        names: typing.List[str],
        paths: typing.List[pathlib.Path] = None,
    ) -> pathlib.Path | None:
        paths = paths or []
        for name in names:
            fullpath = cwd.joinpath(name)
            if fullpath.is_dir():
                paths.append(fullpath)

        if (
            cwd == pathlib.Path(cwd.root)
            or cwd == cwd.parent
            or cwd == self.__base_path
        ):
            return paths

        return self.__find_dirs_upwards(cwd.parent, names, paths=paths)


class CommandMockerBuilder:
    def __init__(self, test_name, test_dir):
        self.__test_dir = test_dir
        self.__test_name = test_name
        self.__base_path = find_upwards(test_dir, "unit")
        if not self.__base_path:
            raise FileNotFoundError("Cannot locate the tests base path")

    def build(self):
        return CommandMocker(self.__test_name, self.__base_path, self.__test_dir)
