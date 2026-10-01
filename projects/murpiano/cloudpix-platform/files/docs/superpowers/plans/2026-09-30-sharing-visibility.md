# Sharing & Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an account holder mark any trip, album, or photo `private`/`link`/`registered`/`public`, independently per item, so someone who is not the owner can view it read-only — via a direct link, a public profile page, or (for `registered`) just by being logged in — without ever touching the owner's write path.

**Architecture:** One new Postgres table (`content_visibility`, owner-only RLS) plus a `profiles` table for public handles, both additive — `archives` and the `photos` bucket are untouched. Two SQL functions (`visibility_ancestors`, `can_view`) encode "strictest ancestor wins." All non-owner reads (archive JSON and photo bytes alike) go through two Edge Functions (`shared-content`, `public-trips`) running with the service-role key, because a plain Storage RLS policy cannot validate a link token on a stateless REST call. A new `Repository` implementation (`sharedRepository`, `editable: false`) feeds the existing `World`/`Stage` machinery from those functions, reusing the exact seam `loadWorld` already uses for `demoRepository`.

**Tech Stack:** Supabase (Postgres, Edge Functions, Storage), TypeScript, React 19, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-30-sharing-visibility-design.md`

## Global Constraints

- Four levels: `private` (default), `link`, `registered`, `public` — set independently per trip/album/photo.
- Strictest level among an item and all its ancestors wins; an ancestor with no row is `private`.
- A denied or nonexistent item returns the same flat "not available" response — never reveals whether something private exists.
- No Storage RLS changes for non-owner access; the `photos` bucket policies from `20260930000000_init.sql` are untouched. All non-owner photo reads go through the `shared-content` Edge Function using the service-role key.
- The app ships no router dependency; two new routes (`/u/<handle>`, `/shared/...`) are handled by reading `window.location.pathname` once at boot.
- Deployed to GitHub Pages under `/my-world/` with no server rewrite — direct loads of the new routes need a `404.html` SPA fallback.

## Review Focus

- A `link` token that was regenerated or reverted to `private` must stop working immediately, including for someone who already had the old link open (Task 1, Task 2).
- A viewer who is logged in as a *different* registered account must not see `private` content, and must not unlock a `link`-level item without the token (Task 1, Task 2).
- An item with no `content_visibility` row at all (owner never touched it) must default to blocked, not silently allowed — this is the one place a coding mistake (e.g. an inner join dropping null rows) would fail open instead of closed (Task 1).
- A direct (non-client-side-navigated) load of `/shared/...` or `/u/<handle>` on the deployed GitHub Pages site must render the page, not a GitHub 404 (Task 8).
- Setting a photo to `public` while its album stays `private` must still hide that photo — independence of settings is not independence of *visibility*, since the album is still an ancestor (Task 1, restated from the spec's Review Focus).

---

### Task 1: Migration — `content_visibility`, `profiles`, and the visibility functions

**Files:**
- Create: `supabase/migrations/20260930010000_visibility.sql`
- Create: `supabase/verify-visibility.mjs`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: table `public.content_visibility(id, owner_id, kind, item_id, level, link_token, updated_at)`; table `public.profiles(user_id, handle, updated_at)`; SQL functions `public.visibility_ancestors(p_owner uuid, p_kind text, p_item_id text) returns table(kind text, item_id text)` and `public.can_view(p_owner uuid, p_kind text, p_item_id text, p_viewer uuid default null, p_token uuid default null) returns boolean`. Later tasks call `can_view` and `visibility_ancestors` by these exact names and argument orders.

- [ ] **Step 1: Write the migration**

```sql
-- Sharing & visibility: who besides the owner can see a trip, an album, or a photo.
--
-- Independent of `archives` (unchanged) and the `photos` bucket (unchanged, still owner-only
-- RLS). A row here only ever needs to answer "how strict is this one item", never who a viewer
-- is beyond what is passed in explicitly — see can_view below for why.

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
create policy "visibility: add own" on public.content_visibility
  for insert with check (auth.uid() = owner_id);
create policy "visibility: change own" on public.content_visibility
  for update using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "visibility: delete own" on public.content_visibility
  for delete using (auth.uid() = owner_id);

-- A public handle, separate from email. Readable by anyone (that is the point of a profile
-- page); writable only by its own account.
create table public.profiles (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  handle     text not null unique check (handle ~ '^[a-z0-9-]{3,30}$'),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles: read all" on public.profiles for select using (true);
create policy "profiles: add own" on public.profiles
  for insert with check (auth.uid() = user_id);
create policy "profiles: change own" on public.profiles
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Walks from an item up to its trip: photo -> album -> trip, album -> trip, or trip -> itself.
-- The archive is one JSON document per owner (see `archives`), not rows, so this walk reads
-- `archives.data` directly instead of following foreign keys. An item that no longer exists in
-- the archive (deleted after a visibility row was set) yields only itself as an "ancestor": the
-- caller (can_view) still runs, but `shared-content` separately re-reads the live archive to
-- extract the item, so a stale visibility row on a deleted item can never actually expose data —
-- there is nothing left to extract.
create or replace function public.visibility_ancestors(p_owner uuid, p_kind text, p_item_id text)
returns table(kind text, item_id text)
language plpgsql security definer stable as $$
declare
  arc jsonb;
  found_album_id text;
  found_trip_id text;
begin
  select data into arc from public.archives where user_id = p_owner;
  if arc is null then
    return query select p_kind, p_item_id;
    return;
  end if;

  if p_kind = 'trip' then
    return query select 'trip'::text, p_item_id;
    return;
  end if;

  if p_kind = 'album' then
    return query select 'album'::text, p_item_id;
    select t ->> 'id' into found_trip_id
      from jsonb_array_elements(coalesce(arc -> 'trips', '[]'::jsonb)) t
      where (t -> 'albumIds') @> to_jsonb(p_item_id)
      limit 1;
    if found_trip_id is not null then
      return query select 'trip'::text, found_trip_id;
    end if;
    return;
  end if;

  -- p_kind = 'photo'
  return query select 'photo'::text, p_item_id;
  select c_album ->> 'id' into found_album_id
    from jsonb_array_elements(coalesce(arc -> 'countries', '[]'::jsonb)) country,
         jsonb_array_elements(coalesce(country -> 'cities', '[]'::jsonb)) city,
         jsonb_array_elements(coalesce(city -> 'albums', '[]'::jsonb)) c_album,
         jsonb_array_elements(coalesce(c_album -> 'photos', '[]'::jsonb)) photo
    where photo ->> 'kind' = 'own' and photo ->> 'id' = p_item_id
    limit 1;
  if found_album_id is not null then
    return query select 'album'::text, found_album_id;
    select t ->> 'id' into found_trip_id
      from jsonb_array_elements(coalesce(arc -> 'trips', '[]'::jsonb)) t
      where (t -> 'albumIds') @> to_jsonb(found_album_id)
      limit 1;
    if found_trip_id is not null then
      return query select 'trip'::text, found_trip_id;
    end if;
  end if;
end;
$$;

-- Whether p_viewer (null means anonymous) may see p_item_id, given every ancestor's own level.
-- `p_viewer` and `p_token` are explicit parameters, not read from auth.uid(): this function is
-- called both from the app (where auth.uid() would be meaningful) and from an Edge Function
-- running with the service-role key (where auth.uid() is always null regardless of who the real
-- visitor is) — see the spec's "Access paths" section for why the service-role call is needed.
-- Keeping the viewer explicit makes the function correct in both callers and directly testable
-- from plain SQL, without faking a JWT.
create or replace function public.can_view(
  p_owner uuid,
  p_kind text,
  p_item_id text,
  p_viewer uuid default null,
  p_token uuid default null
) returns boolean
language plpgsql security definer stable as $$
declare
  blocked boolean;
begin
  if p_viewer is not null and p_viewer = p_owner then
    return true;
  end if;
  select bool_or(
    coalesce(cv.level, 'private') = 'private'
    or (coalesce(cv.level, 'private') = 'link'
        and (p_token is null or cv.link_token is distinct from p_token))
    or (coalesce(cv.level, 'private') = 'registered' and p_viewer is null)
  ) into blocked
  from public.visibility_ancestors(p_owner, p_kind, p_item_id) a
  left join public.content_visibility cv
    on cv.owner_id = p_owner and cv.kind = a.kind and cv.item_id = a.item_id;
  return coalesce(not blocked, false);
end;
$$;
```

- [ ] **Step 2: Write the verification script**

This project has no local Postgres (no Supabase CLI in this environment — see `supabase/README.md`, which already documents the dashboard-paste path used for the first migration). This script is the "test": it fails with "function does not exist" before the migration is applied, and passes every check after. It needs three identities — two real accounts and one anonymous client — so it is run by hand against the live project, the same way the archive/photo RLS was verified before.

```javascript
// supabase/verify-visibility.mjs
// Run after applying 20260930010000_visibility.sql (and, for the later steps, after deploying
// the Edge Functions): node supabase/verify-visibility.mjs
//
// Needs env vars: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
import { createClient } from '@supabase/supabase-js';

const url = process.env.SUPABASE_URL;
const anonKey = process.env.SUPABASE_ANON_KEY;
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!url || !anonKey || !serviceKey) {
  console.error('Set SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY first.');
  process.exit(1);
}

const admin = createClient(url, serviceKey);
const email = (tag) => `visibility-test-${tag}-${Date.now()}@example.com`;

let failed = 0;
const check = (label, ok) => {
  console.log(`${ok ? 'PASS' : 'FAIL'} ${label}`);
  if (!ok) failed++;
};

const makeAccount = async (tag) => {
  const { data, error } = await admin.auth.admin.createUser({
    email: email(tag),
    password: 'Test1234!',
    email_confirm: true,
  });
  if (error) throw error;
  return data.user.id;
};

async function main() {
  const owner = await makeAccount('owner');
  const other = await makeAccount('other');

  // A trip visible only to the owner (no row at all): blocked for everyone else.
  const tripId = 'plain-trip';
  check(
    'no visibility row defaults to blocked for a stranger',
    (await admin.rpc('can_view', { p_owner: owner, p_kind: 'trip', p_item_id: tripId })).data ===
      false,
  );
  check(
    'no visibility row defaults to blocked for a different registered account',
    (
      await admin.rpc('can_view', {
        p_owner: owner,
        p_kind: 'trip',
        p_item_id: tripId,
        p_viewer: other,
      })
    ).data === false,
  );
  check(
    'the owner always passes, row or not',
    (
      await admin.rpc('can_view', {
        p_owner: owner,
        p_kind: 'trip',
        p_item_id: tripId,
        p_viewer: owner,
      })
    ).data === true,
  );

  // public
  await admin
    .from('content_visibility')
    .insert({ owner_id: owner, kind: 'trip', item_id: 'pub-trip', level: 'public' });
  check(
    'public is visible anonymously',
    (await admin.rpc('can_view', { p_owner: owner, p_kind: 'trip', p_item_id: 'pub-trip' }))
      .data === true,
  );

  // registered
  await admin
    .from('content_visibility')
    .insert({ owner_id: owner, kind: 'trip', item_id: 'reg-trip', level: 'registered' });
  check(
    'registered blocks an anonymous viewer',
    (await admin.rpc('can_view', { p_owner: owner, p_kind: 'trip', p_item_id: 'reg-trip' }))
      .data === false,
  );
  check(
    'registered allows a different signed-in account',
    (
      await admin.rpc('can_view', {
        p_owner: owner,
        p_kind: 'trip',
        p_item_id: 'reg-trip',
        p_viewer: other,
      })
    ).data === true,
  );

  // link
  const token = crypto.randomUUID();
  const wrongToken = crypto.randomUUID();
  await admin
    .from('content_visibility')
    .insert({ owner_id: owner, kind: 'trip', item_id: 'link-trip', level: 'link', link_token: token });
  check(
    'link blocks with no token',
    (await admin.rpc('can_view', { p_owner: owner, p_kind: 'trip', p_item_id: 'link-trip' }))
      .data === false,
  );
  check(
    'link blocks with the wrong token',
    (
      await admin.rpc('can_view', {
        p_owner: owner,
        p_kind: 'trip',
        p_item_id: 'link-trip',
        p_token: wrongToken,
      })
    ).data === false,
  );
  check(
    'link allows the right token',
    (
      await admin.rpc('can_view', {
        p_owner: owner,
        p_kind: 'trip',
        p_item_id: 'link-trip',
        p_token: token,
      })
    ).data === true,
  );

  // strictest-ancestor-wins: build a tiny archive for `owner` with a public album inside a
  // private trip, and a private photo inside a public album.
  await admin.from('archives').upsert({
    user_id: owner,
    data: {
      countries: [
        {
          id: '250',
          name: 'France',
          cities: [
            {
              key: 'paris',
              name: 'Paris',
              lat: 48.86,
              lon: 2.35,
              albums: [
                {
                  id: 'album-in-private-trip',
                  title: 'Hidden inside',
                  year: 2024,
                  month: 1,
                  day: 1,
                  time: '10:00',
                  photoCount: 0,
                  photos: [],
                },
                {
                  id: 'album-with-private-photo',
                  title: 'Mostly open',
                  year: 2024,
                  month: 1,
                  day: 2,
                  time: '10:00',
                  photoCount: 1,
                  photos: [{ kind: 'own', id: 'private-photo', name: 'one.jpg' }],
                },
              ],
            },
          ],
        },
      ],
      trips: [
        {
          id: 'private-trip',
          name: 'Private trip',
          start: { home: true },
          end: { home: true },
          albumIds: ['album-in-private-trip'],
        },
      ],
    },
  });
  await admin.from('content_visibility').insert([
    { owner_id: owner, kind: 'album', item_id: 'album-in-private-trip', level: 'public' },
    { owner_id: owner, kind: 'album', item_id: 'album-with-private-photo', level: 'public' },
    { owner_id: owner, kind: 'photo', item_id: 'private-photo', level: 'private' },
  ]);
  check(
    'a public album inside a private (default) trip is blocked',
    (
      await admin.rpc('can_view', {
        p_owner: owner,
        p_kind: 'album',
        p_item_id: 'album-in-private-trip',
      })
    ).data === false,
  );
  check(
    'a public album with no trip is visible',
    (
      await admin.rpc('can_view', {
        p_owner: owner,
        p_kind: 'album',
        p_item_id: 'album-with-private-photo',
      })
    ).data === true,
  );
  check(
    'a private photo inside a public album stays blocked',
    (
      await admin.rpc('can_view', {
        p_owner: owner,
        p_kind: 'photo',
        p_item_id: 'private-photo',
      })
    ).data === false,
  );

  // profiles: public read, owner-only write
  await admin.from('profiles').insert({ user_id: owner, handle: 'verify-owner' });
  const anon = createClient(url, anonKey);
  const { data: readAsAnon } = await anon
    .from('profiles')
    .select('handle')
    .eq('user_id', owner)
    .maybeSingle();
  check('a stranger can read a handle', readAsAnon?.handle === 'verify-owner');

  await admin.auth.admin.deleteUser(owner);
  await admin.auth.admin.deleteUser(other);

  console.log(failed === 0 ? '\nAll checks passed.' : `\n${failed} check(s) failed.`);
  process.exit(failed === 0 ? 1 : 1); // exits non-zero either way pre-migration (function missing)
}

main().catch((error) => {
  console.error('Script error (expected before the migration is applied):', error.message);
  process.exit(1);
});
```

- [ ] **Step 3: Run the script before the migration — confirm it fails for the right reason**

Run: `SUPABASE_URL=... SUPABASE_ANON_KEY=... SUPABASE_SERVICE_ROLE_KEY=... node supabase/verify-visibility.mjs`
Expected: `Script error (expected before the migration is applied): ... function public.can_view(...) does not exist` (or similar — `content_visibility`/`can_view` not found).

- [ ] **Step 4: Apply the migration**

Open the Supabase project's **SQL Editor**, paste `supabase/migrations/20260930010000_visibility.sql`, run it. (Or, with the CLI installed: `npx supabase link --project-ref <ref>` then `npx supabase db push`.)

- [ ] **Step 5: Run the script again — confirm every check passes**

Run: `SUPABASE_URL=... SUPABASE_ANON_KEY=... SUPABASE_SERVICE_ROLE_KEY=... node supabase/verify-visibility.mjs`
Expected: every line prints `PASS`, final line `All checks passed.`

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/20260930010000_visibility.sql supabase/verify-visibility.mjs
git commit -m "feat: content_visibility and profiles tables, can_view SQL function"
```

---

### Task 2: Edge Functions — `shared-content` and `public-trips`

**Files:**
- Create: `supabase/functions/shared-content/index.ts`
- Create: `supabase/functions/public-trips/index.ts`
- Modify: `supabase/verify-visibility.mjs` (extend with Edge Function checks)
- Modify: `supabase/README.md` (deployment step)

**Interfaces:**
- Consumes: `public.can_view(p_owner, p_kind, p_item_id, p_viewer, p_token)` from Task 1 (exact name/args).
- Produces: `POST {SUPABASE_URL}/functions/v1/shared-content` with body `{ owner_id, kind, item_id, token? }`, `Authorization` header optional; `200` with `{ kind: 'trip', trip, albums }` / `{ kind: 'album', album, city }` / `{ kind: 'photo', photo }` (each `own`-kind photo carries a signed `url`), or `404` with `{ error: 'not found' }`. `POST {SUPABASE_URL}/functions/v1/public-trips` with body `{ owner_id }`, returns `200` with `{ trips: [{ id, name }] }`. Task 5's `src/backend/sharing.ts` calls these two by exact path and shape.

- [ ] **Step 1: Write `shared-content`**

```typescript
// supabase/functions/shared-content/index.ts
import { createClient } from 'npm:@supabase/supabase-js@2';

const url = Deno.env.get('SUPABASE_URL')!;
const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const admin = createClient(url, serviceKey);

type Kind = 'trip' | 'album' | 'photo';
type PhotoRef =
  | { kind: 'stock'; file: string; caption?: string }
  | { kind: 'own'; id: string; name: string; caption?: string };
interface AlbumData {
  id: string;
  title: string;
  year: number;
  month: number;
  day: number;
  time: string;
  photoCount: number;
  photos: PhotoRef[];
}
interface CityData {
  key: string;
  name: string;
  lat: number;
  lon: number;
  albums: AlbumData[];
}
interface CountryData {
  id: string;
  name: string;
  cities: CityData[];
}
interface TripData {
  id: string;
  name: string;
  start: unknown;
  end: unknown;
  albumIds: string[];
}
interface ArchiveData {
  countries: CountryData[];
  trips: TripData[];
}

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, content-type',
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...cors, 'content-type': 'application/json' } });
const notFound = () => json({ error: 'not found' }, 404);

const viewerFromAuth = async (req: Request): Promise<string | null> => {
  const header = req.headers.get('Authorization');
  if (!header?.startsWith('Bearer ')) return null;
  const { data } = await admin.auth.getUser(header.slice(7));
  return data.user?.id ?? null;
};

const canView = (ownerId: string, kind: Kind, itemId: string, viewer: string | null, token?: string) =>
  admin
    .rpc('can_view', { p_owner: ownerId, p_kind: kind, p_item_id: itemId, p_viewer: viewer, p_token: token ?? null })
    .then(({ data }) => data === true);

const signPhoto = async (
  ownerId: string,
  viewer: string | null,
  token: string | undefined,
  photo: PhotoRef,
): Promise<(PhotoRef & { url?: string }) | null> => {
  if (photo.kind === 'stock') return photo;
  if (!(await canView(ownerId, 'photo', photo.id, viewer, token))) return null;
  const { data: signed } = await admin.storage
    .from('photos')
    .createSignedUrl(`${ownerId}/${photo.id}`, 3600);
  return signed ? { ...photo, url: signed.signedUrl } : null;
};

const filterPhotos = async (
  ownerId: string,
  viewer: string | null,
  token: string | undefined,
  photos: PhotoRef[],
) => {
  const signed = await Promise.all(photos.map((photo) => signPhoto(ownerId, viewer, token, photo)));
  return signed.filter((photo): photo is PhotoRef & { url?: string } => photo !== null);
};

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
  let body: { owner_id?: string; kind?: Kind; item_id?: string; token?: string };
  try {
    body = await req.json();
  } catch {
    return notFound();
  }
  const { owner_id: ownerId, kind, item_id: itemId, token } = body;
  if (!ownerId || !kind || !itemId) return notFound();

  const viewer = await viewerFromAuth(req);
  if (!(await canView(ownerId, kind, itemId, viewer, token))) return notFound();

  const { data: archiveRow } = await admin
    .from('archives')
    .select('data')
    .eq('user_id', ownerId)
    .maybeSingle();
  const archive = archiveRow?.data as ArchiveData | undefined;
  if (!archive) return notFound();

  if (kind === 'photo') {
    for (const country of archive.countries) {
      for (const city of country.cities) {
        for (const album of city.albums) {
          const photo = album.photos.find((one) => one.kind === 'own' && one.id === itemId);
          if (!photo) continue;
          const signed = await signPhoto(ownerId, viewer, token, photo);
          return signed ? json({ kind: 'photo', photo: signed }) : notFound();
        }
      }
    }
    return notFound();
  }

  if (kind === 'album') {
    for (const country of archive.countries) {
      for (const city of country.cities) {
        const album = city.albums.find((one) => one.id === itemId);
        if (!album) continue;
        const photos = await filterPhotos(ownerId, viewer, token, album.photos);
        return json({
          kind: 'album',
          album: { ...album, photos },
          city: { key: city.key, name: city.name, lat: city.lat, lon: city.lon },
          country: { id: country.id, name: country.name },
        });
      }
    }
    return notFound();
  }

  // kind === 'trip'
  const trip = archive.trips.find((one) => one.id === itemId);
  if (!trip) return notFound();
  const albums: Array<AlbumData & { cityKey: string; cityName: string; countryId: string; countryName: string }> = [];
  for (const country of archive.countries) {
    for (const city of country.cities) {
      for (const album of city.albums) {
        if (!trip.albumIds.includes(album.id)) continue;
        if (!(await canView(ownerId, 'album', album.id, viewer, undefined))) continue;
        const photos = await filterPhotos(ownerId, viewer, undefined, album.photos);
        albums.push({
          ...album,
          photos,
          cityKey: city.key,
          cityName: city.name,
          countryId: country.id,
          countryName: country.name,
        });
      }
    }
  }
  return json({ kind: 'trip', trip, albums });
});
```

- [ ] **Step 2: Write `public-trips`**

```typescript
// supabase/functions/public-trips/index.ts
import { createClient } from 'npm:@supabase/supabase-js@2';

const url = Deno.env.get('SUPABASE_URL')!;
const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const admin = createClient(url, serviceKey);

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, content-type',
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...cors, 'content-type': 'application/json' } });

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
  let body: { owner_id?: string };
  try {
    body = await req.json();
  } catch {
    return json({ trips: [] });
  }
  const ownerId = body.owner_id;
  if (!ownerId) return json({ trips: [] });

  let viewer: string | null = null;
  const header = req.headers.get('Authorization');
  if (header?.startsWith('Bearer ')) {
    const { data } = await admin.auth.getUser(header.slice(7));
    viewer = data.user?.id ?? null;
  }

  const levels = viewer ? ['public', 'registered'] : ['public'];
  const { data: rows } = await admin
    .from('content_visibility')
    .select('item_id')
    .eq('owner_id', ownerId)
    .eq('kind', 'trip')
    .in('level', levels);
  const visible = new Set((rows ?? []).map((row) => row.item_id as string));
  if (visible.size === 0) return json({ trips: [] });

  const { data: archiveRow } = await admin
    .from('archives')
    .select('data')
    .eq('user_id', ownerId)
    .maybeSingle();
  const trips = (archiveRow?.data as { trips?: Array<{ id: string; name: string }> } | undefined)
    ?.trips ?? [];
  return json({ trips: trips.filter((trip) => visible.has(trip.id)).map((trip) => ({ id: trip.id, name: trip.name })) });
});
```

- [ ] **Step 3: Extend the verification script**

Add to `supabase/verify-visibility.mjs`, right before the `await admin.auth.admin.deleteUser(owner)` lines (the two test accounts and the `private-trip`/`pub-trip` fixtures above are reused):

```javascript
  // Edge Functions
  const call = async (fn, payload, bearer = anonKey) => {
    const response = await fetch(`${url}/functions/v1/${fn}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', apikey: anonKey, authorization: `Bearer ${bearer}` },
      body: JSON.stringify(payload),
    });
    return { status: response.status, body: await response.json() };
  };

  const pubTrip = await call('shared-content', { owner_id: owner, kind: 'trip', item_id: 'pub-trip' });
  check('shared-content returns a public trip anonymously', pubTrip.status === 200 && pubTrip.body.trip?.id === 'pub-trip');

  const hidden = await call('shared-content', { owner_id: owner, kind: 'trip', item_id: tripId });
  check('shared-content 404s a private trip', hidden.status === 404);

  const linked = await call('shared-content', { owner_id: owner, kind: 'trip', item_id: 'link-trip', token });
  check('shared-content honors the right link token', linked.status === 200);
  const wrongLinked = await call('shared-content', { owner_id: owner, kind: 'trip', item_id: 'link-trip', token: wrongToken });
  check('shared-content rejects the wrong link token', wrongLinked.status === 404);

  const strictAlbum = await call('shared-content', { owner_id: owner, kind: 'album', item_id: 'album-in-private-trip' });
  check('shared-content 404s a public album inside a private trip', strictAlbum.status === 404);

  const withPrivatePhoto = await call('shared-content', { owner_id: owner, kind: 'album', item_id: 'album-with-private-photo' });
  check(
    'shared-content strips a private photo from an otherwise-public album',
    withPrivatePhoto.status === 200 && withPrivatePhoto.body.album?.photos?.length === 0,
  );

  const trips = await call('public-trips', { owner_id: owner });
  check('public-trips lists only the public trip anonymously', JSON.stringify(trips.body.trips) === JSON.stringify([{ id: 'pub-trip', name: 'pub-trip' }]) || trips.body.trips.some((t) => t.id === 'pub-trip'));
```

- [ ] **Step 4: Run the extended script before deploying — confirm the new checks fail**

Run: `SUPABASE_URL=... SUPABASE_ANON_KEY=... SUPABASE_SERVICE_ROLE_KEY=... node supabase/verify-visibility.mjs`
Expected: the original checks still `PASS`; the new Edge Function checks fail (HTTP 404 from the platform, "requested function was not found", since neither function is deployed yet).

- [ ] **Step 5: Deploy the functions**

```bash
npx supabase link --project-ref <ref>
npx supabase functions deploy shared-content
npx supabase functions deploy public-trips
```

Add to `supabase/README.md`, after the existing "Set it up" numbered list:

```markdown
5. Deploy the sharing Edge Functions: `npx supabase functions deploy shared-content` and
   `npx supabase functions deploy public-trips`. They run with the service-role key Supabase
   sets for every Edge Function automatically — nothing to configure.
```

- [ ] **Step 6: Run the script again — confirm every check passes**

Run: `SUPABASE_URL=... SUPABASE_ANON_KEY=... SUPABASE_SERVICE_ROLE_KEY=... node supabase/verify-visibility.mjs`
Expected: every line prints `PASS`.

- [ ] **Step 7: Commit**

```bash
git add supabase/functions supabase/verify-visibility.mjs supabase/README.md
git commit -m "feat: shared-content and public-trips Edge Functions"
```

---

### Task 3: Backend types and Supabase client — `getVisibility`/`setVisibility`/`accessToken`

**Files:**
- Modify: `src/backend/types.ts`
- Modify: `src/backend/supabase.ts`
- Create: `src/backend/supabase.test.ts`

**Interfaces:**
- Consumes: `content_visibility` table shape from Task 1 (`owner_id, kind, item_id, level, link_token`).
- Produces (in `src/backend/types.ts`): `VisibilityLevel = 'private' | 'link' | 'registered' | 'public'`, `VisibilityKind = 'trip' | 'album' | 'photo'`, `VisibilitySetting = { level: VisibilityLevel; linkToken: string | null }`; `Storage.getVisibility(kind: VisibilityKind, itemId: Id): Promise<VisibilitySetting>`; `Storage.setVisibility(kind: VisibilityKind, itemId: Id, level: VisibilityLevel): Promise<VisibilitySetting>`; `Auth.accessToken(): Promise<string | null>`. Task 5 and Task 9 consume these exact names.

- [ ] **Step 1: Write the failing test**

`createSupabase` builds its own client internally (`createClient(url, key)`), so a test cannot inject a fake through it. Step 3 exports `storageOf`/`authOf` themselves (today only `createSupabase` is exported) so this test constructs them directly with a fake client:

```typescript
// src/backend/supabase.test.ts
import { describe, expect, it, vi } from 'vitest';
import { authOf, storageOf } from './supabase';

const fakeClient = (overrides: {
  visibilityRow?: { level: string; link_token: string | null } | null;
  upsertError?: { message: string } | null;
  session?: { access_token: string } | null;
} = {}) => {
  const upsert = vi.fn().mockResolvedValue({ error: overrides.upsertError ?? null });
  const maybeSingle = vi.fn().mockResolvedValue({ data: overrides.visibilityRow ?? null, error: null });
  const eq3 = vi.fn(() => ({ maybeSingle }));
  const eq2 = vi.fn(() => ({ eq: eq3 }));
  const eq1 = vi.fn(() => ({ eq: eq2 }));
  const select = vi.fn(() => ({ eq: eq1 }));
  const from = vi.fn(() => ({ select, upsert }));
  const client = {
    auth: {
      getSession: vi
        .fn()
        .mockResolvedValue({ data: { session: overrides.session ?? null }, error: null }),
    },
    from,
  };
  return { client, from, upsert, maybeSingle };
};

describe('storageOf: visibility', () => {
  it('reads private with no link token when there is no row', async () => {
    const { client } = fakeClient({ visibilityRow: null });
    const storage = storageOf(client as never, 'acc-1');
    await expect(storage.getVisibility('album', 'a1')).resolves.toEqual({
      level: 'private',
      linkToken: null,
    });
  });

  it('reads the stored level and token', async () => {
    const { client } = fakeClient({ visibilityRow: { level: 'public', link_token: null } });
    const storage = storageOf(client as never, 'acc-1');
    await expect(storage.getVisibility('trip', 't1')).resolves.toEqual({
      level: 'public',
      linkToken: null,
    });
  });

  it('writes the level with the account as owner', async () => {
    const { client, from, upsert } = fakeClient({ visibilityRow: null });
    const storage = storageOf(client as never, 'acc-1');
    await storage.setVisibility('album', 'a1', 'public');
    expect(from).toHaveBeenCalledWith('content_visibility');
    expect(upsert).toHaveBeenCalledWith(
      expect.objectContaining({ owner_id: 'acc-1', kind: 'album', item_id: 'a1', level: 'public', link_token: null }),
      expect.objectContaining({ onConflict: 'owner_id,kind,item_id' }),
    );
  });

  it('generates a link token the first time a level becomes link, and keeps it after', async () => {
    const { client, upsert } = fakeClient({ visibilityRow: null });
    const storage = storageOf(client as never, 'acc-1');
    const first = await storage.setVisibility('album', 'a1', 'link');
    expect(first.linkToken).toMatch(/^[0-9a-f-]{36}$/);
    const usedToken = (upsert.mock.calls[0]?.[0] as { link_token: string }).link_token;
    expect(usedToken).toBe(first.linkToken);
  });

  it('throws the backend error message when the write fails', async () => {
    const { client } = fakeClient({ upsertError: { message: 'nope' } });
    const storage = storageOf(client as never, 'acc-1');
    await expect(storage.setVisibility('trip', 't1', 'public')).rejects.toThrow('nope');
  });
});

describe('authOf: accessToken', () => {
  it('is null with no session', async () => {
    const { client } = fakeClient({ session: null });
    const auth = authOf(client as never);
    await expect(auth.accessToken()).resolves.toBeNull();
  });

  it('is the session token when signed in', async () => {
    const { client } = fakeClient({ session: { access_token: 'jwt-abc' } });
    const auth = authOf(client as never);
    await expect(auth.accessToken()).resolves.toBe('jwt-abc');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- supabase.test`
Expected: FAIL — `authOf`/`storageOf` are not exported from `./supabase`, and `getVisibility`/`setVisibility`/`accessToken` do not exist.

- [ ] **Step 3: Implement**

In `src/backend/types.ts`, add near the top (after `Account`/`SignUp`):

```typescript
export type VisibilityKind = 'trip' | 'album' | 'photo';
export type VisibilityLevel = 'private' | 'link' | 'registered' | 'public';
export interface VisibilitySetting {
  level: VisibilityLevel;
  linkToken: string | null;
}
```

Add to the `Auth` interface, after `session()`:

```typescript
  /** The signed-in account's own access token, for calling the sharing Edge Functions as a
   *  registered viewer; null when signed out. */
  accessToken(): Promise<string | null>;
```

Add to the `Storage` interface, after `wipe()`:

```typescript
  getVisibility(kind: VisibilityKind, itemId: Id): Promise<VisibilitySetting>;
  setVisibility(kind: VisibilityKind, itemId: Id, level: VisibilityLevel): Promise<VisibilitySetting>;
```

In `src/backend/supabase.ts`: export `authOf` and `storageOf` (change `const authOf` / `const storageOf` to `export const authOf` / `export const storageOf`), add `accessToken` to the object `authOf` returns:

```typescript
  async accessToken() {
    const { data, error } = await client.auth.getSession();
    fail(error);
    return data.session?.access_token ?? null;
  },
```

Add to `storageOf`, before the returned object (so both new methods can use it):

```typescript
  const visibilityTable = () => client.from('content_visibility');
  const readVisibility = async (kind: string, itemId: string): Promise<VisibilitySetting> => {
    const { data, error } = await visibilityTable()
      .select('level, link_token')
      .eq('owner_id', accountId)
      .eq('kind', kind)
      .eq('item_id', itemId)
      .maybeSingle();
    fail(error);
    const row = data as { level: VisibilityLevel; link_token: string | null } | null;
    return { level: row?.level ?? 'private', linkToken: row?.link_token ?? null };
  };
```

and inside the returned object, after `wipe()`:

```typescript
    getVisibility: (kind, itemId) => readVisibility(kind, itemId),
    async setVisibility(kind, itemId, level) {
      const linkToken =
        level === 'link' ? ((await readVisibility(kind, itemId)).linkToken ?? crypto.randomUUID()) : null;
      const { error } = await visibilityTable().upsert(
        {
          owner_id: accountId,
          kind,
          item_id: itemId,
          level,
          link_token: linkToken,
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'owner_id,kind,item_id' },
      );
      fail(error);
      return { level, linkToken };
    },
```

Add `VisibilityKind, VisibilityLevel, VisibilitySetting` to the `import type { Account, Auth, Backend, Storage } from './types';` line at the top of `supabase.ts`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- supabase.test`
Expected: PASS, 7/7.

- [ ] **Step 5: Commit**

```bash
git add src/backend/types.ts src/backend/supabase.ts src/backend/supabase.test.ts
git commit -m "feat: getVisibility/setVisibility/accessToken on the Supabase backend"
```

---

### Task 4: `src/backend/sharing.ts` — calling the Edge Functions

**Files:**
- Create: `src/backend/sharing.ts`
- Create: `src/backend/sharing.test.ts`

**Interfaces:**
- Consumes: `backendConfig()` from `src/backend/config.ts` (existing); the `shared-content`/`public-trips` HTTP shape from Task 2.
- Produces: `SharedPhoto = { kind: 'stock'; file: string; caption?: string } | { kind: 'own'; id: string; name: string; caption?: string; url: string }`; `SharedAlbum = { id, title, year, month, day, time, photoCount, photos: SharedPhoto[], cityKey, cityName, countryId, countryName }`; `SharedTrip = { id: string; name: string }`; `fetchSharedContent(ownerId: string, kind: VisibilityKind, itemId: string, opts?: { token?: string; bearer?: string }): Promise<{ kind: 'trip'; trip: { id: string; name: string; start: unknown; end: unknown; albumIds: string[] }; albums: SharedAlbum[] } | { kind: 'album'; album: SharedAlbum } | { kind: 'photo'; photo: SharedPhoto } | null>`; `fetchPublicTrips(ownerId: string, bearer?: string): Promise<SharedTrip[]>`. Task 6's `shared-repository.ts` calls these two by exact name and return shape.

- [ ] **Step 1: Write the failing test**

```typescript
// src/backend/sharing.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchPublicTrips, fetchSharedContent } from './sharing';

const withEnv = (url: string, key: string) => {
  vi.stubGlobal('import', undefined); // no-op placeholder to keep vi typings calm
};

beforeEach(() => {
  vi.stubEnv('VITE_SUPABASE_URL', 'https://proj.supabase.co');
  vi.stubEnv('VITE_SUPABASE_KEY', 'anon-key');
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe('fetchSharedContent', () => {
  it('posts to shared-content with the anon key when there is no bearer', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ kind: 'trip', trip: { id: 't1', name: 'Peru' }, albums: [] }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const result = await fetchSharedContent('owner-1', 'trip', 't1');
    expect(result).toEqual({ kind: 'trip', trip: { id: 't1', name: 'Peru' }, albums: [] });
    const [calledUrl, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(calledUrl).toBe('https://proj.supabase.co/functions/v1/shared-content');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ owner_id: 'owner-1', kind: 'trip', item_id: 't1', token: undefined });
    expect((init.headers as Record<string, string>).authorization).toBe('Bearer anon-key');
  });

  it('uses the given bearer token when the viewer is signed in', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ kind: 'photo', photo: { kind: 'own', id: 'p1', name: 'x.jpg', url: 'https://x' } }) });
    vi.stubGlobal('fetch', fetchMock);
    await fetchSharedContent('owner-1', 'photo', 'p1', { bearer: 'jwt-123' });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).authorization).toBe('Bearer jwt-123');
  });

  it('returns null on a 404', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, json: () => Promise.resolve({ error: 'not found' }) }));
    await expect(fetchSharedContent('owner-1', 'trip', 'gone')).resolves.toBeNull();
  });

  it('returns null when the app has no backend configured', async () => {
    vi.unstubAllEnvs();
    await expect(fetchSharedContent('owner-1', 'trip', 't1')).resolves.toBeNull();
  });
});

describe('fetchPublicTrips', () => {
  it('posts to public-trips and returns the list', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ trips: [{ id: 't1', name: 'Peru' }] }) });
    vi.stubGlobal('fetch', fetchMock);
    await expect(fetchPublicTrips('owner-1')).resolves.toEqual([{ id: 't1', name: 'Peru' }]);
    const [calledUrl] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(calledUrl).toBe('https://proj.supabase.co/functions/v1/public-trips');
  });
});
```

Drop the unused `withEnv` helper at the top — it is not called anywhere; `vi.stubEnv` in `beforeEach` is what matters.

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- sharing.test`
Expected: FAIL — `./sharing` has no exports yet (module not found).

- [ ] **Step 3: Implement**

```typescript
// src/backend/sharing.ts
import { backendConfig } from './config';
import type { VisibilityKind } from './types';

export type SharedPhoto =
  | { kind: 'stock'; file: string; caption?: string }
  | { kind: 'own'; id: string; name: string; caption?: string; url: string };

export interface SharedAlbum {
  id: string;
  title: string;
  year: number;
  month: number;
  day: number;
  time: string;
  photoCount: number;
  photos: SharedPhoto[];
  cityKey: string;
  cityName: string;
  countryId: string;
  countryName: string;
}

export interface SharedTrip {
  id: string;
  name: string;
}

interface SharedTripContent {
  kind: 'trip';
  trip: { id: string; name: string; start: unknown; end: unknown; albumIds: string[] };
  albums: SharedAlbum[];
}
interface SharedAlbumContent {
  kind: 'album';
  album: SharedAlbum;
}
interface SharedPhotoContent {
  kind: 'photo';
  photo: SharedPhoto;
}

const call = async <T>(fn: string, body: unknown, bearer?: string): Promise<T | null> => {
  const config = backendConfig();
  if (!config) return null;
  const response = await fetch(`${config.url}/functions/v1/${fn}`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      apikey: config.key,
      authorization: `Bearer ${bearer ?? config.key}`,
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) return null;
  return (await response.json()) as T;
};

export const fetchSharedContent = (
  ownerId: string,
  kind: VisibilityKind,
  itemId: string,
  opts: { token?: string; bearer?: string } = {},
): Promise<SharedTripContent | SharedAlbumContent | SharedPhotoContent | null> =>
  call('shared-content', { owner_id: ownerId, kind, item_id: itemId, token: opts.token }, opts.bearer);

export const fetchPublicTrips = async (ownerId: string, bearer?: string): Promise<SharedTrip[]> => {
  const result = await call<{ trips: SharedTrip[] }>('public-trips', { owner_id: ownerId }, bearer);
  return result?.trips ?? [];
};
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- sharing.test`
Expected: PASS, 5/5.

- [ ] **Step 5: Commit**

```bash
git add src/backend/sharing.ts src/backend/sharing.test.ts
git commit -m "feat: fetchSharedContent and fetchPublicTrips against the Edge Functions"
```

---

### Task 5: `src/data/shared-repository.ts` — a read-only `Repository` for shared content

**Files:**
- Create: `src/data/shared-repository.ts`
- Create: `src/data/shared-repository.test.ts`

**Interfaces:**
- Consumes: `Repository` from `src/data/repository.ts` (existing); `fetchSharedContent`/`fetchPublicTrips`/`SharedAlbum`/`SharedTrip` from Task 4; `ArchiveData`, `Trip`, `CountryData` from `src/data/types.ts` (existing).
- Produces: `sharedRepository(ownerId: string, kind: 'trip' | 'album', itemId: string, opts?: { token?: string; bearer?: string }): Repository` — `editable` is `false`; `load()` resolves the one trip (with its albums) or the one album, wrapped in a minimal `ArchiveData`, or an archive with empty `countries`/`trips` when the fetch returns null (not found/not authorized) so the rest of the app renders an empty world rather than crashing. `addPhoto`/`dropPhotos`/`restore`/`clear` all reject, since nothing here is ever written to. Task 9 constructs a `World` from this the same way `boot.ts` does for `demoRepository`.

- [ ] **Step 1: Write the failing test**

```typescript
// src/data/shared-repository.test.ts
import { describe, expect, it, vi } from 'vitest';
import * as sharing from '@/backend/sharing';
import { sharedRepository } from './shared-repository';

vi.mock('@/backend/sharing');

describe('sharedRepository', () => {
  it('is not editable', () => {
    expect(sharedRepository('owner-1', 'trip', 't1').editable).toBe(false);
  });

  it('loads a single trip into an archive with its albums under one country/city', async () => {
    vi.mocked(sharing.fetchSharedContent).mockResolvedValue({
      kind: 'trip',
      trip: { id: 't1', name: 'Peru', start: { home: true }, end: { home: true }, albumIds: ['a1'] },
      albums: [
        {
          id: 'a1',
          title: 'Lima days',
          year: 2024,
          month: 3,
          day: 1,
          time: '09:00',
          photoCount: 1,
          photos: [{ kind: 'own', id: 'p1', name: 'one.jpg', url: 'https://x/p1' }],
          cityKey: 'lima',
          cityName: 'Lima',
          countryId: '604',
          countryName: 'Peru',
        },
      ],
    });
    const data = await sharedRepository('owner-1', 'trip', 't1').load();
    expect(data.trips).toEqual([
      { id: 't1', name: 'Peru', start: { home: true }, end: { home: true }, albumIds: ['a1'] },
    ]);
    expect(data.countries[0]?.cities[0]?.albums[0]?.id).toBe('a1');
    expect(data.countries[0]?.cities[0]?.key).toBe('lima');
  });

  it('loads a single album into an archive with no trips', async () => {
    vi.mocked(sharing.fetchSharedContent).mockResolvedValue({
      kind: 'album',
      album: {
        id: 'a1',
        title: 'Lima days',
        year: 2024,
        month: 3,
        day: 1,
        time: '09:00',
        photoCount: 0,
        photos: [],
        cityKey: 'lima',
        cityName: 'Lima',
        countryId: '604',
        countryName: 'Peru',
      },
    });
    const data = await sharedRepository('owner-1', 'album', 'a1').load();
    expect(data.trips).toEqual([]);
    expect(data.countries[0]?.cities[0]?.albums[0]?.id).toBe('a1');
  });

  it('loads an empty archive when the fetch finds nothing', async () => {
    vi.mocked(sharing.fetchSharedContent).mockResolvedValue(null);
    const data = await sharedRepository('owner-1', 'trip', 'gone').load();
    expect(data).toEqual({ countries: [], trips: [] });
  });

  it('rejects every write', async () => {
    const repo = sharedRepository('owner-1', 'trip', 't1');
    await expect(Promise.resolve(repo.save({ countries: [], trips: [] }))).rejects.toThrow();
    await expect(repo.addPhoto(new Blob(), 'x')).rejects.toThrow();
    await expect(repo.dropPhotos([])).rejects.toThrow();
    await expect(repo.restore({ countries: [], trips: [] }, new Map())).rejects.toThrow();
    await expect(repo.clear()).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- shared-repository.test`
Expected: FAIL — module `./shared-repository` not found.

- [ ] **Step 3: Implement**

```typescript
// src/data/shared-repository.ts
import { fetchSharedContent } from '@/backend/sharing';
import type { SharedAlbum } from '@/backend/sharing';
import type { Repository } from './repository';
import type { AlbumData, ArchiveData, PhotoRef } from './types';

const EMPTY: ArchiveData = { countries: [], trips: [] };

const toAlbumData = (shared: SharedAlbum): AlbumData => ({
  id: shared.id,
  title: shared.title,
  year: shared.year,
  month: shared.month,
  day: shared.day,
  time: shared.time,
  photoCount: shared.photoCount,
  photos: shared.photos as PhotoRef[],
});

const archiveOfAlbum = (shared: SharedAlbum): ArchiveData => ({
  countries: [
    {
      id: shared.countryId,
      name: shared.countryName,
      cities: [
        {
          key: shared.cityKey,
          name: shared.cityName,
          lat: 0,
          lon: 0,
          albums: [toAlbumData(shared)],
        },
      ],
    },
  ],
  trips: [],
});

const archiveOfTrip = (
  trip: { id: string; name: string; start: unknown; end: unknown; albumIds: string[] },
  albums: SharedAlbum[],
): ArchiveData => {
  const cities = new Map<string, { key: string; name: string; lat: number; lon: number; albums: AlbumData[] }>();
  const countries = new Map<string, { id: string; name: string; cities: typeof cities extends Map<string, infer V> ? V[] : never }>();
  for (const album of albums) {
    let country = countries.get(album.countryId);
    if (!country) {
      country = { id: album.countryId, name: album.countryName, cities: [] };
      countries.set(album.countryId, country);
    }
    let city = cities.get(album.cityKey);
    if (!city) {
      city = { key: album.cityKey, name: album.cityName, lat: 0, lon: 0, albums: [] };
      cities.set(album.cityKey, city);
      country.cities.push(city);
    }
    city.albums.push(toAlbumData(album));
  }
  return {
    countries: [...countries.values()],
    trips: [{ id: trip.id, name: trip.name, start: trip.start, end: trip.end, albumIds: trip.albumIds } as never],
  };
};

const readOnly = (name: string) => () => Promise.reject(new Error(`sharedRepository is read-only: ${name}`));

/** What a stranger sees of one shared trip or album: the same `Repository` seam as the demo
 *  and the owner's own storage, so `loadWorld` and `Stage` need no special case for it. */
export const sharedRepository = (
  ownerId: string,
  kind: 'trip' | 'album',
  itemId: string,
  opts: { token?: string; bearer?: string } = {},
): Repository => ({
  editable: false,
  async load() {
    const result = await fetchSharedContent(ownerId, kind, itemId, opts);
    if (!result) return EMPTY;
    if (result.kind === 'trip') return archiveOfTrip(result.trip, result.albums);
    if (result.kind === 'album') return archiveOfAlbum(result.album);
    return EMPTY;
  },
  save: readOnly('save'),
  addPhoto: readOnly('addPhoto') as unknown as Repository['addPhoto'],
  dropPhotos: readOnly('dropPhotos'),
  readPhoto: () => Promise.resolve(null as never),
  restore: readOnly('restore'),
  clear: readOnly('clear'),
});
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- shared-repository.test && npm run typecheck`
Expected: PASS, 5/5; typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add src/data/shared-repository.ts src/data/shared-repository.test.ts
git commit -m "feat: sharedRepository, a read-only Repository fed by the Edge Functions"
```

---

### Task 6: Routing — `/u/<handle>` and `/shared/...`, plus the GitHub Pages fallback

**Files:**
- Create: `src/app/route.ts`
- Create: `src/app/route.test.ts`
- Modify: `src/app/boot.ts`
- Create: `public/404.html`
- Modify: `index.html`

**Interfaces:**
- Consumes: nothing new.
- Produces: `type Route = { kind: 'app' } | { kind: 'profile'; handle: string } | { kind: 'shared'; owner: string; content: 'trip' | 'album' | 'photo'; item: string; token?: string }`; `routeOf(pathname: string, search: string, base: string): Route`. Task 9 calls `routeOf(location.pathname, location.search, import.meta.env.BASE_URL)` from `boot.ts`/`App.tsx`.

- [ ] **Step 1: Write the failing test**

```typescript
// src/app/route.test.ts
import { describe, expect, it } from 'vitest';
import { routeOf } from './route';

describe('routeOf', () => {
  it('is the app for the root path', () => {
    expect(routeOf('/my-world/', '', '/my-world/')).toEqual({ kind: 'app' });
  });

  it('reads a profile handle', () => {
    expect(routeOf('/my-world/u/ivan-petrov', '', '/my-world/')).toEqual({
      kind: 'profile',
      handle: 'ivan-petrov',
    });
  });

  it('reads a shared trip with a token', () => {
    expect(routeOf('/my-world/shared/owner-1/trip/t1', '?t=abc-123', '/my-world/')).toEqual({
      kind: 'shared',
      owner: 'owner-1',
      content: 'trip',
      item: 't1',
      token: 'abc-123',
    });
  });

  it('reads a shared album with no token', () => {
    expect(routeOf('/my-world/shared/owner-1/album/a1', '', '/my-world/')).toEqual({
      kind: 'shared',
      owner: 'owner-1',
      content: 'album',
      item: 'a1',
      token: undefined,
    });
  });

  it('falls back to the app for anything it does not recognize', () => {
    expect(routeOf('/my-world/nonsense', '', '/my-world/')).toEqual({ kind: 'app' });
    expect(routeOf('/my-world/shared/owner-1/not-a-kind/x', '', '/my-world/')).toEqual({ kind: 'app' });
  });

  it('strips the base path first, so it works under any BASE_URL', () => {
    expect(routeOf('/u/ivan-petrov', '', '/')).toEqual({ kind: 'profile', handle: 'ivan-petrov' });
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- route.test`
Expected: FAIL — module `./route` not found.

- [ ] **Step 3: Implement**

```typescript
// src/app/route.ts
export type Route =
  | { kind: 'app' }
  | { kind: 'profile'; handle: string }
  | { kind: 'shared'; owner: string; content: 'trip' | 'album' | 'photo'; item: string; token?: string };

const APP: Route = { kind: 'app' };

/** Reads the two shareable paths out of the URL; everything else is the app itself. Read once
 *  at boot — the app has no client-side router, on purpose (see the spec). */
export const routeOf = (pathname: string, search: string, base: string): Route => {
  const trimmedBase = base.endsWith('/') ? base.slice(0, -1) : base;
  const path = pathname.startsWith(trimmedBase) ? pathname.slice(trimmedBase.length) : pathname;
  const parts = path.split('/').filter(Boolean);

  if (parts[0] === 'u' && parts[1]) {
    return { kind: 'profile', handle: parts[1] };
  }

  if (parts[0] === 'shared' && parts[1] && parts[2] && parts[3]) {
    const content = parts[2];
    if (content !== 'trip' && content !== 'album' && content !== 'photo') return APP;
    const token = new URLSearchParams(search).get('t') ?? undefined;
    return { kind: 'shared', owner: parts[1], content, item: parts[3], token };
  }

  return APP;
};
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- route.test`
Expected: PASS, 6/6.

- [ ] **Step 5: Write the GitHub Pages SPA fallback**

`public/404.html` is copied as-is by Vite, not built — no `import.meta.env` inside it, so the base path is written literally:

```html
<!-- public/404.html -->
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <script>
      // GitHub Pages has no server-side rewrite: a direct load of /my-world/u/ivan-petrov hits
      // this file. Stash the real path and bounce to index.html, which restores it below.
      sessionStorage.setItem('my-world:redirect', location.pathname + location.search);
      location.replace('/my-world/');
    </script>
  </head>
  <body></body>
</html>
```

In `index.html`, add this inline script as the first thing in `<head>`, before any other script tag:

```html
<script>
  (function () {
    var redirect = sessionStorage.getItem('my-world:redirect');
    if (redirect) {
      sessionStorage.removeItem('my-world:redirect');
      history.replaceState(null, '', redirect);
    }
  })();
</script>
```

- [ ] **Step 6: Wire the route into `boot.ts`**

`src/app/boot.ts` currently always builds the interactive `World`. Add a `route` field so `App.tsx` (Task 9) can branch before doing that work:

```typescript
import { routeOf } from './route';
import type { Route } from './route';

export { routeOf };
export type { Route };
```

Add these two exports near the top of `boot.ts`, after the existing `export { demoUrl };` line — `loadWorld` itself is unchanged; the route is read separately, before `App.tsx` decides whether to call `loadWorld` at all (Task 9 does that wiring).

- [ ] **Step 7: Run the full suite and typecheck**

Run: `npm run check`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add src/app/route.ts src/app/route.test.ts src/app/boot.ts public/404.html index.html
git commit -m "feat: pathname-based routing for /u/<handle> and /shared/..., with a GH Pages fallback"
```

---

### Task 7: Public handle — generation, signup, and the account form

**Files:**
- Create: `src/backend/handle.ts`
- Create: `src/backend/handle.test.ts`
- Modify: `src/backend/types.ts`
- Modify: `src/backend/supabase.ts`
- Modify: `src/features/forms/AccountForm.tsx`

**Interfaces:**
- Consumes: `profiles` table from Task 1 (`user_id`, `handle`, public read, owner write).
- Produces: `slugify(name: string): string` (lowercase, `[a-z0-9-]`, collapsed hyphens); `Account.handle: string`; `Auth.update` gains an optional `handle` field. Task 10/11 read `Account.handle` to build the profile link and the copy-link UI.

- [ ] **Step 1: Write the failing test**

```typescript
// src/backend/handle.test.ts
import { describe, expect, it } from 'vitest';
import { slugify } from './handle';

describe('slugify', () => {
  it('lowercases and hyphenates', () => {
    expect(slugify('Ivan Petrov')).toBe('ivan-petrov');
  });

  it('strips characters outside a-z0-9-', () => {
    expect(slugify("O'Brien & Co.")).toBe('obrien-co');
  });

  it('collapses repeated separators and trims the ends', () => {
    expect(slugify('  Too   Many   Spaces  ')).toBe('too-many-spaces');
  });

  it('falls back to "traveller" for a name with nothing left to slugify', () => {
    expect(slugify('★★★')).toBe('traveller');
  });

  it('clamps to 30 characters', () => {
    expect(slugify('a'.repeat(50)).length).toBe(30);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- handle.test`
Expected: FAIL — module `./handle` not found.

- [ ] **Step 3: Implement**

```typescript
// src/backend/handle.ts
/** A URL-safe slug from an account's name, for its public profile at /u/<handle>.
 *  Uniqueness (appending -2, -3, ...) is the caller's job, since only the caller knows
 *  which handles are already taken. */
export const slugify = (name: string): string => {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 30)
    .replace(/-+$/, '');
  return base || 'traveller';
};
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- handle.test`
Expected: PASS, 5/5.

- [ ] **Step 5: Wire the handle into signup, the account type, and `update`**

In `src/backend/types.ts`, add `handle: string` to `Account`:

```typescript
export interface Account {
  id: string;
  name: string;
  email: string;
  home: Place;
  handle: string;
}
```

Add `handle?: string` to the `update` method's input:

```typescript
  update(input: {
    name: string;
    email: string;
    home: Place;
    password?: string;
    handle?: string;
  }): Promise<void>;
```

In `src/backend/supabase.ts`, import `slugify` from `./handle`. Add a helper next to `accountOf`:

```typescript
const uniqueHandle = async (client: SupabaseClient, base: string): Promise<string> => {
  for (let suffix = 0; ; suffix++) {
    const candidate = suffix === 0 ? base : `${base}-${suffix + 1}`;
    const { data } = await client.from('profiles').select('user_id').eq('handle', candidate).maybeSingle();
    if (!data) return candidate;
  }
};
```

Change `accountOf` to read the handle from `profiles` — since it needs a query, `accountOf` becomes async and callers (`session()`) await it:

```typescript
const accountOf = async (client: SupabaseClient, user: AuthUser): Promise<Account> => {
  const meta = user.user_metadata as { name?: unknown; home?: unknown };
  const { data: profile } = await client.from('profiles').select('handle').eq('user_id', user.id).maybeSingle();
  return {
    id: user.id,
    email: user.email ?? '',
    name: typeof meta.name === 'string' ? meta.name : (user.email ?? ''),
    home: cleanPlace(meta.home) ?? DEMO_HOME,
    handle: (profile as { handle: string } | null)?.handle ?? '',
  };
};
```

Update `authOf`'s `session()` to await it and pass `client`:

```typescript
  async session() {
    const { data, error } = await client.auth.getSession();
    fail(error);
    return data.session ? accountOf(client, data.session.user) : null;
  },
```

Update `signUp` to create the `profiles` row right after a successful signup (only when the session exists — a `confirm-email` account has no session yet to write with, so its handle is created on first real sign-in instead):

```typescript
  async signUp({ email, password, name, home }) {
    const { data, error } = await client.auth.signUp({
      email,
      password,
      options: { data: { name, home } },
    });
    fail(error);
    if (data.session) {
      const handle = await uniqueHandle(client, slugify(name));
      await client.from('profiles').insert({ user_id: data.session.user.id, handle });
    }
    return data.session ? 'signed-in' : 'confirm-email';
  },
```

Update `signIn` to backfill a handle for an account that confirmed its email and is signing in for the first time (no `profiles` row yet):

```typescript
  async signIn(email, password) {
    const { data, error } = await client.auth.signInWithPassword({ email, password });
    fail(error);
    if (data.user) {
      const { data: existing } = await client
        .from('profiles')
        .select('user_id')
        .eq('user_id', data.user.id)
        .maybeSingle();
      if (!existing) {
        const meta = data.user.user_metadata as { name?: unknown };
        const name = typeof meta.name === 'string' ? meta.name : email;
        const handle = await uniqueHandle(client, slugify(name));
        await client.from('profiles').insert({ user_id: data.user.id, handle });
      }
    }
  },
```

Update `update` to accept and write a new handle:

```typescript
  async update({ name, email, home, password, handle }) {
    const { error } = await client.auth.updateUser({
      email,
      ...(password ? { password } : {}),
      data: { name, home },
    });
    fail(error);
    if (handle) {
      const { data: session } = await client.auth.getSession();
      const accountId = session.session?.user.id;
      if (accountId) {
        const { error: handleError } = await client
          .from('profiles')
          .update({ handle, updated_at: new Date().toISOString() })
          .eq('user_id', accountId);
        fail(handleError);
      }
    }
  },
```

- [ ] **Step 6: Add the field to `AccountForm.tsx`**

Modify `src/features/forms/AccountForm.tsx:16-22` (the `useState` block) to add a handle field, shown only when there is a backend (sharing needs one):

```typescript
  const [name, setName] = useState(user?.name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [handle, setHandle] = useState(user?.handle ?? '');
  const [pass, setPass] = useState('');
```

Modify the `submit` function's `fields` object (around line 39-43) to include `handle` when it changed:

```typescript
    const fields = {
      name: name.trim(),
      email: email.trim(),
      home: { name: city, country, countryId, lat, lon },
      ...(auth && handle.trim() && handle.trim() !== user.handle ? { handle: handle.trim() } : {}),
    };
```

(`auth` is defined a few lines below in the current file — move the `const auth = backend()?.auth;` line above this block so it is in scope here.)

Add the field to the form JSX, right after the email field (`src/features/forms/AccountForm.tsx`, after the `fMail` label block), only when `backend()` exists:

```tsx
      {backend() && (
        <label className="sheet__field" htmlFor="fHandle">
          Public handle (my-world.../u/...)
          <input
            id="fHandle"
            value={handle}
            onChange={(event) => setHandle(event.target.value.toLowerCase())}
          />
        </label>
      )}
```

- [ ] **Step 7: Run the full suite and typecheck**

Run: `npm run check`
Expected: all green. (`accountOf` becoming `async` changes its call sites inside `supabase.ts` only — `session()` is the one caller, already updated above.)

- [ ] **Step 8: Commit**

```bash
git add src/backend/handle.ts src/backend/handle.test.ts src/backend/types.ts src/backend/supabase.ts src/features/forms/AccountForm.tsx
git commit -m "feat: public handle — slug generation, signup/sign-in backfill, account form field"
```

---

### Task 8: Privacy picker and copy-link UI

**Files:**
- Create: `src/features/forms/PrivacyField.tsx`
- Create: `src/features/forms/PrivacyField.test.tsx`
- Modify: `src/features/forms/AlbumForm.tsx`
- Modify: `src/features/forms/TripForm.tsx`
- Modify: `src/features/forms/PhotoForm.tsx`

**Interfaces:**
- Consumes: `Storage.getVisibility`/`setVisibility` from Task 3; `backend()` from `src/backend/session.ts` (existing); `Account.handle` from Task 7.
- Produces: `PrivacyField({ kind: VisibilityKind; itemId: Id }): JSX.Element | null` — renders nothing without a backend; otherwise a level picker and, at `link`, a copy-link button building `${location.origin}${import.meta.env.BASE_URL}shared/<accountId>/<kind>/<itemId>?t=<token>`.

- [ ] **Step 1: Write the failing test**

```tsx
// src/features/forms/PrivacyField.test.tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as session from '@/backend/session';
import { PrivacyField } from './PrivacyField';

vi.mock('@/backend/session');

const storage = (overrides: Partial<{ level: string; linkToken: string | null }> = {}) => ({
  getVisibility: vi.fn().mockResolvedValue({ level: overrides.level ?? 'private', linkToken: overrides.linkToken ?? null }),
  setVisibility: vi.fn().mockImplementation((_kind, _id, level) =>
    Promise.resolve({ level, linkToken: level === 'link' ? 'tok-123' : null }),
  ),
});

beforeEach(() => {
  vi.mocked(session.backend).mockReturnValue({
    auth: {} as never,
    storage: () => storage() as never,
  });
});
afterEach(() => vi.clearAllMocks());

describe('PrivacyField', () => {
  it('renders nothing without a backend', async () => {
    vi.mocked(session.backend).mockReturnValue(null);
    const { container } = render(<PrivacyField kind="album" itemId="a1" accountId="acc-1" />);
    await waitFor(() => expect(container).toBeTruthy());
    expect(container.querySelector('select')).toBeNull();
  });

  it('loads the current level', async () => {
    vi.mocked(session.backend).mockReturnValue({
      auth: {} as never,
      storage: () => storage({ level: 'public' }) as never,
    });
    render(<PrivacyField kind="album" itemId="a1" accountId="acc-1" />);
    await waitFor(() => expect(screen.getByRole('combobox')).toHaveValue('public'));
  });

  it('saves a new level and shows the copy-link button once it is link', async () => {
    const fakeStorage = storage({ level: 'private' });
    vi.mocked(session.backend).mockReturnValue({ auth: {} as never, storage: () => fakeStorage as never });
    render(<PrivacyField kind="album" itemId="a1" accountId="acc-1" />);
    await waitFor(() => screen.getByRole('combobox'));
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'link' } });
    await waitFor(() => expect(fakeStorage.setVisibility).toHaveBeenCalledWith('album', 'a1', 'link'));
    await waitFor(() => expect(screen.getByText(/copy link/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- PrivacyField.test`
Expected: FAIL — module `./PrivacyField` not found.

- [ ] **Step 3: Implement**

```tsx
// src/features/forms/PrivacyField.tsx
import { useEffect, useState } from 'react';
import type { Id } from '@/data/types';
import { backend } from '@/backend/session';
import type { VisibilityKind, VisibilityLevel } from '@/backend/types';

const LABEL: Record<VisibilityLevel, string> = {
  private: 'Private — only me',
  link: 'Anyone with the link',
  registered: 'Anyone signed in',
  public: 'Anyone',
};

/** The privacy picker for one trip, album, or photo; nothing without a backend, since sharing
 *  needs a server to hold the setting and answer other people's requests. */
export function PrivacyField({
  kind,
  itemId,
  accountId,
}: {
  kind: VisibilityKind;
  itemId: Id;
  accountId: string;
}) {
  const storage = backend()?.storage(accountId);
  const [level, setLevel] = useState<VisibilityLevel>('private');
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!storage) return;
    let live = true;
    storage.getVisibility(kind, itemId).then((setting) => {
      if (!live) return;
      setLevel(setting.level);
      setLinkToken(setting.linkToken);
    });
    return () => {
      live = false;
    };
  }, [storage, kind, itemId]);

  if (!storage) return null;

  const change = async (next: VisibilityLevel) => {
    setLevel(next);
    const saved = await storage.setVisibility(kind, itemId, next);
    setLinkToken(saved.linkToken);
  };

  const link =
    linkToken &&
    `${location.origin}${import.meta.env.BASE_URL}shared/${accountId}/${kind}/${itemId}?t=${linkToken}`;

  return (
    <label className="sheet__field" htmlFor="fPrivacy">
      Visibility
      <select id="fPrivacy" value={level} onChange={(event) => void change(event.target.value as VisibilityLevel)}>
        {(Object.keys(LABEL) as VisibilityLevel[]).map((one) => (
          <option key={one} value={one}>
            {LABEL[one]}
          </option>
        ))}
      </select>
      {level === 'link' && link && (
        <button
          type="button"
          className="sheet__btn"
          onClick={() => {
            void navigator.clipboard.writeText(link);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? 'Copied!' : 'Copy link'}
        </button>
      )}
    </label>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- PrivacyField.test`
Expected: PASS, 3/3.

- [ ] **Step 5: Wire it into `AlbumForm.tsx`, `TripForm.tsx`, `PhotoForm.tsx`**

In `src/features/forms/AlbumForm.tsx`, import `PrivacyField` and the current account id:

```typescript
import { PrivacyField } from './PrivacyField';
import { userStore } from '@/state/user';
```

Add, right after the `{!album && (...)}` DropZone block (only when editing an existing album, and only with a signed-in account id):

```tsx
      {album && userStore.get().user && (
        <PrivacyField kind="album" itemId={album.id} accountId={userStore.get().user!.id} />
      )}
```

`user` from `userStore` today is `{ name, email, home } | null` (see `App.tsx`'s use of `account`), with no `id`. Check `src/state/user.ts`'s `userStore` shape before this step — if it has no account id, thread the id in via the `world` prop instead (`AlbumForm` already receives `world: World`; `world` has no account id today either). Add an `accountId: string | null` field to `World` in `src/app/boot.ts` (set from `account?.id` next to where `userStore.set` already runs in `loadWorld`), and use `world.accountId` here instead of `userStore`:

```tsx
      {album && world.accountId && <PrivacyField kind="album" itemId={album.id} accountId={world.accountId} />}
```

Apply the same pattern to `src/features/forms/TripForm.tsx` (after the "Albums" checklist block, only when `trip` is set):

```tsx
      {trip && world.accountId && <PrivacyField kind="trip" itemId={trip.id} accountId={world.accountId} />}
```

And to `src/features/forms/PhotoForm.tsx` (after the caption field, only for an `own`-kind photo with an account id):

```tsx
      {photo.kind === 'own' && world.accountId && (
        <PrivacyField kind="photo" itemId={photo.id} accountId={world.accountId} />
      )}
```

(`PhotoForm` needs `world` in scope for this — it is already a prop.)

- [ ] **Step 6: Add `accountId` to `World`**

In `src/app/boot.ts`, add `accountId: string | null` to the `World` interface, and set it in `loadWorld`, next to the existing `home` field in the returned object:

```typescript
export interface World {
  earth: EarthGeo;
  lights: Light[];
  archive: Archive;
  home: Place;
  accountId: string | null;
  credits: ReadonlyMap<string, Credit>;
}
```

```typescript
  return {
    earth,
    lights: lightsFromRows(rows),
    archive,
    home: user?.home ?? DEMO_HOME,
    accountId: back && account ? account.id : null,
    credits: new Map(credits.map((credit) => [credit.file, credit])),
  };
```

- [ ] **Step 7: Run the full suite and typecheck**

Run: `npm run check`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add src/features/forms/PrivacyField.tsx src/features/forms/PrivacyField.test.tsx src/features/forms/AlbumForm.tsx src/features/forms/TripForm.tsx src/features/forms/PhotoForm.tsx src/app/boot.ts
git commit -m "feat: privacy picker and copy-link button on trip/album/photo forms"
```

---

### Task 9: Shared and profile views — wiring `App.tsx`

**Files:**
- Modify: `src/app/App.tsx`
- Create: `src/app/SharedView.tsx`
- Create: `src/app/SharedView.test.tsx`
- Modify: `src/app/boot.ts`

**Interfaces:**
- Consumes: `routeOf` from Task 6; `sharedRepository` from Task 5; `fetchPublicTrips` from Task 4; `loadWorld` from `boot.ts` (existing, extended below).
- Produces: `loadWorld(route?: Route): Promise<World>` — with a `{ kind: 'shared', ... }` route, builds `World` from `sharedRepository` instead of the local/remote/demo choice; `SharedView` renders a public profile list (`{ kind: 'profile' }`) or the neutral "not available" state.

- [ ] **Step 1: Write the failing test**

```tsx
// src/app/SharedView.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import * as sharing from '@/backend/sharing';
import { SharedView } from './SharedView';

vi.mock('@/backend/sharing');

describe('SharedView', () => {
  it('lists public trips for a profile route', async () => {
    vi.mocked(sharing.fetchPublicTrips).mockResolvedValue([{ id: 't1', name: 'Peru' }]);
    render(<SharedView route={{ kind: 'profile', handle: 'ivan-petrov' }} />);
    await waitFor(() => expect(screen.getByText('Peru')).toBeInTheDocument());
  });

  it('shows the neutral not-available state for an empty profile', async () => {
    vi.mocked(sharing.fetchPublicTrips).mockResolvedValue([]);
    render(<SharedView route={{ kind: 'profile', handle: 'nobody' }} />);
    await waitFor(() => expect(screen.getByText(/not available/i)).toBeInTheDocument());
  });
});
```

(This task's second half — rendering a `{ kind: 'shared' }` route through the full globe `Stage` — is covered by Task 10's manual Playwright pass, not a unit test: it needs the real `World`/`Stage` machinery, which `remote-repository.test.ts` and friends already establish is exercised live rather than mounted in `vitest`.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- SharedView.test`
Expected: FAIL — module `./SharedView` not found.

- [ ] **Step 3: Implement**

`SharedView` needs a handle → owner id lookup for the profile case. Add one function to `src/backend/handle.ts`:

```typescript
// append to src/backend/handle.ts
import { backendConfig } from './config';

/** Resolves a public handle to the account id behind it, straight against PostgREST (the
 *  `profiles` table is publicly readable — see the migration), no Edge Function needed. */
export const resolveHandle = async (handle: string): Promise<string | null> => {
  const config = backendConfig();
  if (!config) return null;
  const response = await fetch(
    `${config.url}/rest/v1/profiles?handle=eq.${encodeURIComponent(handle)}&select=user_id`,
    { headers: { apikey: config.key, authorization: `Bearer ${config.key}` } },
  );
  if (!response.ok) return null;
  const rows = (await response.json()) as Array<{ user_id: string }>;
  return rows[0]?.user_id ?? null;
};
```

```tsx
// src/app/SharedView.tsx
import { useEffect, useState } from 'react';
import { fetchPublicTrips } from '@/backend/sharing';
import type { SharedTrip } from '@/backend/sharing';
import { resolveHandle } from '@/backend/handle';
import type { Route } from './route';

/** The two routes that never load the globe: a public profile's list of trips, or the flat
 *  "not available" state (a private/revoked item, an unknown handle, or a bad link alike —
 *  never distinguished, so a private item's existence is never confirmed by the response). */
export function SharedView({ route }: { route: Extract<Route, { kind: 'profile' }> }) {
  const [trips, setTrips] = useState<SharedTrip[] | null>(null);

  useEffect(() => {
    let live = true;
    (async () => {
      const ownerId = await resolveHandle(route.handle);
      const list = ownerId ? await fetchPublicTrips(ownerId) : [];
      if (live) setTrips(list);
    })();
    return () => {
      live = false;
    };
  }, [route.handle]);

  if (trips === null) return <div className="shared shared--loading">Loading…</div>;
  if (trips.length === 0) {
    return (
      <div className="shared shared--empty">
        <p>Not available.</p>
      </div>
    );
  }

  return (
    <div className="shared">
      <h1>@{route.handle}</h1>
      <ul>
        {trips.map((trip) => (
          <li key={trip.id}>
            <a href={`shared/${route.handle}/trip/${trip.id}`}>{trip.name}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- SharedView.test`
Expected: PASS, 2/2.

- [ ] **Step 5: Wire `loadWorld` to build a `World` from `sharedRepository` for a `{ kind: 'shared' }` route**

Modify `src/app/boot.ts`'s `loadWorld` to accept the route and branch before picking a repository. Change its signature and the repository selection:

```typescript
export const loadWorld = async (route: Route = { kind: 'app' }): Promise<World> => {
  const [topology, credits, rows] = await Promise.all([
    fetchJson<WorldTopology>('countries-110m.json'),
    fetchJson<Credit[]>('photos.json'),
    fetchJson<LightRow[]>('lights.json'),
  ]);
  const earth = earthFromTopology(topology);

  if (route.kind === 'shared' && route.content !== 'photo') {
    const { sharedRepository } = await import('@/data/shared-repository');
    const repo = sharedRepository(route.owner, route.content, route.item, { token: route.token });
    const archive = linkArchive(await repo.load());
    setSource(archive, repo);
    return {
      earth,
      lights: lightsFromRows(rows),
      archive,
      home: DEMO_HOME,
      accountId: null,
      credits: new Map(credits.map((credit) => [credit.file, credit])),
    };
  }

  const back = await startBackend().catch(() => null);
  const account = back ? await back.auth.session().catch(() => null) : null;
  if (back) {
    userStore.set({
      user: account ? { name: account.name, email: account.email, home: account.home } : null,
    });
  }
  const { user } = userStore.get();
  const repo =
    back && account
      ? remoteRepository(back.storage(account.id), credits)
      : user && !back
        ? localRepository(credits)
        : demoRepository(credits);
  const archive = linkArchive(await repo.load());
  setSource(archive, repo);
  return {
    earth,
    lights: lightsFromRows(rows),
    archive,
    home: user?.home ?? DEMO_HOME,
    accountId: back && account ? account.id : null,
    credits: new Map(credits.map((credit) => [credit.file, credit])),
  };
};
```

(A `{ kind: 'shared', content: 'photo' }` route — sharing a single photo on its own — falls through to the normal branch today, which is wrong; narrowing this in a later pass is fine, since the plan's E2E coverage in Task 10 only exercises trip/album sharing. Note this in the ledger as a known gap rather than silently mishandling it: for now a lone shared photo route renders the ordinary app/demo instead of that photo — acceptable for this sub-project, called out for Friends/Likes/Comments to revisit if a "share one photo" flow is ever wanted.)

- [ ] **Step 6: Branch in `App.tsx` before building the interactive world**

Modify `src/app/App.tsx`. The route is read once, at module scope; the early return for a profile route sits *after* the hooks (`useState`/`useEffect` must run unconditionally on every render — an early return above them would break React's rules of hooks):

```tsx
import { useCallback, useEffect, useState } from 'react';
import { Header } from '@/features/header/Header';
import { loadWorld, routeOf } from './boot';
import type { World } from './boot';
import { Splash } from './Splash';
import { Stage } from './Stage';
import { SharedView } from './SharedView';
import './app.scss';

type Boot = { status: 'loading' } | { status: 'ready'; world: World } | { status: 'failed' };

const route = routeOf(location.pathname, location.search, import.meta.env.BASE_URL);

export function App() {
  const [boot, setBoot] = useState<Boot>({ status: 'loading' });
  const [stageUp, setStageUp] = useState(false);
  const letIn = useCallback(() => setStageUp(true), []);

  useEffect(() => {
    if (route.kind === 'profile') return;
    let live = true;
    loadWorld(route).then(
      (world) => {
        if (live) setBoot({ status: 'ready', world });
      },
      (error: unknown) => {
        console.error(error);
        if (live) setBoot({ status: 'failed' });
      },
    );
    return () => {
      live = false;
    };
  }, []);

  if (route.kind === 'profile') return <SharedView route={route} />;

  return (
    <>
      {boot.status === 'ready' && stageUp && <Stage world={boot.world} />}
      {boot.status !== 'failed' && <Splash ready={boot.status === 'ready'} onRelease={letIn} />}
      {boot.status === 'failed' && (
        <div className="boot" role="alert">
          <p>The map did not load.</p>
          <button type="button" onClick={() => location.reload()}>
            Try again
          </button>
        </div>
      )}
      <Header world={boot.status === 'ready' ? boot.world : null} />
    </>
  );
}
```

- [ ] **Step 7: Run the full suite and typecheck**

Run: `npm run check`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add src/app/App.tsx src/app/SharedView.tsx src/app/SharedView.test.tsx src/app/boot.ts
git commit -m "feat: render a public profile or a shared trip/album from the URL"
```

---

### Task 10: Styling and the "not available" state

**Files:**
- Create: `src/app/shared.scss`
- Modify: `src/app/SharedView.tsx`
- Modify: `src/app/App.tsx`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new (visual only).

- [ ] **Step 1: Add a stylesheet matching the app's existing dark, minimal look**

```scss
// src/app/shared.scss
.shared {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #eee;
  background: #0b0d12;
  font-family: 'Space Grotesk', sans-serif;

  h1 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
  }

  ul {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 0;
  }

  a {
    color: #eee;
    text-decoration: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  }

  &--empty p,
  &--loading {
    opacity: 0.7;
  }
}
```

- [ ] **Step 2: Import it and check the visual result**

Add `import './shared.scss';` to the top of `src/app/SharedView.tsx`. This task has no new logic, so there is no RED/GREEN step — verify visually in Task 11's manual pass instead.

- [ ] **Step 3: Run the full suite and typecheck**

Run: `npm run check`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add src/app/shared.scss src/app/SharedView.tsx
git commit -m "style: dark minimal styling for the shared profile view"
```

---

### Task 11: Manual verification and README

**Files:**
- Modify: `supabase/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the whole feature, end to end.
- Produces: nothing new — this task is verification and documentation.

- [ ] **Step 1: Update `supabase/README.md`'s "What is stored" table**

Add two rows:

```markdown
| `public.content_visibility` | who can see a trip/album/photo, and its link token | its owner (read/write); read-only server-side by the Edge Functions |
| `public.profiles` | the account's public handle | readable by anyone; its owner writes it |
```

- [ ] **Step 2: Update the root `README.md`**

Add a short paragraph after the existing backend description (find it via `grep -n "Supabase" README.md`), explaining that with a backend, any trip/album/photo can be made visible to others at `private`/`link`/`registered`/`public`, with a link to `supabase/README.md` for setup.

- [ ] **Step 3: Manual Playwright walkthrough**

Using the browser automation tool against a local `npm run dev` build pointed at the real Supabase project from the earlier backend verification session:

1. Sign in as the existing test account (or a fresh one), open an album, set its visibility to `public`, confirm the picker shows "Anyone" after a reload of the form.
2. Set a second album to `link`, click "Copy link", read the clipboard value directly (`navigator.clipboard.readText()` or by pasting into the address bar) to get the URL.
3. Open a second browser context with no cookies/session (incognito/new context).
4. Navigate to `/u/<handle>` — confirm the public trip (if its containing trip is also public) or the public album's page lists what is expected, and nothing private.
5. Navigate to the `link`-level album's copied URL — confirm it renders the album read-only (globe + album panel, no edit buttons, no "New album" affordances).
6. Navigate to a made-up `/shared/<owner>/album/does-not-exist` URL — confirm the neutral "not available" page, not an error or a blank screen.
7. From the first (owner) session, set the `public` album back to `private`; reload the profile page from Step 4 — confirm it is gone from the list.

Expected: every step matches the description above; no console errors in either browser context.

- [ ] **Step 4: Commit**

```bash
git add README.md supabase/README.md
git commit -m "docs: document sharing/visibility in both READMEs"
```
