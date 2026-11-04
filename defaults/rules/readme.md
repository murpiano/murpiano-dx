# README standard

Describe purpose, installation, usage, configuration, structure, checks, and limits.
Use confirmed facts and runnable commands. Keep agent-only instructions in
`AGENTS.md`. Add CI and Release badges only when their workflows and visibility
requirements are satisfied.

The selected README template is mandatory. Preserve its fixed headings and order,
static text, footer, and links. Replace placeholders with verified project facts.
Follow the template's conditional instructions. The existing README never takes
precedence. Depart only on explicit user instruction. Preserve an existing agent
entry-point notice as the first line; template corrections must not remove it.
Preserve all four footer links, including MIT even without a local LICENSE file.
Do not add separator dots or HTML wrappers to the footer. Keep unrelated
development traces out of public product documentation.

Run `bash <murpiano-dx>/sync.sh check-readme <project>` and fix every failure
before completion, commit, PR, or publication. Review factual accuracy separately.
