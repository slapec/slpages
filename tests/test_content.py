import unittest
from textwrap import dedent

import yaml

from slpages import exceptions as exc
from slpages.content import Content


class TestContent(unittest.TestCase):
    def test_as_dict_returns_independent_data(self):
        content = Content(title='title', body='body', lang='hu', tags=['tag'])
        data = content.as_dict()

        self.assertEqual(data, {
            'title': 'title',
            'body': 'body',
            'lang': 'hu',
            'tags': ['tag'],
        })

        data['title'] = 'changed'
        data['tags'].append('new tag')

        self.assertEqual(content, Content(title='title', body='body', lang='hu', tags=['tag']))
        self.assertEqual(content.as_dict()['tags'], ['tag'])

    def test_html_content(self):
        content = Content.from_html('''
            <html lang='en'>
                <head>
                    <title>title</title>
                    <meta name='keywords' content='tag1, tag2'>
                </head>
                <body><h1>body</h1></body>
            </html>
        ''')

        self.assertEqual(content.title, 'title')
        self.assertEqual(content.body, '<h1>body</h1>')
        self.assertEqual(content.lang, 'en')
        self.assertEqual(content.tags, ['tag1', 'tag2'])

    def test_html_content_combines_keywords_and_tags(self):
        content = Content.from_html('''
            <html>
                <head>
                    <title>title</title>
                    <meta name='keywords' content='tag1, tag2'>
                    <meta name='tags' content='tag2, tag3'>
                </head>
                <body></body>
            </html>
        ''')

        self.assertEqual(content.tags, ['tag1', 'tag2', 'tag2', 'tag3'])

    def test_html_content_keeps_meta_order(self):
        content = Content.from_html('''
            <html>
                <head>
                    <title>title</title>
                    <meta name='tags' content='tag1'>
                    <meta name='keywords' content='tag2'>
                </head>
                <body></body>
            </html>
        ''')

        self.assertEqual(content.tags, ['tag1', 'tag2'])

    def test_html_content_defaults_missing_meta(self):
        content = Content.from_html('''
            <html>
                <head><title>title</title></head>
                <body></body>
            </html>
        ''')

        self.assertEqual(content.tags, [])
        self.assertIsNone(content.lang)

    def test_html_content_body_contains_inner_html(self):
        content = Content.from_html('''
            <html>
                <head><title>title</title></head>
                <body><h1>title</h1><p>text</p></body>
            </html>
        ''')

        self.assertEqual(content.body, '<h1>title</h1><p>text</p>')

    def test_html_content_requires_document_elements(self):
        cases = (
            ('<head><title>title</title></head><body></body>', 'html'),
            ('<html><title>title</title><body></body></html>', 'head'),
            ('<html><head><title>title</title></head></html>', 'body'),
            ('<html><head></head><body></body></html>', 'title'),
        )
        for html, missing_element in cases:
            with self.subTest(element=missing_element):
                with self.assertRaises(exc.MissingHtmlElement) as caught:
                    Content.from_html(html)

                self.assertEqual(caught.exception.element, missing_element)

    def test_html_content_requires_non_empty_title(self):
        for title in ('', '   '):
            with self.subTest(title=title):
                with self.assertRaises(exc.InvalidContentTitle):
                    Content.from_html(f'''
                        <html>
                            <head><title>{title}</title></head>
                            <body></body>
                        </html>
                    ''')

    def test_markdown_content(self):
        content = Content.from_markdown(dedent('''\
            ---
            title: title
            lang: en
            tags:
              - tag1
              - tag2
            ---

            # body
        '''))

        self.assertEqual(content.title, 'title')
        self.assertEqual(content.body, '<h1>body</h1>\n')
        self.assertEqual(content.lang, 'en')
        self.assertEqual(content.tags, ['tag1', 'tag2'])

    def test_markdown_content_combines_keywords_and_tags(self):
        content = Content.from_markdown(dedent('''\
            ---
            title: title
            keywords:
              - tag1
              - tag2
            tags:
              - tag2
              - tag3
            ---
        '''))

        self.assertEqual(content.tags, ['tag1', 'tag2', 'tag2', 'tag3'])

    def test_markdown_content_defaults_missing_lang(self):
        content = Content.from_markdown(dedent('''\
            ---
            title: title
            ---
        '''))

        self.assertIsNone(content.lang)

    def test_markdown_content_requires_string_lang(self):
        with self.assertRaises(exc.InvalidMarkdownLanguage) as caught:
            Content.from_markdown(dedent('''\
                ---
                title: title
                lang: 42
                ---
            '''))

        self.assertEqual(caught.exception.value, 42)

    def test_markdown_content_rejects_invalid_titles(self):
        front_matter_cases = ('lang: en', "title: ''", "title: '   '", 'title: 1')
        for front_matter in front_matter_cases:
            with self.subTest(front_matter=front_matter):
                with self.assertRaises(exc.InvalidContentTitle):
                    Content.from_markdown(f'---\n{front_matter}\n---')

    def test_markdown_content_rejects_invalid_front_matter(self):
        with self.assertRaises(yaml.YAMLError):
            Content.from_markdown(dedent('''\
                ---
                title: [
                ---
            '''))

    def test_markdown_content_rejects_non_mapping_front_matter(self):
        with self.assertRaises(exc.InvalidMarkdownFrontMatterType):
            Content.from_markdown(dedent('''\
                ---
                - title
                ---
            '''))

    def test_markdown_content_rejects_invalid_tags(self):
        cases = (
            ('keywords: tag', 'keywords', 'tag'),
            ('tags: tag', 'tags', 'tag'),
            ('tags:\n  - tag\n  - 1', 'tags', ['tag', 1]),
        )
        for fields, expected_field, expected_value in cases:
            with self.subTest(field=expected_field, value=expected_value):
                markdown = f'---\ntitle: title\n{fields}\n---'
                with self.assertRaises(exc.InvalidMarkdownTags) as caught:
                    Content.from_markdown(markdown)

                self.assertEqual(caught.exception.field, expected_field)
                self.assertEqual(caught.exception.value, expected_value)
