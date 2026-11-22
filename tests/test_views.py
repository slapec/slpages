import unittest
from pathlib import Path

from slpages import exceptions as exc
from slpages.site import Site
from tests.utils import InMemoryBuildAssertionsMixin, InMemoryTarget

FIXTURES = Path(__file__).parent / 'fixtures' / 'test_views'


class TestRoutes(InMemoryBuildAssertionsMixin, unittest.TestCase):
    def test_decorator_returns_function(self):
        site = Site(FIXTURES)

        def original():
            return 'direct content'

        decorated = site('direct.txt')(original)

        self.assertIs(decorated, original)
        self.assertEqual(decorated(), 'direct content')

    def test_route_name(self):
        for name, expected in ((None, 'page.txt'), ('My page', 'My page'), ('', '')):
            with self.subTest(name=name):
                site = Site(FIXTURES)

                @site('page.txt', name=name)
                def page():
                    return 'content'

                self.assertEqual(str(site.url(expected)), '/page.txt')
                self.assert_builds(site, {'page.txt': 'content'})

    def test_url_unknown_name(self):
        site = Site(FIXTURES)

        with self.assertRaises(exc.UnknownRoute) as caught:
            site.url('unknown')

        self.assertEqual(caught.exception.name, 'unknown')

    def test_url_with_parameters(self):
        site = Site(FIXTURES, path_prefix='/docs')

        @site('/{section}/{name}.html', name='page')
        def page(route):
            return 'content', route('blog', name='hello')

        url = site.url('page', 'blog', name='hello')
        self.assertEqual(str(url), '/docs/blog/hello.html')
        self.assertEqual(url.output_path, '/blog/hello.html')
        self.assertEqual(url['section'], 'blog')
        self.assertEqual(url['name'], 'hello')
        self.assertEqual(str(site.url('page', section='blog', name='hello')), str(url))
        self.assert_builds(site, {'blog/hello.html': 'content'})

    def test_route_pattern_validation(self):
        for path in ('/{page', '/page}'):
            with self.subTest(path=path):
                site = Site(FIXTURES)
                with self.assertRaises(exc.InvalidRoutePattern):
                    @site(path)
                    def page():
                        return 'content'

        for path, parameter in (('/{page-name}', 'page-name'), ('/{class}', 'class')):
            with self.subTest(path=path):
                site = Site(FIXTURES)
                @site(path)
                def page():
                    return 'content'

                url = site.url(path, **{parameter: 'value'})
                self.assertEqual(url[parameter], 'value')
                self.assertEqual(url.path, '/value')

    def test_route_parameter_order(self):
        site = Site(FIXTURES)

        @site('/{a}/{b}/{c}')
        def route_parameter_order(route):
            url = route('A', 'B', 'C')
            return f'a={url['a']}, b={url['b']}, c={url['c']}, url={url}', url

        self.assert_builds(site, {
            'A/B/C': 'a=A, b=B, c=C, url=/A/B/C',
        })

    def test_non_string_parameter(self):
        site = Site(FIXTURES)

        @site('/pages/{page}')
        def non_string_parameter(route):
            url = route(page=1)
            return f'page={url['page']}, url={url}', url

        self.assert_builds(site, {
            'pages/1': 'page=1, url=/pages/1',
        })

    def test_too_many_positional_parameters(self):
        site = Site(FIXTURES)

        @site('/{page}.html')
        def too_many_positional_parameters(route):
            return 'unreachable', route('intro', 'extra')

        self.assert_build_raises(site, exc.TooManyRouteParameters)

    def test_missing_parameter(self):
        site = Site(FIXTURES)

        @site('/{section}/{page}.html')
        def missing_parameter(route):
            return 'unreachable', route(section='blog')

        self.assert_build_raises(site, exc.MissingRouteParameters)

    def test_unknown_parameter(self):
        site = Site(FIXTURES)

        @site('/{page}.html')
        def unknown_parameter(route):
            return 'unreachable', route(page='intro', extra='ignored')

        self.assert_build_raises(site, exc.UnknownRouteParameter)

    def test_duplicate_parameter(self):
        site = Site(FIXTURES)

        @site('/{section}/{page}.html')
        def duplicate_parameter(route):
            return 'unreachable', route('blog', section='news', page='intro')

        target = InMemoryTarget()
        with self.assertLogs('slpages.site', level='WARNING') as logs:
            site.build(target)

        self.assertIn('keyword value will be used', logs.output[0])
        self.assertEqual(target.files, {'news/intro.html': 'unreachable'})

    def test_duplicate_template_parameter(self):
        site = Site(FIXTURES)

        with self.assertLogs('slpages.site', level='WARNING') as logs:
            @site('/{section}/{section}/{page}', name='post')
            def duplicate_template_parameter(route):
                return 'unreachable'

        url = site.url('post', 'blog', 'intro')
        self.assertEqual(url.path, '/blog/blog/intro')
        self.assertIn('Duplicate route parameter', logs.output[0])

    def test_url_parameter_errors(self):
        site = Site(FIXTURES)

        @site('/{page}.html')
        def page():
            return 'content'

        for args, kwargs in (
            ((), {}),
            (('a', 'b'), {}),
            ((), {'unknown': 'a'}),
        ):
            with self.subTest(args=args, kwargs=kwargs):
                with self.assertRaises(exc.RouteParameterError):
                    site.url('/{page}.html', *args, **kwargs)

    def test_duplicate_route_name(self):
        for first_path, first_name, second_path, second_name in (
            ('a.txt', 'page', 'b.txt', 'page'),
            ('a.txt', None, 'a.txt', None),
            ('a.txt', None, 'b.txt', 'a.txt'),
            ('a.txt', '', 'b.txt', ''),
        ):
            with self.subTest(first_name=first_name, second_name=second_name):
                site = Site(FIXTURES)

                @site(first_path, name=first_name)
                def first():
                    return 'first'

                with self.assertLogs('slpages.site', level='WARNING') as logs:
                    @site(second_path, name=second_name)
                    def second():
                        return 'second'

                target = InMemoryTarget()
                if first_path == second_path:
                    with self.assertLogs('slpages.site', level='WARNING') as build_logs:
                        site.build(target)
                    self.assertIn('Duplicate output path', build_logs.output[0])
                else:
                    site.build(target)
                route_name = second_path if second_name is None else second_name
                self.assertEqual(site.url(route_name).path, f'/{second_path}')
                self.assertEqual(target.files, {first_path: 'first', second_path: 'second'})
                self.assertIn('Duplicate route name', logs.output[0])

    def test_unexpected_url_format_error_propagates(self):
        site = Site(FIXTURES)
        error = KeyError('format bug')

        class BrokenValue:
            def __format__(self, spec):
                raise error

        @site('/{page}')
        def page():
            return 'content'

        with self.assertRaises(KeyError) as caught:
            site.url('/{page}', BrokenValue())

        self.assertIs(caught.exception, error)


class TestLowLevelViews(InMemoryBuildAssertionsMixin, unittest.TestCase):
    def test_simple(self):
        site = Site(FIXTURES)

        @site('simple.txt')
        def simple():
            return 'simple content'

        self.assert_builds(site, {
            'simple.txt': 'simple content',
        })

    def test_multiple_views(self):
        site = Site(FIXTURES)

        @site('first.txt')
        def first():
            return 'first content'

        @site('second.txt')
        def second():
            return 'second content'

        self.assert_builds(site, {
            'first.txt': 'first content',
            'second.txt': 'second content',
        })

    def test_binary(self):
        site = Site(FIXTURES)

        @site('/tests/test_binary/out.bin')
        def binary():
            return b'binary content'

        self.assert_builds(site, {
            'tests/test_binary/out.bin': b'binary content',
        })

    def test_file(self):
        site = Site(FIXTURES)

        @site('/tests/test_file/out.bin')
        def file():
            return FIXTURES / 'test.bin'

        self.assert_builds(site, {
            'tests/test_file/out.bin': b'copied file content',
        })

    def test_parameterized(self):
        site = Site(FIXTURES)

        @site('/tests/{page_param}')
        def parameterized(route):
            url = route(page_param='parameterized.txt')
            return f'parameterized content, page_param={url['page_param']}, url={url}', url

        self.assert_builds(site, {
            'tests/parameterized.txt': (
                'parameterized content, page_param=parameterized.txt, url=/tests/parameterized.txt'
            ),
        })

    def test_multiple_parameters(self):
        site = Site(FIXTURES)

        @site('/{section}/{page}.html')
        def multiple_parameters(route):
            url = route('blog', page='intro')
            return f'section={url['section']}, page={url['page']}, url={url}', url

        self.assert_builds(site, {
            'blog/intro.html': 'section=blog, page=intro, url=/blog/intro.html',
        })

    def test_parameterized_file(self):
        site = Site(FIXTURES)

        @site('/tests/test_file/{name}')
        def parameterized_file(route):
            url = route('parameterized.bin')
            return FIXTURES / 'test.bin', url

        self.assert_builds(site, {
            'tests/test_file/parameterized.bin': b'copied file content',
        })

    def test_list(self):
        site = Site(FIXTURES)

        @site('/{page}.txt')
        def pages(route):
            return [('first', route('a')), ('second', route('b'))]

        self.assert_builds(site, {
            'a.txt': 'first',
            'b.txt': 'second',
        })

    def test_generator(self):
        site = Site(FIXTURES)

        @site('/tests/generator/{page}')
        def generator(route):
            for i in [0, 1, 2]:
                url = route(f'{i}.txt')
                yield f'contents of file {url['page']}', url

        self.assert_builds(site, {
            'tests/generator/0.txt': 'contents of file 0.txt',
            'tests/generator/1.txt': 'contents of file 1.txt',
            'tests/generator/2.txt': 'contents of file 2.txt',
        })

    def test_generator_files(self):
        site = Site(FIXTURES)

        @site('/tests/test_file/{name}')
        def generator_files(route):
            for name in ['a.bin', 'b.bin']:
                yield FIXTURES / 'test.bin', route(name)

        self.assert_builds(site, {
            'tests/test_file/a.bin': b'copied file content',
            'tests/test_file/b.bin': b'copied file content',
        })

    def test_invalid_view_results(self):
        invalid_results = (
            None,
            42,
            (),
            ('content',),
            ('content', 'url', 'extra'),
            ['content'],
            iter(['content']),
        )
        for result in invalid_results:
            with self.subTest(result_type=type(result).__name__):
                site = Site(FIXTURES)

                @site('invalid.txt')
                def invalid():
                    return result

                self.assert_build_raises(site, exc.InvalidViewContent)

    def test_empty_iterable_of_results(self):
        site = Site(FIXTURES)

        @site('/{page}')
        def pages(route):
            return []

        self.assert_builds(site, {})

    def test_unexpected_view_error_propagates(self):
        site = Site(FIXTURES)
        error = ValueError('view bug')

        @site('broken.txt')
        def broken():
            raise error

        with self.assertRaises(ValueError) as caught:
            self.assert_builds(site, {})

        self.assertIs(caught.exception, error)

    def test_duplicate_generator_outputs(self):
        site = Site(FIXTURES)

        @site('/{page}')
        def pages(route):
            yield 'first', route('same')
            yield 'second', route('same')

        target = InMemoryTarget()
        with self.assertLogs('slpages.site', level='WARNING') as logs:
            site.build(target)

        self.assertEqual(target.files, {'same': 'second'})
        self.assertIn('Duplicate output path', logs.output[0])

    def test_repeated_build_is_stable(self):
        site = Site(FIXTURES)
        generated_paths = []

        @site('simple.txt')
        def simple():
            return 'simple content'

        @site('/{page}.txt')
        def pages(route):
            url = route('a')
            generated_paths.append(url.path)
            yield 'page content', url

        for _ in range(2):
            self.assert_builds(site, {
                'simple.txt': 'simple content',
                'a.txt': 'page content',
            })

        self.assertEqual(generated_paths, ['/a.txt', '/a.txt'])

    def test_parameterized_view_result_errors(self):
        cases = (
            ('content', exc.InvalidParameterizedViewResult),
            (('content', 'not a URL'), exc.InvalidViewUrl),
            ([('content',)], exc.InvalidViewResultTuple),
            (['content'], exc.InvalidParameterizedViewResult),
        )
        for result, error_type in cases:
            with self.subTest(result=result):
                site = Site(FIXTURES)

                @site('/{page}')
                def page(route):
                    return result

                self.assert_build_raises(site, error_type)
