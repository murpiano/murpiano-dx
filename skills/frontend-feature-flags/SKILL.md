---
name: frontend-feature-flags
description: Use when a project needs to ship behind a flag, run an A/B test, or have a kill switch for a feature — whether a tool is needed at all, and which one. Not for analytics in general (frontend-analytics), even though some tools combine both.
---

# Feature flags / experimentation

Governs `project-profile.md` fields: Constraints & non-functional
requirements → Feature flags / experimentation (ask explicitly — see project-profile/SKILL.md).

Scope: a project that needs to turn a feature on/off, or for some users
and not others, without a full redeploy, or needs to run a real
experiment with bucketed users. "None" is correct and complete for a
project that just ships when a feature is ready — don't add flag
infrastructure speculatively for a toggle a redeploy already handles
fine.

## Default: a hand-rolled flag, not a service, until the need outgrows it

For a solo/small project whose actual need is "turn this one thing on
or off, I control the deploy": a plain constant (an object/module
exporting booleans, or an environment variable read at build time) is
the right default — no dependency, no account, no runtime network call
for something a redeploy already solves. Reaching for a flag *service*
before the need is real adds an external dependency and an account to
manage for a problem a single file solves.

**The actual trigger to add a service** is one of:

- Multiple people need to toggle something without a developer
  redeploying.
- A flag needs to vary per-user or per-segment (a real experiment, a
  gradual percentage rollout) — a hand-rolled constant can't bucket
  users.
- The flag needs to change without a deploy at all (an incident kill
  switch flipped at 2am with no code change available).

## Tool choice, once the trigger is real

- **Already using PostHog for analytics?** Its feature-flag product is
  the default add — one tool, one bill, and flags can target by the
  same user properties the analytics already tracks. Pay-per-request
  pricing with a sizeable free tier.
- **Self-hosting matters, or no analytics tool is involved**:
  **Unleash** (open-source, self-hostable) — a generous free tier makes
  it workable for an individual/small team without recurring cost.
  **ConfigCat** is the stated alternative for a small team that wants
  a hosted, predictably-priced option with minimal setup instead of
  running infrastructure.
- **LaunchDarkly is an enterprise-tier choice**, not a default here —
  its governance/audit features matter at an organizational scale this
  framework's typical solo/small-team project isn't at; it is also
  the most expensive of the options above for a small team.

## Basis (checked 2026-11-13)

- The common framing across 2026 feature-flag tool comparisons: a
  small team with simple needs fits a lightweight/predictable-pricing
  tool (ConfigCat) or a self-hosted option (Unleash) better than an
  enterprise platform; LaunchDarkly is consistently described as the
  enterprise/battle-tested choice that becomes expensive for a small
  team; PostHog is repeatedly recommended when a team already uses it
  for analytics, since it removes the need for a second tool:
  [Best feature flag tools, 2026](https://dupple.com/learn/best-feature-flag-tools),
  [PostHog vs. LaunchDarkly](https://posthog.com/blog/posthog-vs-launchdarkly.md).
