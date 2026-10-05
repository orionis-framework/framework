# Orionis · Pydoctor theme

Reusable theme for the Orionis API reference. It extends the `base` theme through
`--template-dir`; it does not modify generated HTML afterward or Pydoctor's
installed files. Verified with Pydoctor **25.10.1**.

## Generate the documentation

From the repository root, with `uv` installed:

```powershell
.\DOCS.ps1
```

The output is written to `docs/index.html`. The script installs the `docs` group
dependencies through `uv`, reads the version from `pyproject.toml`, and links the
source code to the current Git revision. It can be invoked from another directory
and restores the original working directory when it finishes.

Generation starts from scratch in `.docs-build-<id>/site`. The indexes, search,
and inventory are validated before replacing the previous output. **All previous
contents of `docs` are replaced**, including any files or folders unrelated to
the generated documentation. If publication fails, the script attempts to restore
the previous output. At the end, including after a failed generation, the script
removes the `.docs-build-*` temporary directories directly under the repository
root, including leftovers from previous runs. Diagnostics remain in the console;
redirect output to a log file if you need to keep them.

- Exit code `0`: documentation generated successfully.
- Exit code `2`: Pydoctor finished with docstring-parsing or AST errors. If all
  main artifacts exist, the output is published, a warning is shown, and exit code
  `2` is preserved for CI. Check the log: some text or objects may be incomplete.
- Exit code `1`: generation, validation, publication, or temporary cleanup failed.

To use search, serve the documentation over HTTP; browsers restrict loading its
indexes when opening a file through `file://`:

```powershell
uv run python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Open <http://127.0.0.1:8000/>. `Ctrl+C` stops the server. The site uses local
assets; it needs no Google Fonts, CDN, or frontend build process.

## Structure

```text
resources/docs/pydoctor/
├── README.md
└── templates/
    ├── extra.css           # Tokens, layout, responsive behavior, and printing
    ├── head.html           # Stylesheets, scripts, favicon, and viewport
    ├── header.html         # Branding and global controls
    ├── subheader.html      # Breadcrumb and landing page
    ├── footer.html         # Metadata and original search scripts
    ├── orionis-theme.js    # Applies color preference before CSS
    ├── orionis-ui.js       # Navigation, shortcuts, and example copying
    ├── orionis-icon.svg
    └── orionis-fonts/      # Titillium Web, Fira Code, and OFL licenses
```

## Customization and reuse

The `extra.css` tokens follow Orionis branding: blue `#206bc4`, navy `#082b52`,
cyan `#66d5f4`, gold `#f5ca37`, and Titillium Web. Fira Code is used for
signatures and examples. Adjust `:root` and `html[data-theme='dark']` to change
colors, surfaces, borders, and fonts without editing the templates.

The initial mode follows the system preference, and the button saves the choice
in `localStorage` under `orionis-api-theme`. Mobile navigation appears at widths
up to 760 px; if you change that breakpoint, update both the CSS and
`orionis-ui.js`. The `/`, `Ctrl+K`, and `Cmd+K` shortcuts focus search when the
user is not in an editing field; `Escape` closes the results or mobile navigation.
Examples can be copied, with manual selection as a fallback if the browser does
not support clipboard access.

The main configuration lives in `[tool.pydoctor]` in `pyproject.toml`. To reuse
the theme in another repository, copy this folder and configure:

```toml
[tool.pydoctor]
project-name = "My project"
add-package = ["my_package"]
html-output = "docs/api"
theme = "base"
template-dir = ["resources/docs/pydoctor/templates"]
docformat = "numpy"
sidebar-expand-depth = 2
sidebar-toc-depth = 3
use-hardlinks = true
```

Then run `uv run --group docs pydoctor`. Adapt the branding, links, and text in
`header.html`, `subheader.html`, and `footer.html`. The landing page is enabled
for `index.html`, `orionis.html`, or a directory URL; adjust detection in
`orionis-theme.js` if your root uses another name. The docstring format and
visibility policy should match the target project. Orionis retains `PUBLIC:**`,
as its previous script did.

## Maintenance

The `head.html` and `footer.html` templates declare version **3** of their
Pydoctor 25.10.1 counterparts. `header.html` and `subheader.html` are unversioned
extension points. When upgrading Pydoctor, check template warnings and review the
landing page, a class with long signatures, indexes, search, mobile layout, and
both color modes. Pydoctor's navigation, renderers, and search engine are retained.

The icon comes from `orionis/metadata/icon.svg`; Titillium Web comes from
`storage/app/public/fonts/titillium-web`, and Fira Code from
`orionis/http/default/assets/fonts`. Copies inside the theme let you move it
without depending on those paths. Preserve the OFL licenses when redistributing
the fonts.

References: [official customization guide](https://pydoctor.readthedocs.io/en/latest/customize.html)
and [Pydoctor configuration](https://pydoctor.readthedocs.io/en/latest/help.html).
