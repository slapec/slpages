from dataclasses import dataclass
from typing import Self, TypedDict

import bs4
import markdown_it
import yaml
from mdit_py_plugins.front_matter import front_matter_plugin

from slpages import exceptions as exc


TAG_KEYS = ('keywords', 'tags')


class ContentDict(TypedDict):
    title: str
    body: str
    lang: str | None
    tags: list[str]


@dataclass
class Content:
    title: str
    body: str
    lang: str | None
    tags: list[str]

    def as_dict(self) -> ContentDict:
        return {
            'title': self.title,
            'body': self.body,
            'lang': self.lang,
            'tags': list(self.tags),
        }

    @staticmethod
    def _require_title(title: object) -> str:
        if not isinstance(title, str) or not title.strip():
            raise exc.InvalidContentTitle(title)

        return title

    @classmethod
    def from_html(cls, html: str) -> Self:
        soup = bs4.BeautifulSoup(html, features='html.parser')

        html_elem = soup.find('html', recursive=False)
        if html_elem is None:
            raise exc.MissingHtmlElement('html')

        def get(name: str, root: bs4.BeautifulSoup | bs4.Tag = html_elem) -> bs4.Tag:
            elem = root.find(name, recursive=False)
            if elem is None:
                raise exc.MissingHtmlElement(name)
            return elem

        head_elem = get('head')
        title_elem = get('title', head_elem)
        body_elem = get('body')

        tags: list[str] = []

        for meta_elem in head_elem.find_all('meta'):
            if meta_elem.get('name') not in TAG_KEYS:
                continue

            tag_content = meta_elem.get('content')
            if not isinstance(tag_content, str):
                continue

            tags.extend(part.strip() for part in tag_content.split(','))

        lang = html_elem.get('lang')
        if not isinstance(lang, str):
            lang = None

        return cls(
            title=cls._require_title(title_elem.decode_contents()),
            body=body_elem.decode_contents(),
            lang=lang,
            tags=tags,
        )

    @classmethod
    def from_markdown(cls, markdown: str) -> Self:
        md_parser = markdown_it.MarkdownIt().use(front_matter_plugin)
        md_tokens = md_parser.parse(markdown)
        front_matter_raw = None
        content_tokens = []

        for md_token in md_tokens:
            if md_token.type == 'front_matter':
                if front_matter_raw is None:
                    front_matter_raw = md_token.content
                continue

            content_tokens.append(md_token)

        front_matter = yaml.safe_load(front_matter_raw or '')

        if front_matter is None:
            front_matter = {}

        if not isinstance(front_matter, dict):
            raise exc.InvalidMarkdownFrontMatterType(front_matter)

        tags: list[str] = []

        for key in TAG_KEYS:
            tag_values = front_matter.get(key)
            if tag_values is None:
                continue

            if not isinstance(tag_values, list) or not all(isinstance(value, str) for value in tag_values):
                raise exc.InvalidMarkdownTags(key, tag_values)

            tags.extend(value.strip() for value in tag_values)

        lang = front_matter.get('lang')
        if lang is not None and not isinstance(lang, str):
            raise exc.InvalidMarkdownLanguage(lang)

        return cls(
            title=cls._require_title(front_matter.get('title')),
            body=md_parser.renderer.render(
                content_tokens,
                md_parser.options,
                {},
            ),
            lang=lang,
            tags=tags,
        )
