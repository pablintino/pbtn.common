import subprocess
import typing

from ansible.module_utils.common.text.converters import to_text


class CommandRunException(Exception):
    def __init__(
        self, *args: object, stdout=None, stderr=None, return_code=None
    ) -> None:
        super().__init__(*args)
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code

    def __str__(self) -> str:
        return f"[{self.return_code}] {self.stdout} {self.stderr}".rstrip()


def get_local_command_runner() -> (
    typing.Callable[[typing.List], subprocess.CompletedProcess]
):
    def local_run_fn(cmd, check=True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )
        if check and result.returncode:
            raise CommandRunException(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
        return result

    return local_run_fn


def get_module_command_runner(
    module,
) -> typing.Callable[[typing.List], subprocess.CompletedProcess]:
    def ansible_run_fn(cmd, check=True) -> subprocess.CompletedProcess:
        returncode, stdout, stderr = module.run_command(
            [to_text(item) for item in cmd] if isinstance(cmd, list) else to_text(cmd)
        )
        if check and returncode:
            raise CommandRunException(
                stdout=stdout, stderr=stderr, return_code=returncode
            )

        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)

    return ansible_run_fn
