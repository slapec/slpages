class SLPagesError(Exception):
    category_code: int = 1


class RouteError(SLPagesError):
    category_code: int = 2


class RouteParameterError(RouteError):
    pass


class UnknownRoute(RouteError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(name)

    def __str__(self) -> str:
        return f'Unknown route: {self.name}'


class InvalidRoutePattern(RouteParameterError):
    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(path)

    def __str__(self) -> str:
        return f'Invalid route pattern: {self.path}'


class UnknownRouteParameter(RouteParameterError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(name)

    def __str__(self) -> str:
        return f'Unknown route parameter: {self.name}'


class MissingRouteParameters(RouteParameterError):
    def __init__(self, names: list[str] | tuple[str, ...]) -> None:
        self.names = tuple(names)
        super().__init__(self.names)

    def __str__(self) -> str:
        names = ', '.join(self.names)
        return f'Missing route parameters: {names}'


class TooManyRouteParameters(RouteParameterError):
    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(expected, actual)

    def __str__(self) -> str:
        return f'Too many route parameters: expected at most {self.expected}, got {self.actual}'


class ContentError(SLPagesError):
    category_code: int = 3


class MissingHtmlElement(ContentError):
    def __init__(self, element: str) -> None:
        self.element = element
        super().__init__(element)

    def __str__(self) -> str:
        return f'Missing HTML element: {self.element}'


class InvalidContentTitle(ContentError):
    def __init__(self, title: object) -> None:
        self.title = title
        super().__init__(title)

    def __str__(self) -> str:
        return 'Content title must be a non-empty string'


class InvalidMarkdownFrontMatterType(ContentError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(value)

    def __str__(self) -> str:
        return 'Markdown front matter must be a mapping'


class InvalidMarkdownTags(ContentError):
    def __init__(self, field: str, value: object) -> None:
        self.field = field
        self.value = value
        super().__init__(field, value)

    def __str__(self) -> str:
        return f'Markdown {self.field} must be a list of strings'


class InvalidMarkdownLanguage(ContentError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(value)

    def __str__(self) -> str:
        return 'Markdown lang must be a string'


class UnsupportedContent(ContentError):

    def __init__(self, extension: str) -> None:
        self.extension = extension
        super().__init__(extension)

    def __str__(self) -> str:
        return f'Unsupported content extension: {self.extension}'


class InvalidContentPath(ContentError):
    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(path)

    def __str__(self) -> str:
        return f'Content path must stay within the source directory: {self.path}'


class BuildError(SLPagesError):
    category_code: int = 4


class ViewResultError(BuildError):
    pass


class InvalidViewResultTuple(ViewResultError):
    def __init__(self, size: int) -> None:
        self.size = size
        super().__init__(size)

    def __str__(self) -> str:
        return f'View result tuple must contain content and URL; got {self.size} items'


class InvalidParameterizedViewResult(ViewResultError):
    def __init__(self, result: object) -> None:
        self.result = result
        super().__init__(result)

    def __str__(self) -> str:
        return (
            'Parameterized view must return a (content, Url) tuple or an '
            f'iterable of such tuples; got {type(self.result).__name__}'
        )


class InvalidViewUrl(ViewResultError):
    def __init__(self, url: object) -> None:
        self.url = url
        super().__init__(url)

    def __str__(self) -> str:
        return f'View URL must be Url; got {type(self.url).__name__}'


class InvalidViewContent(ViewResultError):
    def __init__(self, content: object) -> None:
        self.content = content
        super().__init__(content)

    def __str__(self) -> str:
        return f'View content must be str, bytes or Path; got {type(self.content).__name__}'


class OutputError(BuildError):
    pass


class InvalidOutputPath(OutputError):

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(path)

    def __str__(self) -> str:
        return f'Invalid output path: {self.path}'
