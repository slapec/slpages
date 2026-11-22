import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from slpages import exceptions as exc


class Target(ABC):
    @abstractmethod
    def write(self, path: str, content: str | bytes) -> None:
        ...

    @abstractmethod
    def copy(self, path: str, source: Path) -> None:
        ...


class FileSystem(Target):
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory).resolve()

    def _prepare_destination(self, output_path: str) -> Path:
        destination_path = (self.directory / output_path.lstrip('/')).resolve()
        if (
            output_path.endswith('/')
            or destination_path == self.directory
            or not destination_path.is_relative_to(self.directory)
        ):
            raise exc.InvalidOutputPath(output_path)

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        return destination_path

    def write(self, path: str, content: str | bytes) -> None:
        destination_path = self._prepare_destination(path)
        if isinstance(content, bytes):
            destination_path.write_bytes(content)
        else:
            destination_path.write_text(content, encoding='utf-8')

    def copy(self, path: str, source: Path) -> None:
        destination_path = self._prepare_destination(path)
        shutil.copyfile(source, destination_path)
