![<Name>](docs/screenshot.jpg)

# <Name>

<What it is, in one sentence.> <What it is built on, in one short sentence.>

[![CI](https://github.com/murpiano/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/murpiano/<repo>/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/murpiano/<repo>?color=informational)](https://github.com/murpiano/<repo>/releases/latest)

[Live demo](<url>) · [How it works](#how-it-works) · [Run locally](#run-locally)

<!-- Optional. Only what a visitor must know before clicking the demo:
     cold starts, demo credentials, data that resets. 2-3 sentences. -->
<Warning paragraph.>

## What you can do

<!-- One paragraph, 3-6 sentences. The user's verbs: open, drag, sort, upload, call,
     connect. Concrete limits from the code (sizes, counts, formats).
     Backend, CLI or library: a short real example may follow. -->
<Paragraph.>

<!--
```text
$ curl <real request>
<real response, trimmed to 5-10 lines>
```
-->

## How it works

<!-- 2-6 subsections, different lengths. Each: what was done, why, what it costs.
     Name files in backticks. Headings are plain nouns, not slogans. -->

### <Part of the system>

<2-5 sentences.>

### <Another part>

<2-5 sentences.>

## Run locally

```bash
git clone https://github.com/murpiano/<repo>.git
cd <repo>
npm install

npm run dev       # <what it does>
npm test          # vitest
npm run check     # type check and tests
npm run build     # <what it does>
```

<Runtime requirement, e.g. "Needs Node 22.12 or newer.">

<!-- Environment variables, if any: table with Variable, Default, Purpose. -->

<Where tests live and what they leave untouched. What CI runs and when,
with the path .github/workflows/ci.yml. Deploy in one sentence, if any.>

## Where things live

```text
src/
├── <dir>/        <what is inside, only if not obvious>
└── <dir>/        <...>
```

<1-2 sentences on the rule that organises the tree and where tests live.>

## API

<!-- Backend or frontend with its own backend: endpoints.
     CLI: rename to "## CLI" and show the help output.
     Library: rename to "## Usage" and show 1-3 code examples. -->

Base URL: `<url>`

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| GET | `<path>` | | <what> |

## Rough edges

- <Real limitation, stated as a fact.>
- <Another one.>

---

<sub>Bogdan Trotsenko · [@murpiano](https://github.com/murpiano) · [Telegram](https://t.me/murpiano) · <License></sub>
