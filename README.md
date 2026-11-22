# slpages

slpages is a simple, opinionated static site library and generator for programmers.
It takes a bit of inspiration from FastAPI and Django.

## Installation

slpages requires Python 3.12 or newer. From the root of your local slpages
checkout, install it into your site's virtual environment:

```sh
python -m pip install .
```

## Minimal example

In your site directory, save this as `build.py`:

```python
from slpages.site import Site

site = Site('src', context={'site_name': 'My site'})

@site('index.html', name='home')
def home():
    return site.template('index.html').render()

@site('posts/{slug}.html', name='post')
def post(route):
    page_url = route('hello-world')
    page = site.template('post.html').render(title='Hello, world!')
    return page, page_url


site.build('dist')
```

Any file in the source directory can be a Jinja2 template. You choose the
directory structure. Templates can access the context variables and use the
`url()` helper to link to another view.

Assume this source structure:

```text
src/
├── index.html
└── post.html
```

The contents of `index.html`:

```html
<h1>{{ site_name }}</h1>
<a href="{{ url('post', slug='hello-world') }}">Read the post</a>
```

The contents of `post.html`:

```html
<h1>{{ title }}</h1>
```

Run the script from the directory containing `build.py` and `src/`:

```sh
python build.py
```

The build creates this output:

```text
dist/
├── index.html
└── posts/
    └── hello-world.html
```

`dist/index.html`:

```html
<h1>My site</h1>
<a href="/posts/hello-world.html">Read the post</a>
```

`dist/posts/hello-world.html`:

```html
<h1>Hello, world!</h1>
```

## Views

Views return content that slpages writes to the output:

- Return a `str` to write text, or `bytes` to write binary content.
- Return a `Path` to copy that file to the output.

A simple view returns one content value. A parameterized view returns a
`(content, url)` tuple or an iterable of such tuples. In each tuple, `content`
is a `str`, `bytes`, or `Path`. To get the `Url`, call the route function
that slpages passes to your view, as in `route('hello-world')` above. slpages
writes the content to the output path from that URL.

## Content model

You don't need to use the content model, but it's available for loading
content from Markdown and HTML files.

Markdown files require a title in YAML front matter. For example, in
`src/about.md`:

```markdown
---
title: About me
---

I build small tools in Python.
```

`Site.content()` reads HTML and Markdown files from the source directory and
returns a `Content` object. Pass `content.as_dict()` to a template to render its
title, body, language, and tags:

```python
content = site.content('about.md')
html = site.template('content.html').render(content.as_dict())
```

## URL prefix

If you serve the example site under `/docs`, set the prefix when creating the site:

```python
site = Site('src', context={'site_name': 'My site'}, path_prefix='/docs')
```

The home page now links to `/docs/posts/hello-world.html`. The build writes the
post to `dist/posts/hello-world.html`.
