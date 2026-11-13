---
name: frontend-auth
description: Use when building or reviewing the client-side side of authentication — where the session lives, protected-route/redirect flow, and logout. Not the server-side auth mechanism itself (project-profile.md's Backend → Auth row covers session-based/JWT/OAuth2/SSO) and not the XSS boundary in general (frontend-security), though this skill leans on it directly.
---

# Auth / session handling (frontend)

Governs `project-profile.md` fields: Frontend → Auth / session handling (frontend).

Scope: the client side of being logged in — where the session credential
actually lives in the browser, what happens when a logged-out user hits
a protected view, and what logout actually clears. Distinct from
section 4's backend "Auth" row, which is the server-side mechanism a
custom backend implements; a project with no custom backend (a BaaS
like Supabase/Firebase, or no accounts at all) still has this row to
answer.

## Where the session credential lives

- **Default, when a custom backend exists**: the backend sets the
  session credential as an `HttpOnly`, `Secure`, `SameSite=Strict` (or
  `Lax`) cookie — the browser never exposes it to JavaScript, so an XSS
  payload (`frontend-security`'s own concern) cannot read or exfiltrate
  it. `localStorage` is the wrong default: any script running on the
  page, including an injected one, can read it outright.
- **A short-lived access token in memory + a refresh token in an
  `HttpOnly` cookie** is the common hybrid for an SPA talking to an
  OAuth/OIDC provider directly — accept that the in-memory token is
  lost on reload and the app must silently re-acquire it via the
  refresh cookie, rather than treating that reload behavior as a bug.
- **A BaaS's own SDK (Supabase, Firebase) decides this for you** — most
  ship a client library that manages its own storage, and it is common
  for that default to be `localStorage`, not a cookie. Don't treat this
  as a skill failure to silently work around with no backend of your
  own: changing it genuinely requires adding a server component (an
  Edge Function acting as a backend-for-frontend) most solo/small
  projects don't have reason to add. Record the BaaS's actual default
  honestly in the profile row, and treat it as a reason to be stricter,
  not looser, about `frontend-security`'s XSS audit for that project —
  the tradeoff is accepted for the simplicity of no custom backend, not
  ignored. `my-world` is the worked example: Supabase's JS client stores
  its session in the browser's own storage; there's no custom backend
  to put an `HttpOnly` cookie in front of it.

## Protected routes

A client-side route guard (redirect an unauthenticated visitor away from
a protected view) is a **UX convenience, not the security boundary** —
whatever actually serves the protected data (a custom backend, or the
BaaS's own row-level security / rules) must independently refuse an
unauthenticated request; a guard that's bypassed (direct API call, a
modified request) must not be able to read or write anything. Preserve
the originally-requested destination through the login-redirect flow
(send the user back to what they were trying to reach, not just to
home) — this is `frontend-routing`'s concern at the point login
succeeds, not a separate mechanism.

## Logout

Clear the session credential *and* any client-side cached data derived
from it (cached queries, in-memory state scoped to that user) — leaving
stale cached data visible after logout is a real, user-visible privacy
bug on a shared device, not just a cosmetic inconsistency.

## Basis (checked 2026-11-13)

- `HttpOnly` + `Secure` + `SameSite` cookies are the practitioner
  consensus for session credentials over `localStorage`, specifically
  because `localStorage` is readable by any script on the page
  including an XSS-injected one; a short-lived in-memory access token
  plus an `HttpOnly` refresh cookie is a common SPA/OIDC hybrid:
  [Where should browser apps store OIDC tokens?](https://oneuptime.com/blog/post/2026-08-10-oidc-browser-token-storage-bff/markdown),
  [Token storage security checklist](https://frontendchecklist.io/rules/security/token-storage-security).
- Client-side route guards only control UI visibility; the server (or
  BaaS rules) must independently validate every request — noted as the
  practical implication across the same sources above, consistent with
  this framework's existing "the UI boundary is not the security
  boundary" stance in `frontend-security`.
