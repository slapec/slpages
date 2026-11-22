import inspect
import logging
import posixpath
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, TypeAlias, cast

import jinja2

from slpages import exceptions as exc
from slpages.content import Content
from slpages.target import FileSystem, Target


log = logging.getLogger(__name__)


@dataclass
class Url:
    path: str
    output_path: str
    params: Mapping[str, object]

    def __getitem__(self, name: str) -> object:
        return self.params[name]

    def __str__(self) -> str:
        return self.path


ViewContent: TypeAlias = str | bytes | Path
ParameterizedViewResult: TypeAlias = tuple[ViewContent, Url]
ViewResult: TypeAlias = ViewContent | ParameterizedViewResult | Iterable[ParameterizedViewResult]
View: TypeAlias = Callable[..., ViewResult]
Route: TypeAlias = Callable[..., Url]
ContentParser: TypeAlias = Callable[[str], Content]


class Template(jinja2.Template):
    def render(self, *args: Any, **kwargs: Any) -> str:
        template_context: dict[str, object] = dict(self.globals['site'].context)
        template_context.update(dict(*args, **kwargs))
        return super().render(template_context)


class ViewDescriptor(NamedTuple):
    registered_path: str
    view: View
    route_args: tuple[Route, ...]
    is_parameterized: bool


class Site:
    def __init__(
        self,
        src_dir: str | Path,
        context: Mapping[str, object] | None = None,
        path_prefix: str = '',
    ) -> None:
        self.src_dir = Path(src_dir)

        self.context: Mapping[str, object]
        if context is None:
            self.context = {}
        else:
            self.context = context

        normalized_path_prefix = path_prefix.strip('/')
        if normalized_path_prefix:
            self.path_prefix = f'/{normalized_path_prefix}'
        else:
            self.path_prefix = ''

        self.env = jinja2.Environment(
            autoescape=False,
            loader=jinja2.FileSystemLoader(self.src_dir),
            undefined=jinja2.StrictUndefined,
        )

        self.env.globals['site'] = self
        self.env.globals['url'] = self.url
        self.env.template_class = Template

        self._view_descriptors: list[ViewDescriptor] = []
        self._name_to_route: dict[str, Route] = {}

    def _make_route(self, path: str) -> tuple[Route, bool]:
        literal_path = re.sub(r'{[^{}]*}', '', path)
        if '{' in literal_path or '}' in literal_path:
            raise exc.InvalidRoutePattern(path)

        parameter_names: dict[str, None] = {}
        for parameter_name in re.findall(r'{([^{}]*)}', path):
            if parameter_name in parameter_names:
                log.warning('Duplicate route parameter %r in route %r', parameter_name, path)
            parameter_names[parameter_name] = None
        parameter_count = len(parameter_names)

        def route(*args: object, **kwargs: object) -> Url:
            if len(args) > parameter_count:
                raise exc.TooManyRouteParameters(parameter_count, len(args))

            route_parameters = dict(zip(parameter_names, args))
            for parameter_name, value in kwargs.items():
                if parameter_name not in parameter_names:
                    raise exc.UnknownRouteParameter(parameter_name)

                if parameter_name in route_parameters:
                    log.warning(
                        'Route parameter %r was provided more than once; the keyword value will be used',
                        parameter_name,
                    )
                route_parameters[parameter_name] = value

            if len(route_parameters) != parameter_count:
                missing_parameter_names = parameter_names.keys() - route_parameters.keys()
                raise exc.MissingRouteParameters(list(missing_parameter_names))

            formatted_path = path.format(**route_parameters)
            public_path = f'{self.path_prefix}/{formatted_path.lstrip("/")}'

            return Url(public_path, formatted_path, route_parameters)

        return route, bool(parameter_names)

    def __call__(self, path: str, name: str | None = None) -> Callable[[View], View]:
        if name is None:
            name = path

        def decorator(view: View) -> View:
            if name in self._name_to_route:
                log.warning('Duplicate route name %r; the later route will be used for URL generation', name)

            route, is_parameterized = self._make_route(path)
            route_args: tuple[Route, ...] = ()
            if inspect.signature(view).parameters:
                route_args = (route, )

            self._view_descriptors.append(ViewDescriptor(
                path, view, route_args, is_parameterized
            ))
            self._name_to_route[name] = route
            return view

        return decorator

    def _view_outputs(
        self,
        view_descriptor: ViewDescriptor,
        view_result: ViewResult,
    ) -> Iterable[tuple[object, str]]:
        if not view_descriptor.is_parameterized:
            yield view_result, view_descriptor.registered_path
            return

        view_results: Iterable[object]
        if isinstance(view_result, tuple):
            if not view_result:
                view_results = ()
            elif isinstance(view_result[0], tuple):
                view_results = view_result
            elif len(view_result) == 2:
                view_results = (view_result,)
            else:
                raise exc.InvalidViewResultTuple(len(view_result))
        elif isinstance(view_result, Iterable) and not isinstance(view_result, ViewContent):
            view_results = view_result
        else:
            raise exc.InvalidParameterizedViewResult(view_result)

        for content_result in view_results:
            if not isinstance(content_result, tuple):
                raise exc.InvalidParameterizedViewResult(content_result)

            if len(content_result) != 2:
                raise exc.InvalidViewResultTuple(len(content_result))

            content, url = content_result
            if not isinstance(url, Url):
                raise exc.InvalidViewUrl(url)

            yield content, url.output_path

    def build(self, output: str | Path | Target) -> None:
        target: Target
        if isinstance(output, (str, Path)):
            target = FileSystem(output)
        else:
            target = output

        written_paths: set[str] = set()
        for view_descriptor in self._view_descriptors:
            view_result = view_descriptor.view(*view_descriptor.route_args)
            for content, output_path in self._view_outputs(
                view_descriptor, view_result
            ):
                if not isinstance(content, ViewContent):
                    raise exc.InvalidViewContent(content)

                if output_path.endswith('/'):
                    raise exc.InvalidOutputPath(output_path)

                output_path = posixpath.normpath(output_path.lstrip('/'))
                if output_path in written_paths:
                    log.warning('Duplicate output path %r; writing the later view result too', output_path)

                if isinstance(content, Path):
                    target.copy(output_path, content)
                else:
                    target.write(output_path, content)

                written_paths.add(output_path)

    def url(self, name: str, /, *args: object, **kwargs: object) -> Url:
        try:
            route = self._name_to_route[name]
        except KeyError:
            raise exc.UnknownRoute(name) from None

        return route(*args, **kwargs)

    def template(self, template: str) -> Template:
        return cast(Template, self.env.get_template(template))

    def content(self, path: str, parser: ContentParser | None = None) -> Content:
        source_root = self.src_dir.resolve()
        source_path = (source_root / path).resolve()
        if not source_path.is_relative_to(source_root):
            raise exc.InvalidContentPath(path)

        if parser is None:
            extension = source_path.suffix.lower()
            if extension == '.html':
                parser = Content.from_html
            elif extension == '.md':
                parser = Content.from_markdown
            else:
                raise exc.UnsupportedContent(source_path.suffix)

        text = source_path.read_text(encoding='utf-8')
        return parser(text)
