# Sharing & Visibility — Design

**Sub-project 1 of 4** (Sharing/visibility → Friends → Likes → Comments). This spec covers only sharing/visibility. Friends-level privacy, likes, and comments are out of scope here and land in later specs.

## Goal

Let an account holder mark any trip, album, or photo as visible beyond themselves, at one of several privacy levels, independently per item. Other people — anonymous visitors, other registered accounts, or holders of a share link — can then view that content read-only, without ever gaining write access or seeing anything the owner did not explicitly open.

## Context

The app currently has no cross-account visibility at all. Each account's archive is a single JSON document in `public.archives`, keyed by `user_id`, readable and writable only by its owner (RLS: `auth.uid() = user_id`). Photos live in a private Storage bucket (`photos`), under `<user_id>/<photo_id>`, with the same owner-only RLS. Nothing in the schema or the app lets one account see another's data.

The archive's internal shape (`src/data/types.ts`): `ArchiveData` holds `countries` (nested `cities` → `albums`) and `trips` (each `Trip.albumIds` points at album ids that live under some city). An album's `id` is unique within an archive; that id is what this design keys visibility on — not a path through countries/cities, since a city/country is not a privacy-bearing unit on its own.

## Privacy levels

Four levels, independently settable on a trip, an album, or a photo:

- `private` — owner only. Default for everything, always.
- `link` — anyone holding the generated link, no account needed.
- `registered` — any logged-in account on the platform.
- `public` — anyone, no login needed.

(A fifth level, `friends`, is added by the Friends sub-project. This design's schema and functions are written so adding it later is a new `check` value and a new branch in `can_view`, not a schema change.)

**Independence and inheritance:** each item's level is set on that item alone. There is no cascading default from trip to album to photo. But when *deciding whether a viewer may see an item*, the strictest level among the item and all its ancestors wins: a `public` album inside a `private` trip is not reachable, because the trip itself blocks the path to it. A `public` trip containing a `private` album shows the trip but not that album. This matches how the account holder already thinks about nesting (hide the whole trip vs. hide one embarrassing album inside an otherwise-open trip).

**Default:** every trip, album, and photo is `private` until the owner changes it — nothing becomes visible by creating it.

## Data model

One new table. `public.archives` and the `photos` bucket are unchanged.

```sql
create table public.content_visibility (
  id          uuid primary key default gen_random_uuid(),
  owner_id    uuid not null references auth.users(id) on delete cascade,
  kind        text not null check (kind in ('trip', 'album', 'photo')),
  item_id     text not null,
  level       text not null default 'private'
              check (level in ('private', 'link', 'registered', 'public')),
  link_token  uuid,
  updated_at  timestamptz not null default now(),
  unique (owner_id, kind, item_id)
);

alter table public.content_visibility enable row level security;

create policy "visibility: read own" on public.content_visibility
  for select using (auth.uid() = owner_id);
create policy "visibility: write own" on public.content_visibility
  for insert with check (auth.uid() = owner_id);
create policy "visibility: update own" on public.content_visibility
  for update using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "visibility: delete own" on public.content_visibility
  for delete using (auth.uid() = owner_id);
```

A row only exists once the owner sets something non-default; an item with no row is `private` (the schema default covers a row that exists with no explicit level, but the common case is simply no row — absence also means private).

`item_id` is `text`, not a foreign key, because the archive is an opaque JSON blob — there is no `trips`/`albums`/`photos` table to reference. `item_id` is the same id already used inside the JSON (`Trip.id`, `AlbumData.id`, the `id` on an `own`-kind `PhotoRef`).

This table is also the anchor the Likes and Comments sub-projects attach to (`content_visibility.id`, or a lighter `(owner_id, kind, item_id)` tuple) — reusing it there avoids a second table with the same shape, but that reuse is decided when that spec is written, not here.

### Ancestor lookup

`can_view` needs to walk from a photo or album up to its album/trip to apply "strictest ancestor wins." Because the archive is JSON, this walk happens inside SQL using `jsonb` path functions reading `public.archives.data` for that `owner_id` — not a second index table. A `security definer` helper resolves an item's ancestor chain:

```sql
create or replace function public.visibility_ancestors(p_owner uuid, p_kind text, p_item_id text)
returns table(kind text, item_id text)
language sql security definer stable as $$
  -- photo -> its album -> that album's trip (if any); album -> its trip; trip -> itself.
  -- Implementation walks archives.data for p_owner to find the containing album id
  -- for a photo, and the containing trip id for an album, returning each level
  -- from the item itself up to the trip.
$$;
```

(Exact `jsonb` traversal is an implementation-plan concern, not a design concern — the contract is: given any item, return itself plus every ancestor, each as `(kind, item_id)`, in order from the item up.)

### `can_view`

```sql
create or replace function public.can_view(
  p_owner uuid, p_kind text, p_item_id text, p_token uuid default null
) returns boolean
language sql security definer stable as $$
  select p_owner = auth.uid()  -- owner always sees their own
    or not exists (
      select 1 from public.visibility_ancestors(p_owner, p_kind, p_item_id) a
      join public.content_visibility cv
        on cv.owner_id = p_owner and cv.kind = a.kind and cv.item_id = a.item_id
      where cv.level = 'private'
         or (cv.level = 'link' and (p_token is null or cv.link_token is distinct from p_token))
         or (cv.level = 'registered' and auth.uid() is null)
    );
$$;
```

Reading it: walk every ancestor (including the item itself); if *any* ancestor's row blocks this viewer, the item is not visible. An ancestor with no row is `private` by default, so the `exists` check treats a missing row as if `level = 'private'` — the function's actual SQL handles the "row absent" case as blocking, via a `left join` plus `coalesce(cv.level, 'private')`, not shown above for brevity; the implementation plan writes this out in full and tests it directly, since it's the security-critical piece.

## Access paths

**Revised during planning:** a plain Storage RLS policy cannot validate `link_token`. RLS sees only the object path (`owner_id/photo_id`) and the caller's JWT; a link token arrives as a query param or request body on a stateless REST call, which never reaches a `using` clause. Worse, `item_id` values come from `freshId()` (`src/data/edits.ts`), which mixes a timestamp with `Math.random()` — not cryptographically opaque — so "the id itself is the secret" (the fallback a pure-RLS design would lean on) does not hold either. All non-owner reads, archive JSON and photos alike, go through one **Edge Function** instead.

**`supabase/functions/shared-content/index.ts`** — the single entry point for every non-owner read:

- Input: `{ owner_id, kind, item_id, token? }`.
- Runs with the service-role key (server-side only, never shipped to the client).
- Calls `can_view(owner_id, kind, item_id, token)` (same SQL function as before — still the one place the visibility rule lives) to authorize.
- Not authorized → returns `404` with a flat, non-descriptive body (see Error handling — never distinguishes "private" from "does not exist").
- Authorized and `kind` is `trip` or `album` → reads the owner's `archives.data`, extracts that subtree, drops any nested photo whose own `can_view` check fails, then — for every remaining `own`-kind photo — mints a signed URL via the Storage admin API (`createSignedUrl`, service role bypasses RLS entirely for this server-side call) and inlines it on the photo, so the client never talks to Storage directly for shared content.
- Authorized and `kind` is `photo` → returns just that photo's signed URL.
- A second function, **`supabase/functions/public-trips/index.ts`**, takes `{ owner_id, viewer_registered }` and returns the trip summaries at `public` level, plus `registered` ones when `viewer_registered` is true (the caller passes this from whether the browser has a session, not from the payload of an easily-forged param — the function re-derives it from the caller's own JWT via `req.headers.get('Authorization')`, falling back to anonymous when absent).

`can_view` and `visibility_ancestors` stay exactly as designed above; only *who calls them* changes — a Postgres function invoked from an Edge Function using the service-role client, not from RLS or a client-callable RPC. `content_visibility`'s RLS (owner-only read/write) is unchanged and still governs the *owner's own* reads/writes of their privacy settings from the normal app.

The `photos` bucket's RLS is untouched (still owner-only, as today) — the Edge Function reads it with the service-role key, which RLS does not apply to.

## Public handle & profile

Each account gets a URL-safe handle, separate from email. Generated at signup from the account's name (`ivan-petrov`; `-2`, `-3`, ... appended on collision), stored in `auth.user.user_metadata.handle` alongside the existing `name`/`home`, editable later from `AccountForm.tsx` the same way name/home are today (with a uniqueness check on save).

`/u/<handle>` resolves the handle to a `user_id` (a small `handle -> user_id` lookup, either a public-readable column on a minimal profiles table or a security-definer RPC — implementation plan decides which, since it's a small, low-risk choice either way) and then calls the `public-trips` Edge Function.

## Routing

The app has no client-side router today — `App.tsx` renders one of Splash/Stage/Header based on boot state, nothing reads the URL. Two new paths are needed:

- `/u/<handle>` — public profile.
- `/shared/<owner_id>/<kind>/<item_id>?t=<token>` — direct view of one trip/album/photo.

Given there are only two routes and the app deliberately carries no router dependency (see `package.json` — React, D3, Supabase, no routing library), this reads `window.location.pathname` once at boot and branches before the existing Splash/Stage flow mounts, instead of pulling in a router for two paths.

The app deploys to GitHub Pages under `/my-world/` (`deploy.yml`, `VITE_BASE: /my-world/`), which serves static files with no server-side rewrite — a direct load of `/my-world/u/ivan-petrov` 404s today. This needs the standard GitHub Pages SPA fallback: a `404.html` that redirects to `index.html` with the original path preserved (as a query param, restored via `history.replaceState` once `index.html` loads), added as part of this sub-project since the new routes are the first thing that needs it.

## UI components

- **Privacy control** on a trip card, an album view, and a photo — a 4-way picker (private/link/registered/public). Writes directly to `content_visibility` via a small upsert, independent of the main archive save-queue (`RemoteRepository`'s queued JSON save is unrelated and unaffected).
- **Copy-link button**, shown when level is `link` — generates `link_token` if absent, builds `/shared/<owner_id>/<kind>/<item_id>?t=<token>`, copies to clipboard.
- **Shared view** (`/shared/...` and `/u/<handle>`) — reuses the existing Trip/Album presentational components in a read-only mode (no edit affordances, no upload). A new `sharedRepository` (same `Repository` interface as `demoRepository`/`localRepository`/`remoteRepository`, `editable: false`) feeds `World` from the `shared-content`/`public-trips` Edge Functions instead of the local/remote backend — it slots into the exact seam `loadWorld` already uses to pick a repository (`src/app/boot.ts`).

## Error handling

- Token revoked, item set back to `private`, or viewer lacks rights → the `shared-content` Edge Function returns `404` with no distinguishing detail. The UI shows one neutral "not available" state — never a reason, so a private item's existence isn't confirmed or denied by the error text.
- `registered`-level content viewed while logged out → same neutral state, with a sign-in prompt (distinct from the flat "not available" for a private/revoked item, since here the fix is actionable).
- Malformed handle or share URL → same "not available" page.

## Testing

- **API tests** (same style as the existing archive/photo RLS tests, two accounts, extended to call the Edge Functions): a stranger cannot read a `private` item via `shared-content`; a `link` item is readable with its token and not with none/a wrong one; a `registered` item is blocked for an anonymous request and allowed for a second logged-in account; a `public` item is readable anonymously; strictest-ancestor-wins is exercised directly (`public` album inside `private` trip → blocked; `private` photo inside `public` album → album visible, that photo excluded from the returned payload).
- **E2E**: owner sets an album to `public`, a second browser with no session opens `/u/<handle>`, sees the profile list, opens the album, sees its photos; owner reverts to `private`, the same URL now shows "not available."

## Review Focus

- Revoking a `link` token (owner regenerates or sets back to `private`) must invalidate the old link immediately — tested above via the "wrong/old token" case.
- A viewer logged in as a *different* registered account must not see `private` or mismatched-`link` content just by virtue of being authenticated — covered by the two-account API tests.
- An ancestor row that doesn't exist (owner never touched visibility on the trip, only on the album) must still default to blocking, not silently allow — called out explicitly in `can_view`'s coalesce-to-`private` behavior and needs its own test (album set `public`, trip never touched → still blocked, since a never-touched trip is `private` by default).
- GitHub Pages direct load of a share URL (not a client-side navigation) must not 404 — covered by the `404.html` fallback, needs a build-output check that `404.html` exists and redirects correctly.
- A `photo`-kind item's own `link`/`public` setting, independent of its album, must be individually shareable even when its album is `private` — the strictest-ancestor rule only looks at the photo's *trip*-through-*album* ancestors, not siblings, so this is already implied by the model but worth a direct test (photo `public`, its album `private` → per the independence rule this is blocked, since the album is an ancestor of the photo; this is the one place the spec's two rules — independent settings, but strictest-ancestor-wins — could read as contradictory, so it's called out here: independence means you *can* set a photo to `public` even while its album is `private`, but visibility still requires every ancestor to allow it too, so that photo stays unreachable until the album is opened at least to `link`. This is the intended, stated behavior from the clarifying question, not a bug.).
