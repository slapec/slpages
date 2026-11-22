import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from slpages import exceptions as exc
from slpages.site import Site
from slpages.target import FileSystem


class TestFileSystemTarget(unittest.TestCase):
    def test_leading_slash_is_relative_to_output_root(self):
        with TemporaryDirectory() as directory:
            target = FileSystem(directory)
            target.write('/about.html', 'first')
            target.write('about.html', 'second')
            self.assertEqual((Path(directory) / 'about.html').read_text(), 'second')

    def test_extensionless_path_is_written_verbatim(self):
        with TemporaryDirectory() as directory:
            target = FileSystem(directory)
            target.write('/about', 'content')
            self.assertTrue((Path(directory) / 'about').is_file())

    def test_output_cannot_escape_root(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = FileSystem(root / 'output')
            with self.assertRaises(exc.InvalidOutputPath):
                target.write('../outside.txt', 'content')
            self.assertFalse((root / 'outside.txt').exists())

    def test_directory_path_does_not_generate_index(self):
        with TemporaryDirectory() as directory:
            target = FileSystem(directory)
            with self.assertRaises(exc.InvalidOutputPath):
                target.write('/about/', 'content')
            self.assertFalse((Path(directory) / 'about/index.html').exists())


class TestSiteBuildTarget(unittest.TestCase):
    def test_build_accepts_string_output(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            site = Site(directory)

            @site('index.html')
            def index():
                return 'index content'

            site.build(str(output))

            self.assertEqual((output / 'index.html').read_text(), 'index content')

    def test_build_writes_text_and_bytes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'output'
            site = Site(root)

            @site('/pages/about.html')
            def about():
                return 'Árvíztűrő tükörfúrógép'

            @site('assets/raw.bin')
            def binary():
                return b'\x01\xfe'

            site.build(output)

            self.assertEqual((output / 'pages/about.html').read_text(encoding='utf-8'),
                             'Árvíztűrő tükörfúrógép')
            self.assertEqual((output / 'assets/raw.bin').read_bytes(), b'\x01\xfe')
            self.assertEqual(sorted(str(path.relative_to(output)) for path in output.rglob('*') if path.is_file()),
                             ['assets/raw.bin', 'pages/about.html'])

    def test_build_copies_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.bin'
            source.write_bytes(b'\x00\xff')
            output = root / 'output'
            site = Site(root)

            @site('/assets/copy.bin')
            def copy():
                return source

            site.build(output)

            self.assertEqual((output / 'assets/copy.bin').read_bytes(), b'\x00\xff')

    def test_build_warns_on_duplicate_output_and_uses_later_file(self):
        with TemporaryDirectory() as directory:
            site = Site(directory)

            @site('/about.html', name='first')
            def first():
                return 'first'

            @site('about.html', name='second')
            def second():
                return 'second'

            with self.assertLogs('slpages.site', level='WARNING') as logs:
                site.build(FileSystem(directory))

            self.assertIn('Duplicate output path', logs.output[0])
            self.assertEqual((Path(directory) / 'about.html').read_text(), 'second')

    def test_build_rejects_directory_path(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            site = Site(directory)

            @site('about/')
            def about():
                return 'content'

            self.assertEqual(site.url('about/').path, '/about/')

            with self.assertRaises(exc.InvalidOutputPath) as caught:
                site.build(output)

            self.assertEqual(caught.exception.path, 'about/')
            self.assertFalse((output / 'about').exists())
