import subprocess
import typing

from ansible.module_utils.common.text.converters import to_text


class CommandRunnerFn(typing.Protocol):
    def __call__(
        self, cmd: typing.List[str], check: typing.Optional[bool] = True
    ) -> subprocess.CompletedProcess:
        ...


class CommandRunException(Exception):
    def __init__(
        self, *args, stdout=None, stderr=None, return_code=None, cmd=None
    ) -> None:
        super().__init__(*args)
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        self.cmd = cmd

    def __str__(self) -> str:
        return f"[{self.cmd} ({self.return_code})] {self.stdout} {self.stderr}".rstrip()


def get_local_command_runner() -> CommandRunnerFn:
    def local_run_fn(cmd, check=True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )
        if check and result.returncode:
            raise CommandRunException(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                cmd=cmd,
            )
        return result

    return local_run_fn


def get_module_command_runner(module) -> CommandRunnerFn:
    def ansible_run_fn(cmd, check=True) -> subprocess.CompletedProcess:
        return_code, stdout, stderr = module.run_command(
            [to_text(item) for item in cmd] if isinstance(cmd, list) else to_text(cmd)
        )
        if check and return_code:
            raise CommandRunException(
                stdout=stdout, stderr=stderr, return_code=return_code, cmd=cmd
            )

        return subprocess.CompletedProcess(cmd, return_code, stdout, stderr)

    return ansible_run_fn
