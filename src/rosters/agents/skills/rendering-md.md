---
type: skill
description: Converts Markdown documents to polished, standalone HTML and prints HTML to PDF with Chrome. Use when producing readable HTML or PDF deliverables from Markdown while preserving headings, lists, code, links, and print styling.
---

# Rendering Markdown to HTML and PDF

Use the helper tools in `~/.agents/skills/rendering-md-tools/`. They do not open generated files automatically.

## Tools

- `md-to-html.py` converts Markdown into a standalone HTML document.
- `html-to-pdf.mjs` prints an HTML document to PDF with Playwright.
- `render-md.sh` runs both conversions in sequence.
- `document.css` contains the screen and print styling embedded in generated HTML.
- `package.json` declares the Playwright dependency.

The HTML converter embeds `document.css` in the output, so the resulting HTML file is portable and does not depend on a separate stylesheet.

## Environment dependencies

- Python 3
- Python package: `markdown`
- Node.js
- Node package: `playwright` (declared in `rendering-md-tools/package.json`)
- Google Chrome, or a Playwright-installed Chromium browser

## Markdown to HTML

```bash
python ~/.agents/skills/rendering-md-tools/md-to-html.py \
  path/to/document.md \
  path/to/document.html
```

The output path is optional. When omitted, the script replaces the input suffix with `.html`:

```bash
python ~/.agents/skills/rendering-md-tools/md-to-html.py path/to/document.md
```

Useful options:

```bash
# Override the HTML title
python ~/.agents/skills/rendering-md-tools/md-to-html.py input.md output.html \
  --title "Document title"

# Use a different stylesheet
python ~/.agents/skills/rendering-md-tools/md-to-html.py input.md output.html \
  --css path/to/custom.css
```

The converter supports ordinary Markdown plus tables, fenced code blocks, footnotes, definition lists, and sane list handling through Python Markdown's `extra` and `sane_lists` extensions.

## HTML to PDF

```bash
node ~/.agents/skills/rendering-md-tools/html-to-pdf.mjs \
  path/to/document.html \
  path/to/document.pdf
```

The output path is optional. When omitted, the script replaces the input suffix with `.pdf`.

The script:

- loads local HTML using a `file:` URL;
- switches Chrome to print media;
- waits for document fonts to finish loading;
- honors the stylesheet's `@page` rules;
- prints backgrounds and link colors; and
- does not add browser headers or footers.

## Markdown directly to PDF

Use the wrapper when both HTML and PDF are needed:

```bash
~/.agents/skills/rendering-md-tools/render-md.sh path/to/document.md
```

This creates files alongside the input:

```text
document.md
document.html
document.pdf
```

Explicit output paths may also be provided:

```bash
~/.agents/skills/rendering-md-tools/render-md.sh \
  input.md output.html output.pdf
```

## Styling

Edit `~/.agents/skills/rendering-md-tools/document.css` to change future output. It includes:

- a centered reading surface for screen display;
- responsive padding for smaller screens;
- dark-blue headings;
- readable list, link, and inline-code styling;
- US Letter page sizing and print margins;
- print typography and page-break controls; and
- removal of the screen border and shadow when printing.

Because the CSS is embedded during Markdown conversion, changing `document.css` does not alter HTML files already generated. Regenerate the HTML and PDF to apply later CSS changes.

## Quality checks

After rendering, verify:

```bash
file output.html output.pdf
```

Then inspect representative pages for:

- headings stranded at page bottoms;
- long URLs overflowing the page;
- clipped code blocks or tables;
- unexpected blank pages; and
- missing glyphs or fonts.

Do not auto-open outputs unless the user asks.
