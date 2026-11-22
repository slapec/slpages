import unittest
from pathlib import Path

import jinja2

from slpages import exceptions as exc
from slpages.content import Content
from slpages.site import Site

FIXTURES = Path(__file__).parent / 'fixtures' / 'test_template'


class TestTemplate(unittest.TestCase):
    def test_render_template_without_context(self):
        site = Site(FIXTURES / 'render_template')
        rendered = site.template(template='static.txt').render()

        self.assertEqual(rendered, 'static template')

    def test_render_template(self):
        site = Site(FIXTURES / 'render_template')

        rendered = site.template('value.txt').render({
            'value': 'local',
            'extra': 'render',
        })

        self.assertEqual(rendered, 'values: value=local, extra=render')

    def test_site_context(self):
        site = Site(FIXTURES / 'render_template', context={
            'value': 'site',
            'extra': 'global',
        })
        rendered = site.template('value.txt').render()

        self.assertEqual(rendered, 'values: value=site, extra=global')

    def test_missing_variable_raises(self):
        site = Site(FIXTURES / 'render_template')

        with self.assertRaises(jinja2.UndefinedError):
            site.template('value.txt').render()

    def test_relative_template_path(self):
        site = Site(FIXTURES / 'render_template')
        rendered = site.template('nested/index.txt').render({
            'value': 'template'
        })

        self.assertEqual(rendered, 'nested: template')

    def test_template_url_global(self):
        site = Site(FIXTURES / 'render_template')

        @site('/about.html', name='about')
        def about():
            return 'about'

        @site('/posts/{slug}.html', name='post')
        def post():
            return 'post'

        rendered = site.template('url.txt').render()

        self.assertEqual(rendered, 'links: /about.html /posts/hello.html')

    def test_url_parameters_support_template_item_access(self):
        site = Site(FIXTURES / 'render_template')

        @site('/posts/{slug}.html', name='post')
        def post():
            return 'post'

        @site('/{path}', name='path')
        def path():
            return 'path'

        template = site.env.from_string(
            "{{ url('post', slug='hello').slug }} "
            "{{ url('post', slug='world')['slug'] }} "
            "{{ url('path', 'parameter')['path'] }} "
            "{{ url('path', 'parameter').path }}"
        )

        self.assertEqual(template.render(), 'hello world parameter /parameter')

    def test_template_url_global_uses_path_prefix(self):
        site = Site(FIXTURES / 'render_template', path_prefix='/docs')

        @site('/about.html', name='about')
        def about():
            return 'about'

        @site('/posts/{slug}.html', name='post')
        def post():
            return 'post'

        rendered = site.template('url.txt').render()

        self.assertEqual(rendered, 'links: /docs/about.html /docs/posts/hello.html')

    def test_template_url_global_propagates_unknown_route(self):
        site = Site(FIXTURES / 'render_template')

        with self.assertRaises(exc.UnknownRoute):
            site.template('url.txt').render()

    def test_template_uses_current_site_context(self):
        site = Site(FIXTURES / 'render_template', context={
            'value': 'initial',
            'extra': 'global',
        })
        template = site.template('value.txt')

        site.context['value'] = 'updated'
        self.assertEqual(template.render(), 'values: value=updated, extra=global')

        site.context = {'value': 'replaced', 'extra': 'new'}
        self.assertEqual(template.render(), 'values: value=replaced, extra=new')

    def test_initially_empty_site_context_remains_live(self):
        context = {}
        site = Site(FIXTURES / 'render_template', context=context)
        template = site.template('value.txt')

        context.update({'value': 'added', 'extra': 'later'})

        self.assertEqual(template.render(), 'values: value=added, extra=later')

    def test_template_reuse_does_not_mutate_context(self):
        site_context = {'value': 'site', 'extra': 'global'}
        site = Site(FIXTURES / 'render_template', context=site_context)
        template = site.template('value.txt')
        context = {'value': 'local'}

        self.assertEqual(
            template.render({'value': 'local', 'extra': 'render'}),
            'values: value=local, extra=render',
        )
        self.assertEqual(template.render(context), 'values: value=local, extra=global')
        self.assertEqual(template.render(), 'values: value=site, extra=global')
        self.assertEqual(context, {'value': 'local'})
        self.assertEqual(site_context, {'value': 'site', 'extra': 'global'})


class TestSiteContent(unittest.TestCase):
    def test_content_parser_is_selected_by_extension(self):
        site = Site(FIXTURES)
        cases = (
            ('html/index.html', 'html content'),
            ('markdown/index.md', 'markdown content'),
        )
        for path, expected_title in cases:
            with self.subTest(path=path):
                content = site.content(path)
                self.assertEqual(content.title, expected_title)

    def test_content_reads_utf8(self):
        site = Site(FIXTURES / 'html')

        content = site.content('unicode.html')

        self.assertEqual(content.title, 'árvíztűrő tükörfúrógép')
        self.assertEqual(content.body, '<p>őű</p>')

    def test_explicit_parser_overrides_extension(self):
        site = Site(FIXTURES)

        def parse_text(text: str) -> Content:
            return Content(title='title', body=text, lang=None, tags=[])

        for path in ('html/index.html', 'render_template/static.txt'):
            with self.subTest(path=path):
                content = site.content(path, parse_text)
                self.assertEqual(content.body, (FIXTURES / path).read_text(encoding='utf-8'))

    def test_unsupported_extension_requires_parser(self):
        site = Site(FIXTURES / 'render_template')

        with self.assertRaises(exc.UnsupportedContent) as caught:
            site.content('static.txt')

        self.assertEqual(caught.exception.extension, '.txt')

    def test_context_precedence_and_no_mutation(self):
        site_context = {'title': 'site title', 'value': 'site', 'extra': 'global'}
        context = {'title': 'render title', 'value': 'local'}
        content = Content(title='content title', body='', lang=None, tags=[])
        site = Site(FIXTURES / 'html', context=site_context)

        rendered = site.template('layout/values.html').render({
            **context,
            **content.as_dict(),
        })

        self.assertEqual(rendered, 'values: title=content title, value=local, extra=global')
        self.assertEqual(context, {'title': 'render title', 'value': 'local'})
        self.assertEqual(site_context, {
            'title': 'site title', 'value': 'site', 'extra': 'global',
        })
        self.assertEqual(content, Content(title='content title', body='', lang=None, tags=[]))

    def test_body_is_not_rendered_as_template(self):
        site = Site(FIXTURES / 'html')
        content = Content(title='title', body='<p>{{ value }}</p>', lang=None, tags=[])

        rendered = site.template('layout/body.html').render({
            **content.as_dict(),
            'value': 'rendered value',
        })

        self.assertEqual(rendered, 'body: <p>{{ value }}</p>')
