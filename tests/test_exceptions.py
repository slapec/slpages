import pickle
import unittest

from slpages import exceptions as exc


class TestSLPagesError(unittest.TestCase):
    def test_category_code(self):
        groups = (
            (1, (exc.SLPagesError,)),
            (2, (
                exc.RouteError,
                exc.RouteParameterError,
                exc.InvalidRoutePattern,
                exc.UnknownRoute,
                exc.UnknownRouteParameter,
                exc.MissingRouteParameters,
                exc.TooManyRouteParameters,
            )),
            (3, (
                exc.ContentError,
                exc.UnsupportedContent,
                exc.MissingHtmlElement,
                exc.InvalidContentTitle,
                exc.InvalidMarkdownFrontMatterType,
                exc.InvalidMarkdownTags,
                exc.InvalidMarkdownLanguage,
            )),
            (4, (
                exc.BuildError,
                exc.ViewResultError,
                exc.OutputError,
                exc.InvalidOutputPath,
                exc.InvalidViewResultTuple,
                exc.InvalidParameterizedViewResult,
                exc.InvalidViewContent,
            )),
        )
        for code, error_types in groups:
            for error_type in error_types:
                with self.subTest(error=error_type.__name__):
                    self.assertEqual(error_type.category_code, code)

    def test_pickle_round_trip(self):
        errors = (
            exc.InvalidRoutePattern('/{page'),
            exc.InvalidOutputPath('../outside'),
            exc.UnknownRoute('post'),
            exc.UnsupportedContent('.txt'),
            exc.UnknownRouteParameter('slug'),
            exc.MissingRouteParameters(['section', 'slug']),
            exc.TooManyRouteParameters(1, 2),
            exc.MissingHtmlElement('head'),
            exc.InvalidContentTitle(None),
            exc.InvalidMarkdownFrontMatterType(['title']),
            exc.InvalidMarkdownTags('tags', 'tag'),
            exc.InvalidViewResultTuple(3),
            exc.InvalidParameterizedViewResult('content'),
            exc.InvalidViewContent(42),
            exc.InvalidViewUrl('url'),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                restored = pickle.loads(pickle.dumps(error))
                self.assertIs(type(restored), type(error))
                self.assertEqual(restored.args, error.args)
                self.assertEqual(vars(restored), vars(error))
                self.assertEqual(str(restored), str(error))


class TestRouteErrors(unittest.TestCase):
    def test_invalid_pattern(self):
        error = exc.InvalidRoutePattern('/{page')
        self.assertIsInstance(error, exc.RouteParameterError)
        self.assertEqual(error.path, '/{page')
        self.assertEqual(str(error), 'Invalid route pattern: /{page')

    def test_unknown_route(self):
        error = exc.UnknownRoute('post')

        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.name, 'post')
        self.assertEqual(str(error), 'Unknown route: post')

    def test_unknown_route_parameter(self):
        error = exc.UnknownRouteParameter('slug')

        self.assertIsInstance(error, exc.RouteParameterError)
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.name, 'slug')
        self.assertEqual(str(error), 'Unknown route parameter: slug')

    def test_missing_route_parameters(self):
        error = exc.MissingRouteParameters(['section', 'slug'])

        self.assertIsInstance(error, exc.RouteParameterError)
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.names, ('section', 'slug'))
        self.assertEqual(str(error), 'Missing route parameters: section, slug')

    def test_too_many_route_parameters(self):
        error = exc.TooManyRouteParameters(1, 2)

        self.assertIsInstance(error, exc.RouteParameterError)
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.expected, 1)
        self.assertEqual(error.actual, 2)
        self.assertEqual(str(error), 'Too many route parameters: expected at most 1, got 2')


class TestContentErrors(unittest.TestCase):
    def test_unsupported_content(self):
        error = exc.UnsupportedContent('.txt')

        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.extension, '.txt')
        self.assertEqual(str(error), 'Unsupported content extension: .txt')

    def test_missing_html_element(self):
        error = exc.MissingHtmlElement('head')

        self.assertIsInstance(error, exc.ContentError)
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.element, 'head')
        self.assertEqual(str(error), 'Missing HTML element: head')

    def test_invalid_content_title(self):
        error = exc.InvalidContentTitle(None)

        self.assertIsInstance(error, exc.ContentError)
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertIsNone(error.title)
        self.assertEqual(str(error), 'Content title must be a non-empty string')

    def test_invalid_markdown_front_matter_type(self):
        error = exc.InvalidMarkdownFrontMatterType(['title'])

        self.assertIsInstance(error, exc.ContentError)
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.value, ['title'])
        self.assertEqual(str(error), 'Markdown front matter must be a mapping')

    def test_invalid_markdown_tags(self):
        error = exc.InvalidMarkdownTags('tags', 'tag')

        self.assertIsInstance(error, exc.ContentError)
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.field, 'tags')
        self.assertEqual(error.value, 'tag')
        self.assertEqual(str(error), 'Markdown tags must be a list of strings')


class TestViewResultErrors(unittest.TestCase):
    def test_invalid_parameterized_view_result(self):
        error = exc.InvalidParameterizedViewResult('content')

        self.assertIsInstance(error, exc.ViewResultError)
        self.assertEqual(error.result, 'content')
        self.assertEqual(
            str(error),
            'Parameterized view must return a (content, Url) tuple or an iterable of such tuples; got str',
        )

    def test_invalid_view_result_tuple(self):
        error = exc.InvalidViewResultTuple(3)

        self.assertIsInstance(error, exc.ViewResultError)
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.size, 3)
        self.assertEqual(str(error), 'View result tuple must contain content and URL; got 3 items')

    def test_invalid_view_content(self):
        error = exc.InvalidViewContent(42)

        self.assertIsInstance(error, exc.ViewResultError)
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.content, 42)
        self.assertEqual(str(error), 'View content must be str, bytes or Path; got int')


class TestOutputErrors(unittest.TestCase):
    def test_invalid_path(self):
        error = exc.InvalidOutputPath('../outside')
        self.assertIsInstance(error, exc.SLPagesError)
        self.assertEqual(error.path, '../outside')
        self.assertEqual(str(error), 'Invalid output path: ../outside')
