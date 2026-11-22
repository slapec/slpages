from pathlib import Path

from slpages.site import Site
from slpages.target import Target


class InMemoryTarget(Target):
    def __init__(self) -> None:
        self.files: dict[str, str | bytes] = {}

    def write(self, path: str, content: str | bytes) -> None:
        self.files[path] = content

    def copy(self, path: str, source: Path) -> None:
        self.files[path] = Path(source).read_bytes()


class InMemoryBuildAssertionsMixin:
    def assert_builds(
        self,
        site: Site,
        expected_files: dict[str, str | bytes],
    ) -> None:
        target = InMemoryTarget()
        site.build(target)
        self.assertEqual(target.files, expected_files)

    def assert_build_raises(
        self,
        site: Site,
        error_type: type[BaseException],
    ) -> BaseException:
        with self.assertRaises(error_type) as caught:
            site.build(InMemoryTarget())
        return caught.exception
