#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re
from contextlib import nullcontext

import os.path
import subprocess
import time
import threading
import typing
import pathlib
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.basic import AnsibleModule


__MODULE_PARAM_NAME_CMD = "cmd"
__MODULE_PARAM_NAME_SHELL = "shell"
__MODULE_PARAM_NAME_CHDIR = "chdir"
__MODULE_PARAM_NAME_TIMEOUT = "timeout"
__MODULE_PARAM_NAME_LOG_PATH = "log_path"
__MODULE_PARAM_NAME_LOG_COMBINE = "log_combine"
__MODULE_PARAM_NAME_LOG_TIMESTAMP = "log_timestamp"


class _LogPipe(threading.Thread):
    def __init__(self, file):
        threading.Thread.__init__(self)
        self.daemon = False
        self.file = file
        self.read_fd, self.write_fd = os.pipe()
        self.pipe_reader = os.fdopen(self.read_fd)
        self.start()
        self.output = ""

    def fileno(self) -> int:
        return self.write_fd

    def run(self):
        for line in iter(self.pipe_reader.readline, ""):
            self.output = self.output + line
            if self.file:
                self.file.write(line)
        self.pipe_reader.close()

    def close(self):
        os.close(self.write_fd)

    def __enter__(self):
        return self

    def __exit__(self, _, __, ___):
        self.close()


def _run_capture_command(
    command_list: typing.Union[str, typing.List[str]],
    cwd=None,
    timeout=None,
    executable=None,
    shell=None,
    env=None,
    stdout_file=None,
    stderr_file=None,
) -> typing.Tuple[int, str, str, bool]:
    working_dir = os.getcwd() if not cwd else cwd
    with _LogPipe(stdout_file) as stdout_pipe, (
        _LogPipe(stderr_file) if stderr_file else nullcontext()
    ) as stderr_pipe:
        process = None
        try:
            process = subprocess.Popen(
                command_list,
                executable=executable,
                stdin=subprocess.DEVNULL,
                stdout=stdout_pipe,
                stderr=stderr_pipe or stdout_pipe,
                universal_newlines=True,
                shell=shell,
                cwd=working_dir,
                env=env,
            )
            process.wait(timeout=timeout)
            return (
                process.returncode,
                stdout_pipe.output,
                stderr_pipe.output if stderr_pipe else "",
                False,
            )
        except subprocess.CalledProcessError as err:
            return (
                err.returncode,
                stdout_pipe.output,
                stderr_pipe.output if stderr_pipe else "",
                False,
            )
        except OSError as err:
            return 1, "", str(err), False
        except subprocess.TimeoutExpired:
            return (
                1,
                stdout_pipe.output,
                stderr_pipe.output if stderr_pipe else "",
                True,
            )
        finally:
            if process:
                process.terminate()


def __compute_log_paths(
    module: AnsibleModule,
) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
    logpath = module.params.get(__MODULE_PARAM_NAME_LOG_PATH, None)
    if not logpath:
        return None, None

    log_path = pathlib.Path(logpath)
    extension_index = log_path.name.find(".")
    extension = (
        log_path.name[extension_index:].lstrip(".") if extension_index >= 0 else ""
    )
    if module.params[__MODULE_PARAM_NAME_LOG_TIMESTAMP]:
        extension = (
            time.strftime("%Y-%m-%d-%H%M%S", time.localtime(time.time()))
            + "."
            + extension
        )

    name_no_extension = (
        log_path.name[:extension_index] if extension_index >= 0 else log_path.name
    )

    stdout_name = name_no_extension
    stderr_name = None
    if not module.params[__MODULE_PARAM_NAME_LOG_COMBINE]:
        stdout_name = stdout_name + "-stdout"
        stderr_name = name_no_extension + "-stderr"

    stderr_file = None
    stdout_file = str(log_path.parent.joinpath(stdout_name + "." + extension).resolve())
    if stderr_name:
        stderr_file = str(
            log_path.parent.joinpath(stderr_name + "." + extension).resolve()
        )

    return stdout_file, stderr_file


def main():
    module = AnsibleModule(
        argument_spec={
            __MODULE_PARAM_NAME_CMD: {"type": "raw", "required": True},
            __MODULE_PARAM_NAME_CHDIR: {"type": "path", "required": False},
            __MODULE_PARAM_NAME_TIMEOUT: {
                "type": "int",
                "required": False,
                "default": None,
            },
            __MODULE_PARAM_NAME_LOG_PATH: {"type": "path", "required": False},
            __MODULE_PARAM_NAME_LOG_COMBINE: {
                "type": "bool",
                "required": False,
                "default": False,
            },
            __MODULE_PARAM_NAME_LOG_TIMESTAMP: {
                "type": "bool",
                "required": False,
                "default": False,
            },
            __MODULE_PARAM_NAME_SHELL: {
                "type": "bool",
                "required": False,
                "default": False,
            },
        },
        supports_check_mode=False,
    )

    module.run_command_environ_update = {
        "LANG": "C",
        "LC_ALL": "C",
        "LC_MESSAGES": "C",
        "LC_CTYPE": "C",
    }
    result = {
        "changed": False,
        "success": False,
        "stdout": "",
        "stdout_lines": [],
        "stderr": "",
        "stderr_lines": [],
        "rc": None,
    }

    plain_cmd = module.params[__MODULE_PARAM_NAME_CMD]
    cmd_args = (
        [to_text(item) for item in plain_cmd]
        if isinstance(plain_cmd, list)
        else to_text(plain_cmd)
    )
    shell = module.params[__MODULE_PARAM_NAME_SHELL]
    if not shell and isinstance(cmd_args, str):
        cmd_args = re.sub(" +", " ", cmd_args).split(" ")

    env = os.environ.copy()
    # Clean out python paths set by ansiballz
    if "PYTHONPATH" in env:
        pypaths = [
            x
            for x in env["PYTHONPATH"].split(":")
            if x
            and not x.endswith("/ansible_modlib.zip")
            and not x.endswith("/debug_dir")
        ]
        if pypaths and any(pypaths):
            env["PYTHONPATH"] = ":".join(pypaths)

    stdout_filename, stderr_filename = __compute_log_paths(module)
    with (
        open(stdout_filename, "w", encoding="utf-8")
        if stdout_filename
        else nullcontext()
    ) as stdout_file, (
        open(stderr_filename, "w", encoding="utf-8")
        if stderr_filename
        else nullcontext()
    ) as stderr_file:
        rc, stdout, stderr, timed_out = _run_capture_command(
            cmd_args,
            executable=os.environ.get("SHELL", "/bin/sh") if shell else None,
            cwd=module.params.get(__MODULE_PARAM_NAME_CHDIR, None),
            shell=shell,
            timeout=module.params.get(__MODULE_PARAM_NAME_TIMEOUT, None),
            stdout_file=stdout_file,
            stderr_file=stderr_file,
        )

        if stdout is not None:
            result["stdout_lines"] = stdout.splitlines()
            result["stdout"] = stdout.rstrip("\n")
        if stderr is not None:
            result["stderr_lines"] = stderr.splitlines()
            result["stderr"] = stderr.rstrip("\n")
        if stdout_filename:
            result["stdout_filename"] = stdout_filename
        if stderr_filename:
            result["stderr_filename"] = stderr_filename

        result["rc"] = rc
        if rc != 0:
            result["msg"] = "non-zero return code" if not timed_out else "timed out"
            module.fail_json(**result)

    result["success"] = True
    module.exit_json(**result)


if __name__ == "__main__":
    main()
