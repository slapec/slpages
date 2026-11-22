# Working on slpages

slpages is a Python 3.12+ static site generator for programmers. A site is a Python program. Its author chooses the files, templates, URLs and output layout. Someone writing a post should be able to open an ordinary HTML or Markdown document in their preferred editor and concentrate on the text. Keep content readable on its own and site-specific decisions visible in the site's Python code.

## Designing the public API

- Start with the code a site author would write. Make the common case convenient: a view can return a string, a file can be copied by returning a `Path`, and `site.build('dist')` is a complete build invocation. More specialized callers can supply a `Target`. Consider the imports, names and intermediate objects a new feature would make every caller remember.
- The FastAPI-inspired `@site(...)` decorator is the one deliberate piece of registration syntax. It registers the view and returns the original function. Use ordinary Python functions, loops, generators and return values for composition. A blog's pagination or asset discovery can live in the blog. Add a library abstraction when concrete call sites demonstrate what it simplifies.
- Keep one way to resolve a route. The callable passed to a view, `site.url(...)` in Python and `url(...)` in Jinja use the same registration. The path itself is the default name. A simple view returns one `str`, `bytes` or `Path`. A parameterized view returns one `(content, Url)` pair or an iterable of pairs. The caller can use the URL while constructing its content and read the original values with `url['slug']`.
- Write the path the author declared. An extensionless route produces an extensionless file. A leading slash starts at the output root. A trailing slash is a directory path and fails the build. The generated link and the output file must agree, accounting for the deployment prefix: `path_prefix='/docs'` makes `about.html` reachable at `/docs/about.html` and leaves it at `about.html` in the output tree. Browser suitability and URL escaping belong to the site author. Keep filesystem reads and writes within their respective roots for `Site.content()` and `FileSystem` destinations.
- Parsing and rendering are separate operations. `site.content(...)` reads source text and selects a parser by extension unless the caller supplies one. Template expressions inside a content body remain content. The explicit bridge is `site.template(...).render(content.as_dict())`. Read the current site context at render time, allow per-render overrides, and preserve the caller's mappings. A missing template variable should surface through Jinja's `StrictUndefined`.
- `slpages/` is intentionally a namespace package so separately distributed extensions can share it. Keep the README pragmatic and in the author's voice. Show working usage whenever the public contract changes.

## Writing code for the next reader

- Aim for a small implementation that can be read from top to bottom. Put imports first, then introduce types, classes and functions close to their first dependent definition. Order tests from the simplest example to the more involved ones. A reader should rarely have to jump around to reconstruct what a value means.
- Use one vocabulary for one concept. Write `for view_descriptor in self._view_descriptors`, name mappings by direction (`_name_to_route`), and use `html_elem`, `head_elem` and `body_elem` consistently. Prefer `Html` and `Url` in class names. Keep useful intermediate variables visible in the debugger.
- Use single-quoted Python strings and allow 120-character lines. Keep a readable expression on one line when it fits. Prefer explicit `if`/`else` assignments when two branches determine a value. Use an ordinary loop for a comprehension that takes work to decipher and a named nested function for a callback. A closure may capture its surrounding state when the binding is clear.
- A helper costs the reader a jump. Inline a one-line private method that only renames an expression. Extract a helper when it removes real duplication or gives a substantial operation a clear boundary. For example, `_view_outputs()` interprets the allowed return shapes, leaving `build()` to copy or write each result. Judge a refactor by reading the resulting caller and helper together.
- Keep the successful path cheap. Construct routes and inspect view signatures at registration time so repeated builds can reuse that work. Compute the names of missing arguments only after detecting a mismatch. When performance decides between two readable implementations, benchmark the specific operation or profile a representative build.
- Run strict mypy on the library. Give a value the most specific honest type. `ContentDict` describes the known fields returned by `Content.as_dict()`, and `ViewDescriptor` names the fields of an internal record. Use a named type when it saves readers from decoding nested annotations or tuple positions.

## Errors and trust

Treat the site author as a competent Python programmer. Validate contracts that slpages owns, such as the shape of a view result or a destination escaping the output root. Preserve informative exceptions from user views, the filesystem, YAML and Jinja. Translate an error when slpages can explain something specific to its own API.

Import library errors with `from slpages import exceptions as exc`. Category classes such as `RouteError` carry a broad `category_code`. Name concrete failures after the condition, for example `MissingRouteParameters`. Pass the relevant values to the exception, expose them as attributes, preserve its constructor arguments and format the message in `__str__`.

When a duplicate has a defined outcome, log a warning and continue. A later registration wins for name lookup, a keyword argument overrides the corresponding positional value, and a later write to the same path still reaches the target. Preserve both the warning and the resulting behavior.

## Testing and collaboration

- For a public API change, begin with a small usage example in the relevant `unittest` suite. Read it as client code before implementing it. If a test fails, establish whether the implementation, the expectation or the fixture is wrong. During design discussions, show the proposed call site and its tradeoffs and wait for an implementation request.
- Test behavior where it belongs. Use `tests/test_views.py` and the in-memory target in `tests/utils.py` for view results. Use `TemporaryDirectory` in `tests/test_target.py` for actual filesystem behavior. An interaction between the two deserves a public-entry-point test: a direct target test alone cannot catch `Site.build()` stripping a trailing slash before it reaches the target.
- Keep parser examples in `tests/test_content.py` and site-level loading and rendering in `tests/test_template.py`. When a method only forwards to another operation, a focused `patch.object` and `assert_called_once_with` can establish the delegation. Test the delegated behavior once at its owner.
- Share a minimal fixture when several cases need the same mechanism. Give a case a dedicated file when its contents matter to the assertion. Combine equivalent inputs with `subTest`, split distinct behaviors, and remove obsolete or redundant cases while preserving meaningful coverage. A test should make clear which regression would turn it red.

From the repository root:

```sh
uv run python -m unittest tests.test_views.TestLowLevelViews.test_simple
uv run python -m unittest discover -s tests
uv run mypy
uv build
```

Use `uv` to regenerate `uv.lock` after dependency changes. Preserve the maintainer's edits when working in a dirty tree.
