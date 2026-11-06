<!-- Preserve an existing agent entry-point notice as the first line.
     Default license: MIT. For projects without a license, create LICENSE from
     this skill's templates/LICENSE and fill its year and verified copyright holder.
     Preserve existing licenses unless the user explicitly requests a change.
     Keep the cover only when a real asset exists. Translate section names together
     when the project uses another language.

     Project kind drives which sections below are kept: app, framework, npm-package,
     or personal-brand (a descriptive, non-code page). Pick one kind before editing.
     A section tagged "kind: a, b" is required for those kinds and optional for the
     rest — delete it, along with its comment, for a kind it does not list. An
     untagged section is universal: keep it for every kind. Run
     `check-readme --kind <kind>` so the checker enforces the right set. -->
![<Name>](docs/screenshot.jpg)

# <Name>

<What it is, in one sentence.> <What it is built on, in one short sentence.>

<!-- Only badges that already show a real status: CI if .github/workflows/ci.yml exists,
     Release if releases are on. Neither: drop this block. -->
[![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/<owner>/<repo>?color=informational)](https://github.com/<owner>/<repo>/releases/latest)

<!-- Link only to headings you actually kept below. -->
[<Anchor>](#<anchor>) · [<Anchor>](#<anchor>)

<!-- Optional. Only what a visitor must know before clicking a link above:
     cold starts, demo credentials, data that resets. 2-3 sentences. -->
<Warning paragraph.>

## What you can do
<!-- personal-brand: rename to "## About" and describe who this is and what they
     do, in the same 3-6 sentences. Universal otherwise: keep for every kind. -->

<!-- One paragraph, 3-6 sentences. The user's verbs: open, drag, sort, upload, call,
     connect. Concrete limits from the code (sizes, counts, formats).
     Backend, CLI, or library: a short real example may follow. -->
<Paragraph.>

<!--
```text
$ curl <real request>
<real response, trimmed to 5-10 lines>
```
-->

## How it works
<!-- kind: app, framework. Optional for npm-package (keep only if internals are
     non-obvious); drop for personal-brand. -->

<!-- 2-6 subsections, different lengths. Each: what was done, why, what it costs.
     Name files in backticks. Headings are plain nouns, not slogans. -->

### <Part of the system>

<2-5 sentences.>

### <Another part>

<2-5 sentences.>

## Run locally
<!-- kind: app, framework, npm-package. npm-package: rename to "## Install" — show
     the install command and 1-3 real import/usage snippets instead of a dev-server
     clone+run. Drop for personal-brand. -->

```bash
git clone https://github.com/<owner>/<repo>.git
cd <repo>
npm install

npm run dev       # <what it does>
npm test          # <keep only if package.json has this script>
npm run check     # <keep only if package.json has this script>
npm run build     # <what it does>
```

<Runtime requirement, e.g. "Needs Node 22.12 or newer.">

<!-- Environment variables, if any: table with Variable, Default, Purpose. -->

<Only for what exists: where tests live and what they leave untouched; what CI runs and
when, with the path .github/workflows/ci.yml; deploy in one sentence.>

## Where things live
<!-- kind: app, framework. Optional for npm-package; drop for personal-brand. -->

```text
src/
├── <dir>/        <what is inside, only if not obvious>
└── <dir>/        <...>
```

<1-2 sentences on the rule that organises the tree and where tests live.>

## API
<!-- kind: app, framework, npm-package. CLI tool: rename to "## CLI" and show the
     help output. Library or npm-package: rename to "## Usage" and show 1-3 code
     examples. Drop for personal-brand. -->

Base URL: `<url>`

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| GET | `<path>` | | <what> |

## Rough edges
<!-- kind: app, framework, npm-package. Optional for personal-brand. -->

- <Real limitation, stated as a fact.>
- <Another one.>

---

<sub>[<Your name or handle>](<your-profile-url>) · [<Your org, if any>](<your-org-url>) · [<Contact>](<contact-url>) · [<License>](LICENSE)</sub>
