import os.path
import pathlib
import typing

import yaml


def find_upwards(cwd: pathlib.Path, name: str) -> typing.Optional[pathlib.Path]:
    if cwd == pathlib.Path(cwd.root) or cwd == cwd.parent:
        return None

    fullpath = cwd.joinpath(name)

    return fullpath if fullpath.exists() else find_upwards(cwd.parent, name)


class FileManager:
    def __init__(self, test_name: str, test_dir: pathlib.Path):
        self.__test_dir = test_dir
        self.__base_path = find_upwards(test_dir, "unit")
        if not self.__base_path:
            raise FileNotFoundError("Cannot locate the tests base path")

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

    def get_file_path(self, file_name) -> pathlib.Path:
        for path in self.__test_files_dirs:
            target_path = path.joinpath(file_name)
            if target_path.is_file():
                return target_path
        raise FileNotFoundError(f"{file_name} not found")

    def get_file_text_content(self, file_name) -> str:
        return self.get_file_path(file_name).read_text(encoding="utf-8")

    def get_file_yaml_content(self, file_name) -> typing.Any:
        with self.get_file_path(file_name).open(mode="r") as file:
            return yaml.safe_load(file)

    def __find_dirs_upwards(
        self,
        cwd: pathlib.Path,
        names: typing.List[str],
        paths: typing.List[pathlib.Path] = None,
    ) -> typing.List[pathlib.Path]:
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
