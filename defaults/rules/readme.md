# README standard

Describe purpose, installation, usage, configuration, structure, checks, and limits.
Use confirmed facts and runnable commands. Keep agent-only instructions in
`AGENTS.md`. Add CI and Release badges only when their workflows and visibility
requirements are satisfied.

Pick the project kind first — `app`, `framework`, `npm-package`, or
`personal-brand` — and pass it to the checker as `--project-kind`. It decides
which template sections are required versus droppable; see the template's
`kind:` comments.

The selected README template is mandatory. Preserve its fixed headings and order,
static text, footer, and links. Replace placeholders with verified project facts.
Follow the template's conditional instructions, including kind-based renames and
drops. The existing README never takes precedence. Depart only on explicit user
instruction. Preserve an existing agent entry-point notice as the first line;
template corrections must not remove it. Preserve all four footer links, inside
`<sub>` and separated by ` · `, with the license link last. Do not omit the
license link unless the project is `personal-brand` and genuinely has no
`LICENSE` file. Keep unrelated development traces out of public product
documentation.

The distribution template's footer is placeholders only — fill a real identity
there only from your own workspace's template override, never by editing this
shipped default.

Run `bash <murpiano-dx>/sync.sh check-readme <project> --project-kind <kind>` and
fix every failure before completion, commit, PR, or publication. Review factual
accuracy separately.
