# Shared regex patterns for scan-traces.sh and pre-commit-hook.sh.
# Source this file; it only sets variables, no side effects.
# Patterns follow policy.md next to this script.

FILES='(^|/)(CLAUDE(\.local)?\.md|AGENTS\.md|GEMINI\.md|\.claude|\.agents|\.codex|\.cursor|\.cursorrules|\.cursorignore|\.windsurf|\.windsurfrules|\.clinerules|\.roo|\.roomodes|\.continue|\.aider[^/]*|\.kiro|\.junie|\.specstory|\.serena|\.superpowers|\.mcp\.json|\.github/copilot-instructions\.md|\.github/instructions|\.github/prompts|memory-bank|docs/superpowers)(/|$)'
TEXT='claude|anthropic|copilot|chatgpt|openai|gpt-[0-9]|gemini|codex|cursor ?ai|co-authored-by|generated (with|by)|ai[- ]generated|as an ai|language model|\bllm\b|🤖'
EMOJI='[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]'
IDENTITY='anthropic|openai|copilot|cursor|codex|\[bot\]'
BRANCH='^(origin/)?(claude|copilot|codex|cursor|devin|jules|gemini|ai|agent)[/-]'
SECRET_FILES='(^|/)(\.env(\.[^/]*)?|[^/]*\.(pem|key|p12|pfx|keystore)|id_(rsa|dsa|ecdsa|ed25519)|\.npmrc|\.netrc|credentials\.json|service-account[^/]*\.json)$'
SECRET_FILES_OK='(^|/)\.env\.(example|sample|template)$'
SECRET_TEXT='-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,}|sk-(ant-|proj-)?[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|(api_?key|secret|token|passw(or)?d)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9_/+.=-]{16,}'
LOCKS=(':!package-lock.json' ':!yarn.lock' ':!pnpm-lock.yaml' ':!bun.lockb')
