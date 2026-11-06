---
name: frontend-project-setup
description: Use when starting a brand-new frontend application from scratch, after stack-selection has already decided the platform (web, Electron, Tauri, React Native, or another native UI platform) — laying down the styling architecture for that platform. Not for adding a feature or component to an already-set-up project. Not for backend/API/database projects.
---

# Guided frontend project setup

Scope: the step-by-step walkthrough for starting a new frontend app. Its
job is to apply framework conventions that are already settled instead of
re-deciding them, and to guide the user through the handful of decisions
that are genuinely new for this project.

## The governing rule

If a convention is already settled in a skill, state it and apply it —
do not ask the user to re-choose something the framework already answered.
Ask only when: the project has a stated reason to deviate, no skill covers
the platform yet, or a better alternative than the settled one is worth
flagging. See `AGENTS.md` → Project rules for this principle framework-wide.

## Step 1 — platform

This skill is reached *after* `stack-selection` has already decided the
application type and language — read its decision, don't re-ask it. If
this skill is somehow entered directly (stack-selection was skipped),
run stack-selection's Step 1 first instead of guessing the platform here.

- Browser/Electron/Tauri → a skill exists (`frontend-web-styles`). Proceed
  to Step 2 stating its conventions directly.
- React Native or another engine → no platform skill exists yet in this
  framework. Say so explicitly, then propose drafting one together
  (mirroring `frontend-web-styles`'s structure: mechanism, token
  consumption, baseline reset, global application point, naming) before
  writing any project code — do not improvise an unwritten convention
  silently.

## Step 2 — state the settled architecture

For a covered platform, state these as already-decided, not as a question:

1. Token source of truth — one file, dark-default + override block (see
   `frontend-styling-concept` rule 1 and the platform skill's token
   template).
2. Style colocation — one style file per component, named after it,
   right next to it (rule 2).
3. Isolation mechanism for this platform (rule 3) — e.g. CSS Modules for
   web.
4. Baseline reset (rule 4) — e.g. `normalize.css` for web, applied once
   before any token or component style.

Only pause for input here if the project has a concrete reason the
default should differ (e.g. an existing brand palette, an existing
component library to integrate with) — ask for that specific input, not
for permission to use the convention itself.

## Step 3 — scaffold in order

Apply the platform skill's templates in the order its own "Applying this
when starting a new project" section gives (baseline reset → tokens →
global application point → first component), confirming each file with
the user before moving to the next rather than dumping the whole
scaffold at once. This keeps the walkthrough legible instead of a wall
of generated files the user never reviewed.

## Step 4 — record anything new

If this project introduces a decision worth keeping for next time (a new
platform's reset rules, a token convention change, a naming rule), that
belongs back in the relevant skill or in `frontend-styling-concept`, not
only in this project's own files — propose the edit to the user so the
next project benefits too, the same way this session's styling
discussion became `frontend-styling-concept` and `frontend-web-styles`.

## What this skill does not cover

Component-by-component styling once the scaffold exists — that is the
platform skill's day-to-day job (`frontend-web-styles` for web). This
skill only runs once, at the start of a project.
