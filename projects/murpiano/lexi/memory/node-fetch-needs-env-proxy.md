---
name: node-fetch-needs-env-proxy
description: "User's machine reaches external AI APIs only via local proxy 127.0.0.1:12334; Node fetch needs NODE_USE_ENV_PROXY=1"
metadata: 
  node_type: memory
  type: project
  originSessionId: a35d6117-b227-49cf-b1b0-4a1463a7134b
  modified: 2026-09-14T11:23:42.036Z
---

The user's WSL machine has HTTPS_PROXY=http://127.0.0.1:12334 (VPN client). Direct connections fail: Gemini returns `User location is not supported for the API use.` (400), OpenRouter times out (`UND_ERR_CONNECT_TIMEOUT`). Node's built-in fetch ignores HTTPS_PROXY unless started with `NODE_USE_ENV_PROXY=1`; with it, Gemini (gemini-2.5-flash, OpenAI-compatible endpoint) works with the user's key. Verified 2026-09-14.

**Why:** Synonym suggestions for repeated words call an external chat model from the Next.js server and scripts.

**How to apply:** Keep `NODE_USE_ENV_PROXY=1` in the dev/start/analysis:fill-synonyms npm scripts. When a network call to an external API fails with geo-block or connect timeout, test through the proxy before switching providers. context-mode sandbox and Bash inline HTTP bypass the proxy too — run a node script file with `NODE_USE_ENV_PROXY=1`.
