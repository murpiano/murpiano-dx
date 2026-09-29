# Travel globe, part 4: the archive — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the archive: a full-screen layer over the paused globe with Trips, Albums, Countries, Cities and Years, their pages (trip route, country, city, year, album photo grid with folders), "Show on map" for albums, years and trips, the return to the archive page 5 s after a year or trip tour ends by itself, and links into the archive from the panel, the photo window and the timeline.

**Architecture:** The archive is a stack of pages in `appStore` (`src/state/archive-nav.ts`, pure). Everything a page shows comes from a pure model (`src/archive/pages.ts`). The director signals a tour that ended by itself (`tourDone`); a small pure rule (`src/archive/return.ts`) tells a finished tour from an interrupted one, and a hook brings the archive back. React renders it in `src/features/archive/`.

**Tech Stack:** as in parts 1–3.

**Spec:** [`docs/design/2026-09-29-travel-globe.md`](../../design/2026-09-29-travel-globe.md) — sections 4 and 5, plus the archive links in 3.5–3.7 and the Esc chain in 3.9. Reference: `docs/design/prototype/flight.html` (archive 1345–1544, cards 1511–1565, 1627–1655; CSS 168–248).

**Out of this plan:** editing (New trip, Edit trip, Add album, Make it a trip, New album, Edit album, Add photos, the photo tiles' "Edit"), and the log-in prompt that the demo shows instead of the archive — both plan 5. Until then the archive opens for everyone; plan 5 adds the gate in `goArchive`, the single way in.

## Global Constraints

- Branch `feat/travel-globe`; never push to `main`. `npm run check` green after every task. Style as before.
- Top bar: ✕ and ← at the left, then tabs Trips, Albums, Countries, Cities, Years; below them breadcrumbs, title, subtitle, action buttons.
- Trips: cards (cover, name, date span, places), newest first; an album in no trip shows as a trip of its own. Trip page: the route (`00 Start home · Kyiv, Ukraine` or a city; each place once in the order first reached, with its album folders; `NN End …`); action Show on map.
- Albums: all albums grouped by year, latest year first. Countries → Country: city cards. Cities → City: albums grouped by year, latest first. Years → Year: that year's folders; Show on map. Album: photo grid, each tile with likes, comment count and caption; Show on map. Folders: a stack of three photos in a folder that fans out on hover.
- The archive pauses the world. Esc goes one step back (after form, menu, photo window).
- Show on map: album — its moment, place in focus, no autoplay; year — the year, first album in focus, tour plays; trip — the trip's stretch, the plane from its start through its albums to its end. 5 s after a year or trip tour finishes by itself, the archive page it was started from fades back in (1.4 s); not if the owner interrupted the tour, or while the photo window or a form is open.
- Links: a second click on the picked year (timeline) and on the current year (panel) open the year / the city; the panel's city, country, album and trip names, the photo window's country, city and album open their pages.

## Review Focus

- **A trip whose albums were all removed, or a page whose target is gone** — the page steps back instead of rendering nothing. Pinned in Task 2 (`findPage` returns null) and Task 4 (the archive steps back).
- **A tour interrupted by the owner** (Esc, ❚❚, a new range, a light outside it) — no return to the archive. Pinned in Task 3 (`tourOutcome`).
- **The photo window opened over the archive** — Esc closes the photo first, then steps back in the archive. Pinned in Task 1 (`escapeTarget`).
- **An album with no photos** — its tile area says so, its folder shows an empty folder, nothing breaks. Pinned in Task 2 (`folderPhotos` of an empty album).
- **Two trips in the same month, and trips with no albums yet** — ordering is stable, empty ones stay on top. Pinned in Task 2 (`journeys`).

---

## File map

Created:

```
src/state/archive-nav.ts, archive-nav.test.ts   pages stack: open, back, close
src/archive/pages.ts, pages.test.ts             journeys, routes, groups, labels, covers
src/archive/return.ts, return.test.ts           finished vs interrupted tour
src/features/archive/Archive.tsx, archive.scss  the layer and its pages
src/features/archive/useArchiveReturn.ts        brings the archive back after a tour
src/features/archive/links.ts                   goArchive, showOnMap
```

Modified: `src/state/app-state.ts`, `src/state/layers.ts` (+test), `src/tour/director.ts` (+test), `src/features/keys/useKeys.ts`, `src/features/panel/AlbumPanel.tsx`, `src/features/panel/panel.scss`, `src/features/lightbox/Lightbox.tsx`, `src/features/lightbox/lightbox.scss`, `src/features/timeline/Timeline.tsx`, `src/app/Stage.tsx`.

---

### Task 1: The archive's pages stack

**Files:**
- Modify: `src/state/app-state.ts`, `src/state/layers.ts`, `src/state/layers.test.ts`
- Create: `src/state/archive-nav.ts`
- Test: `src/state/archive-nav.test.ts`

**Interfaces:**
- Produces:
  - `type ArchivePage = { kind: 'trips' } | { kind: 'trip'; id: string } | { kind: 'albums' } | { kind: 'album'; id: string } | { kind: 'countries' } | { kind: 'country'; id: string } | { kind: 'cities' } | { kind: 'city'; key: string } | { kind: 'years' } | { kind: 'year'; year: number }`
  - `type ArchiveSection = 'trips' | 'albums' | 'countries' | 'cities' | 'years'`
  - `interface ArchiveView { stack: ArchivePage[]; slow: boolean }`; `AppState.archive: ArchiveView | null`, `AppState.tourDone: number`
  - `openArchive(store, page, fresh, slow?)`, `backArchive(store)`, `closeArchive(store)`, `sectionOf(page): ArchiveSection`, `SECTIONS: { key: ArchiveSection; label: string }[]`
  - `escapeTarget` returns `'menu' | 'photo' | 'archive' | 'journey'`; the world is paused while the photo window or the archive is open.

- [ ] **Step 1: Extend the app state**

In `src/state/app-state.ts` add before `AppState`:

```ts
/** A page of the archive. */
export type ArchivePage =
  | { kind: 'trips' }
  | { kind: 'trip'; id: string }
  | { kind: 'albums' }
  | { kind: 'album'; id: string }
  | { kind: 'countries' }
  | { kind: 'country'; id: string }
  | { kind: 'cities' }
  | { kind: 'city'; key: string }
  | { kind: 'years' }
  | { kind: 'year'; year: number };

/** The archive over the globe: the pages walked, the last one shown. */
export interface ArchiveView {
  stack: ArchivePage[];
  /** Fading back in slowly after a tour. */
  slow: boolean;
}
```

add to `AppState`:

```ts
  /** The archive, open over the globe. */
  archive: ArchiveView | null;
  /** Counts the year and trip tours that ended by themselves. */
  tourDone: number;
```

and to `INITIAL_STATE`: `archive: null, tourDone: 0,`.

- [ ] **Step 2: Write the failing tests**

`src/state/archive-nav.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { INITIAL_STATE } from './app-state';
import type { AppState } from './app-state';
import { backArchive, closeArchive, openArchive, sectionOf } from './archive-nav';
import { createStore } from './store';

const setup = () => createStore<AppState>({ ...INITIAL_STATE });

describe('the archive stack', () => {
  it('opens on a page, pauses the world and closes the menus', () => {
    const store = setup();
    store.set({ menu: 'nav' });
    openArchive(store, { kind: 'trips' }, true);
    expect(store.get().archive).toEqual({ stack: [{ kind: 'trips' }], slow: false });
    expect(store.get().paused).toBe(true);
    expect(store.get().menu).toBeNull();
  });

  it('walks deeper and back one page at a time, then closes', () => {
    const store = setup();
    openArchive(store, { kind: 'cities' }, true);
    openArchive(store, { kind: 'city', key: 'paris' }, false);
    expect(store.get().archive?.stack).toHaveLength(2);
    backArchive(store);
    expect(store.get().archive?.stack).toEqual([{ kind: 'cities' }]);
    backArchive(store);
    expect(store.get().archive).toBeNull();
    expect(store.get().paused).toBe(false);
  });

  it('starts over with a fresh page', () => {
    const store = setup();
    openArchive(store, { kind: 'cities' }, true);
    openArchive(store, { kind: 'city', key: 'paris' }, false);
    openArchive(store, { kind: 'years' }, true);
    expect(store.get().archive?.stack).toEqual([{ kind: 'years' }]);
  });

  it('can fade back in slowly', () => {
    const store = setup();
    openArchive(store, { kind: 'year', year: 2023 }, true, true);
    expect(store.get().archive?.slow).toBe(true);
    closeArchive(store);
    expect(store.get().archive).toBeNull();
  });

  it('knows the section of every page', () => {
    expect(sectionOf({ kind: 'trip', id: 'x' })).toBe('trips');
    expect(sectionOf({ kind: 'album', id: 'x' })).toBe('albums');
    expect(sectionOf({ kind: 'country', id: '250' })).toBe('countries');
    expect(sectionOf({ kind: 'city', key: 'paris' })).toBe('cities');
    expect(sectionOf({ kind: 'year', year: 2020 })).toBe('years');
  });
});
```

In `src/state/layers.test.ts`, extend `escapeTarget`'s test — replace its body with:

```ts
    const store = setup();
    expect(escapeTarget(store.get())).toBe('journey');
    store.set({ archive: { stack: [{ kind: 'trips' }], slow: false } });
    expect(escapeTarget(store.get())).toBe('archive');
    openPhoto(store, 'a', 0, null);
    expect(escapeTarget(store.get())).toBe('photo');
    store.set({ menu: 'settings' });
    expect(escapeTarget(store.get())).toBe('menu');
```

and add to `describe('the photo window', ...)`:

```ts
  it('keeps the world paused when it closes over the archive', () => {
    const store = setup();
    store.set({ archive: { stack: [{ kind: 'trips' }], slow: false } });
    openPhoto(store, 'a', 0, null);
    closePhoto(store);
    finishPhoto(store);
    expect(store.get().paused).toBe(true);
  });
```

- [ ] **Step 3: Run them to see them fail**

Run: `npx vitest run src/state`
Expected: FAIL — `./archive-nav` not found; `escapeTarget` returns `'journey'` where `'archive'` is expected; the paused test fails.

- [ ] **Step 4: Implement**

`src/state/layers.ts` — replace `pausedFor` and `escapeTarget`, and export `pausedFor`:

```ts
/** The world clock stops while the photo window or the archive is open. */
export const pausedFor = (state: AppState): boolean => state.photo !== null || state.archive !== null;
```

```ts
/** What Esc closes, innermost first: form (plan 5), menu, photo, archive (one step), the journey. */
export type EscapeTarget = 'menu' | 'photo' | 'archive' | 'journey';

export const escapeTarget = (state: AppState): EscapeTarget =>
  state.menu ? 'menu' : state.photo ? 'photo' : state.archive ? 'archive' : 'journey';
```

`src/state/archive-nav.ts`:

```ts
import type { AppState, ArchivePage } from './app-state';
import { pausedFor } from './layers';
import type { Store } from './store';

type AppStore = Store<AppState>;

export type ArchiveSection = 'trips' | 'albums' | 'countries' | 'cities' | 'years';

export const SECTIONS: { key: ArchiveSection; label: string }[] = [
  { key: 'trips', label: 'Trips' },
  { key: 'albums', label: 'Albums' },
  { key: 'countries', label: 'Countries' },
  { key: 'cities', label: 'Cities' },
  { key: 'years', label: 'Years' },
];

export const sectionOf = (page: ArchivePage): ArchiveSection => {
  switch (page.kind) {
    case 'trips':
    case 'trip':
      return 'trips';
    case 'albums':
    case 'album':
      return 'albums';
    case 'countries':
    case 'country':
      return 'countries';
    case 'cities':
    case 'city':
      return 'cities';
    case 'years':
    case 'year':
      return 'years';
  }
};

/** Opens a page: on top of the walked ones, or `fresh` as the only one. */
export const openArchive = (store: AppStore, page: ArchivePage, fresh: boolean, slow = false) => {
  const current = store.get().archive;
  const stack = fresh || !current ? [page] : [...current.stack, page];
  store.set({ archive: { stack, slow }, menu: null });
  store.set({ paused: pausedFor(store.get()) });
};

/** One page back; from the first page, the archive closes. */
export const backArchive = (store: AppStore) => {
  const current = store.get().archive;
  if (!current) return;
  if (current.stack.length > 1) {
    store.set({ archive: { stack: current.stack.slice(0, -1), slow: false } });
    return;
  }
  closeArchive(store);
};

export const closeArchive = (store: AppStore) => {
  store.set({ archive: null });
  store.set({ paused: pausedFor(store.get()) });
};
```

- [ ] **Step 5: Run the tests and the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/state
git commit -m "feat(state): add the archive's pages stack and pause the world under it"
```

---

### Task 2: The archive's pages model

**Files:**
- Create: `src/archive/pages.ts`
- Test: `src/archive/pages.test.ts`

**Interfaces:**
- Consumes: `Archive`, `byDate`, `MONTHS`, `monthYear`, `endpointPlace`, `cityPhotos`, `Place`, `Endpoint`.
- Produces:
  - `interface Journey { id: string; name: string; start: Endpoint; end: Endpoint; albums: Album[]; real: boolean }`
  - `journeys(archive: Archive): Journey[]`, `journeyOfAlbum(archive, albumId): Journey | undefined`
  - `dateSpan(albums: Album[]): string`, `whenLabel(album: Album): string`, `plural(n: number, word: string): string`
  - `interface RouteStop { n: number; label: string; place: string; albums: Album[] }`, `tripRoute(journey, archive, home): RouteStop[]`
  - `albumsByYear(albums: Album[]): { year: number; albums: Album[] }[]` (latest year first, albums by date)
  - `folderPhotos(album: Album): PhotoRef[]` (up to three), `coverOf(albums: Album[]): PhotoRef | undefined`
  - `findPage(archive, page, home): PageData | null` — a discriminated union with what each page shows (see Step 3)

- [ ] **Step 1: Write the failing test**

`src/archive/pages.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { linkArchive } from '@/data/archive';
import { buildDemo, DEMO_HOME } from '@/data/demo';
import type { ArchiveData, Credit } from '@/data/types';
import {
  albumsByYear,
  coverOf,
  dateSpan,
  findPage,
  folderPhotos,
  journeyOfAlbum,
  journeys,
  plural,
  tripRoute,
  whenLabel,
} from './pages';

const file = fileURLToPath(new URL('../../public/demo/photos.json', import.meta.url));
const demoData = buildDemo(JSON.parse(readFileSync(file, 'utf8')) as Credit[]);
const archive = linkArchive(demoData);
const album = (title: string) => {
  const found = archive.albums.find((a) => a.title === title);
  if (!found) throw new Error(title);
  return found;
};

describe('journeys', () => {
  it('lists the trips newest first', () => {
    const list = journeys(archive);
    expect(list).toHaveLength(23);
    expect(list[0]?.name).toBe('Japan in autumn');
    expect(list[list.length - 1]?.name).toBe('First time abroad');
    expect(list.every((j) => j.real)).toBe(true);
  });

  it('shows an album in no trip as a trip of its own, and an empty trip on top', () => {
    const data: ArchiveData = {
      countries: demoData.countries,
      trips: [
        { id: 'empty', name: 'Someday', start: { home: true }, end: { home: true }, albumIds: [] },
        ...demoData.trips.slice(1),
      ],
    };
    const list = journeys(linkArchive(data));
    expect(list[0]?.name).toBe('Someday');
    const own = list.find((j) => !j.real);
    expect(own?.name).toBe('Paris 2016');
    expect(own?.albums.map((a) => a.title)).toEqual(['First trip abroad']);
  });

  it('finds the trip of an album', () => {
    expect(journeyOfAlbum(archive, album('Sakura week').id)?.name).toBe('Japan in bloom');
  });
});

describe('labels', () => {
  it('spans a month, months of a year, or years', () => {
    expect(dateSpan([album('Paris again')])).toBe('Apr 2022');
    expect(dateSpan([album('Gaudí & the sea'), album('Tram 28')])).toBe('Mar – Apr 2019');
    expect(dateSpan([album('Seven days in Manhattan'), album('Midnight sun')])).toBe(
      'Oct 2017 – Jun 2020',
    );
    expect(dateSpan([])).toBe('no albums yet');
  });

  it('names a moment and counts', () => {
    const a = album('Tram 28');
    expect(whenLabel(a)).toBe(`${a.day} Apr 2019, ${a.time}`);
    expect(plural(1, 'album')).toBe('1 album');
    expect(plural(3, 'city')).toBe('3 cities');
    expect(plural(2, 'place')).toBe('2 places');
  });
});

describe('tripRoute', () => {
  it('goes from the start through each place once to the end', () => {
    const japan = journeys(archive).find((j) => j.name === 'Japan in bloom');
    if (!japan) throw new Error('no trip');
    const route = tripRoute(japan, archive, DEMO_HOME);
    expect(route[0]).toEqual({ n: 0, label: 'Start', place: 'home · Kyiv, Ukraine', albums: [] });
    expect(route.slice(1, -1).map((s) => s.label).sort()).toEqual(['Kyoto', 'Tokyo']);
    expect(route.slice(1, -1).flatMap((s) => s.albums)).toHaveLength(3);
    expect(route[route.length - 1]).toEqual({
      n: 3,
      label: 'End',
      place: 'home · Kyiv, Ukraine',
      albums: [],
    });
  });
});

describe('groups and photos', () => {
  it('groups albums by year, latest first, each year by date', () => {
    const groups = albumsByYear(archive.cityByKey.get('paris')?.albums ?? []);
    expect(groups.map((g) => g.year)).toEqual([2025, 2022, 2016]);
    expect(groups[1]?.albums).toHaveLength(2);
  });

  it('puts up to three photos in a folder, none for an empty album', () => {
    expect(folderPhotos(album('Tram 28')).length).toBeLessThanOrEqual(3);
    expect(folderPhotos({ ...album('Tram 28'), photos: [] })).toEqual([]);
    expect(coverOf([{ ...album('Tram 28'), photos: [] }, album('Paris again')])).toEqual(
      album('Paris again').photos[0],
    );
  });
});

describe('findPage', () => {
  it('builds each page, or nothing when its target is gone', () => {
    expect(findPage(archive, { kind: 'trips' }, DEMO_HOME)?.kind).toBe('trips');
    expect(findPage(archive, { kind: 'city', key: 'paris' }, DEMO_HOME)?.kind).toBe('city');
    expect(findPage(archive, { kind: 'year', year: 2023 }, DEMO_HOME)?.kind).toBe('year');
    expect(findPage(archive, { kind: 'city', key: 'atlantis' }, DEMO_HOME)).toBeNull();
    expect(findPage(archive, { kind: 'trip', id: 'gone' }, DEMO_HOME)).toBeNull();
    expect(findPage(archive, { kind: 'album', id: 'gone' }, DEMO_HOME)).toBeNull();
    expect(findPage(archive, { kind: 'year', year: 1990 }, DEMO_HOME)).toBeNull();
  });

  it('counts what a country holds', () => {
    const page = findPage(archive, { kind: 'country', id: '724' }, DEMO_HOME);
    expect(page?.kind === 'country' && page.cities.map((c) => c.name)).toEqual([
      'Barcelona',
      'Madrid',
      'Seville',
    ]);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/archive/pages.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`src/archive/pages.ts`:

```ts
import type { Archive } from '@/data/archive';
import { byDate } from '@/data/order';
import { endpointPlace } from '@/data/trips';
import type { Album, City, Country, Endpoint, PhotoRef, Place } from '@/data/types';
import { MONTHS } from '@/lib/dates';
import type { ArchivePage } from '@/state/app-state';

/** A trip as the archive lists it; an album in no trip is a trip of its own (`real: false`). */
export interface Journey {
  id: string;
  name: string;
  start: Endpoint;
  end: Endpoint;
  /** Oldest first. */
  albums: Album[];
  real: boolean;
}

const HOME: Endpoint = { home: true };

/** Every trip, newest first; a trip with no albums yet stays on top. */
export const journeys = (archive: Archive): Journey[] => {
  const used = new Set<string>();
  const list: Journey[] = archive.trips.map((trip) => {
    const albums = trip.albumIds
      .map((id) => archive.albumById.get(id))
      .filter((a): a is Album => a !== undefined)
      .sort(byDate);
    for (const album of albums) used.add(album.id);
    return { id: trip.id, name: trip.name, start: trip.start, end: trip.end, albums, real: true };
  });
  for (const album of archive.albums) {
    if (used.has(album.id)) continue;
    list.push({
      id: `a:${album.id}`,
      name: `${album.city.name} ${album.year}`,
      start: HOME,
      end: HOME,
      albums: [album],
      real: false,
    });
  }
  return list.sort((a, b) => {
    const first = a.albums[0];
    const second = b.albums[0];
    if (!first) return -1;
    if (!second) return 1;
    return byDate(second, first);
  });
};

export const journeyOfAlbum = (archive: Archive, albumId: string): Journey | undefined =>
  journeys(archive).find((journey) => journey.albums.some((album) => album.id === albumId));

export const plural = (n: number, word: string): string =>
  `${n.toLocaleString('en')} ${n === 1 ? word : word === 'city' ? 'cities' : `${word}s`}`;

const month = (album: Album) => MONTHS[album.month - 1] ?? '';

/** "Apr 2022", "Mar – Apr 2019" or "Oct 2017 – Jun 2020". */
export const dateSpan = (albums: Album[]): string => {
  const sorted = [...albums].sort(byDate);
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  if (!first || !last) return 'no albums yet';
  if (first.year === last.year) {
    return first.month === last.month
      ? `${month(first)} ${first.year}`
      : `${month(first)} – ${month(last)} ${first.year}`;
  }
  return `${month(first)} ${first.year} – ${month(last)} ${last.year}`;
};

/** "3 Apr 2022, 10:00". */
export const whenLabel = (album: Album): string =>
  `${album.day} ${month(album)} ${album.year}, ${album.time}`;

export interface RouteStop {
  n: number;
  label: string;
  place: string;
  albums: Album[];
}

const endpointLabel = (end: Endpoint, archive: Archive, home: Place): string => {
  const place = endpointPlace(end, archive, home);
  return place.cityKey === null
    ? `home · ${place.name}, ${place.country}`
    : `${place.name}, ${place.country}`;
};

/** A trip as a route: its start, each place once in the order first reached, its end. */
export const tripRoute = (journey: Journey, archive: Archive, home: Place): RouteStop[] => {
  const cities: City[] = [];
  for (const album of journey.albums) if (!cities.includes(album.city)) cities.push(album.city);
  return [
    { n: 0, label: 'Start', place: endpointLabel(journey.start, archive, home), albums: [] },
    ...cities.map((city, i) => ({
      n: i + 1,
      label: city.name,
      place: city.country.name,
      albums: journey.albums.filter((album) => album.city === city),
    })),
    {
      n: cities.length + 1,
      label: 'End',
      place: endpointLabel(journey.end, archive, home),
      albums: [],
    },
  ];
};

/** Albums grouped by year, the latest year first, each year in date order. */
export const albumsByYear = (albums: Album[]): { year: number; albums: Album[] }[] => {
  const years = [...new Set(albums.map((album) => album.year))].sort((a, b) => b - a);
  return years.map((year) => ({
    year,
    albums: albums.filter((album) => album.year === year).sort(byDate),
  }));
};

/** The three photos a folder holds. */
export const folderPhotos = (album: Album): PhotoRef[] => album.photos.slice(0, 3);

/** The first photo among these albums, for a card's cover. */
export const coverOf = (albums: Album[]): PhotoRef | undefined =>
  albums.find((album) => album.photos.length > 0)?.photos[0];

export type PageData =
  | { kind: 'trips'; journeys: Journey[] }
  | { kind: 'trip'; journey: Journey; route: RouteStop[] }
  | { kind: 'albums'; albums: Album[] }
  | { kind: 'album'; album: Album; journey: Journey | undefined }
  | { kind: 'countries'; countries: Country[] }
  | { kind: 'country'; country: Country; cities: City[] }
  | { kind: 'cities'; cities: City[] }
  | { kind: 'city'; city: City }
  | { kind: 'years'; years: number[] }
  | { kind: 'year'; year: number; albums: Album[] };

const byName = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name);

/** What a page shows, or null when what it points at is gone. */
export const findPage = (archive: Archive, page: ArchivePage, home: Place): PageData | null => {
  switch (page.kind) {
    case 'trips':
      return { kind: 'trips', journeys: journeys(archive) };
    case 'trip': {
      const journey = journeys(archive).find((j) => j.id === page.id);
      return journey ? { kind: 'trip', journey, route: tripRoute(journey, archive, home) } : null;
    }
    case 'albums':
      return { kind: 'albums', albums: archive.albums };
    case 'album': {
      const album = archive.albumById.get(page.id);
      return album ? { kind: 'album', album, journey: journeyOfAlbum(archive, album.id) } : null;
    }
    case 'countries':
      return {
        kind: 'countries',
        countries: archive.countries.filter((c) => c.cities.some((city) => city.albums.length > 0)).sort(byName),
      };
    case 'country': {
      const country = archive.countries.find((c) => c.id === page.id);
      const cities = country?.cities.filter((city) => city.albums.length > 0) ?? [];
      return country && cities.length > 0 ? { kind: 'country', country, cities } : null;
    }
    case 'cities':
      return { kind: 'cities', cities: [...archive.cities].sort(byName) };
    case 'city': {
      const city = archive.cityByKey.get(page.key);
      return city && city.albums.length > 0 ? { kind: 'city', city } : null;
    }
    case 'years':
      return {
        kind: 'years',
        years: [...new Set(archive.albums.map((album) => album.year))].sort((a, b) => b - a),
      };
    case 'year': {
      const albums = archive.albums.filter((album) => album.year === page.year);
      return albums.length > 0 ? { kind: 'year', year: page.year, albums } : null;
    }
  }
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/archive/pages.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/archive
git commit -m "feat(archive): add the pages model: trips, routes, years, folders"
```

---

### Task 3: Tours that end by themselves

**Files:**
- Modify: `src/tour/director.ts`, `src/tour/director.test.ts`
- Create: `src/archive/return.ts`
- Test: `src/archive/return.test.ts`

**Interfaces:**
- Produces: the director increments `tourDone` when a year tour stops at its last album and when a trip lands at its end; `type TourOutcome = 'finished' | 'interrupted' | null`, `tourOutcome(prev: AppState, next: AppState): TourOutcome`, `RETURN_DELAY_MS = 5000`, `SLOW_FADE_MS = 1400`.

- [ ] **Step 1: Write the failing tests**

Append inside `describe('tours', ...)` in `src/tour/director.test.ts`:

```ts
  it('counts a year that ends by itself, and a trip that lands at its end', () => {
    const year = setup();
    year.director.showYear(2023);
    year.run(60000);
    expect(year.state().tourDone).toBe(1);
    const trip = setup();
    trip.director.showTrip(tripId('Japan in bloom'));
    trip.run(40000);
    expect(trip.state().tourDone).toBe(1);
  });

  it('does not count a tour the owner interrupted', () => {
    const { director, run, state } = setup();
    director.showYear(2023);
    run(3000);
    director.escape();
    run(60000);
    expect(state().tourDone).toBe(0);
  });
```

`src/archive/return.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { INITIAL_STATE } from '@/state/app-state';
import type { AppState } from '@/state/app-state';
import type { Tour } from '@/tour/tour';
import { tourOutcome } from './return';

const tour: Tour = {
  kind: 'year',
  list: [1, 2],
  start: null,
  end: null,
  name: '2023',
  tripId: null,
  year: 2023,
};
const playing: AppState = { ...INITIAL_STATE, tour, playing: true };

describe('tourOutcome', () => {
  it('sees a tour that ended by itself', () => {
    expect(tourOutcome(playing, { ...playing, playing: false, tourDone: 1 })).toBe('finished');
  });

  it('sees the owner stop or leave it', () => {
    expect(tourOutcome(playing, { ...playing, playing: false })).toBe('interrupted');
    expect(tourOutcome(playing, { ...playing, tour: null })).toBe('interrupted');
  });

  it('ignores everything else', () => {
    expect(tourOutcome(playing, { ...playing, focus: 3 })).toBeNull();
    expect(tourOutcome(INITIAL_STATE, { ...INITIAL_STATE, range: { lo: 1, hi: 2 } })).toBeNull();
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/tour/director.test.ts src/archive/return.test.ts`
Expected: FAIL — `tourDone` stays 0; `./return` not found.

- [ ] **Step 3: Implement**

In `src/tour/director.ts`:

1. In `playNext`, replace `else stop();` with:

```ts
    else if (tour) {
      // a year ends at its last album: the tour ended by itself
      dwell = 0;
      set({ playing: false, tourDone: get().tourDone + 1 });
    } else stop();
```

2. In `arrive`, inside `if (done.end) { ... }`, add `patch.tourDone = get().tourDone + 1;` next to `patch.playing = false;`.

`src/archive/return.ts`:

```ts
import type { AppState } from '@/state/app-state';

/** A year or trip tour that ended by itself brings its archive page back after this long. */
export const RETURN_DELAY_MS = 5000;
/** How slowly the archive fades back in. */
export const SLOW_FADE_MS = 1400;

export type TourOutcome = 'finished' | 'interrupted' | null;

/** Between two states: did a tour end by itself, did the owner stop or leave it, or neither. */
export const tourOutcome = (prev: AppState, next: AppState): TourOutcome => {
  if (next.tourDone !== prev.tourDone) return 'finished';
  if ((prev.tour && !next.tour) || (prev.playing && !next.playing)) return 'interrupted';
  return null;
};
```

- [ ] **Step 4: Run the tests and the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tour src/archive/return.ts src/archive/return.test.ts
git commit -m "feat(tour): tell a tour that ended by itself from one the owner interrupted"
```

---

### Task 4: The archive layer

**Files:**
- Create: `src/features/archive/links.ts`, `src/features/archive/useArchiveReturn.ts`, `src/features/archive/Archive.tsx`, `src/features/archive/archive.scss`
- Modify: `src/app/Stage.tsx`, `src/features/keys/useKeys.ts`

**Interfaces:**
- Consumes: Tasks 1–3, `Director`, `photoUrl`, `photoKey`, `photoNote`, `socialFor`, `socialStore`, `openPhoto`, `cozyRoom` svg.
- Produces:
  - `goArchive(page: ArchivePage): void` — the one way into the archive from the main screen (closes the photo window first; plan 5 adds the log-in gate here)
  - `showOnMap(director: Director, target: { kind: 'album'; id: string } | { kind: 'year'; year: number } | { kind: 'trip'; id: string }): void` — closes the archive, remembers the page for the return, runs the director
  - `useArchiveReturn(): void`
  - `Archive({ world, director })`

- [ ] **Step 1: Write the links and the return hook**

`src/features/archive/links.ts`:

```ts
import type { ArchivePage } from '@/state/app-state';
import { appStore } from '@/state/app-state';
import { closeArchive, openArchive } from '@/state/archive-nav';
import { finishPhoto } from '@/state/layers';
import type { Director } from '@/tour/director';

/** The pages a tour was started from, to come back to when it ends by itself. */
let returnTo: ArchivePage[] | null = null;

export const takeReturn = (): ArchivePage[] | null => {
  const pages = returnTo;
  returnTo = null;
  return pages;
};

export const forgetReturn = () => {
  returnTo = null;
};

/** The one way into the archive from the main screen and the photo window. */
export const goArchive = (page: ArchivePage) => {
  if (appStore.get().photo) finishPhoto(appStore);
  openArchive(appStore, page, true);
};

export type MapTarget =
  | { kind: 'album'; id: string }
  | { kind: 'year'; year: number }
  | { kind: 'trip'; id: string };

/** "Show on map": the archive closes and the globe shows the album, the year or the trip. */
export const showOnMap = (director: Director, target: MapTarget) => {
  const pages = appStore.get().archive?.stack ?? null;
  closeArchive(appStore);
  const shown =
    target.kind === 'album'
      ? director.showAlbumOnMap(target.id)
      : target.kind === 'year'
        ? director.showYear(target.year)
        : director.showTrip(target.id);
  // only a year or a trip plays a tour that can end by itself
  returnTo = shown && target.kind !== 'album' ? pages : null;
};
```

`src/features/archive/useArchiveReturn.ts`:

```ts
import { useEffect } from 'react';
import { RETURN_DELAY_MS, SLOW_FADE_MS, tourOutcome } from '@/archive/return';
import { appStore } from '@/state/app-state';
import { openArchive } from '@/state/archive-nav';
import { forgetReturn, takeReturn } from './links';

/**
 * 5 s after a year or trip tour ends by itself, the archive page it was started from fades back
 * in; not if the owner interrupted the tour, or while the photo window is open.
 */
export const useArchiveReturn = (): void => {
  useEffect(() => {
    let prev = appStore.get();
    let timer = 0;
    let fade = 0;
    const unsubscribe = appStore.subscribe(() => {
      const next = appStore.get();
      const outcome = tourOutcome(prev, next);
      prev = next;
      if (outcome === 'interrupted') {
        forgetReturn();
        clearTimeout(timer);
      }
      if (outcome !== 'finished') return;
      const pages = takeReturn();
      if (!pages || pages.length === 0) return;
      clearTimeout(timer);
      timer = window.setTimeout(() => {
        const state = appStore.get();
        if (state.photo || state.archive) return;
        const [first, ...rest] = pages;
        if (!first) return;
        openArchive(appStore, first, true, true);
        for (const page of rest) openArchive(appStore, page, false, true);
        fade = window.setTimeout(() => {
          const archive = appStore.get().archive;
          if (archive?.slow) appStore.set({ archive: { ...archive, slow: false } });
        }, SLOW_FADE_MS);
      }, RETURN_DELAY_MS);
    });
    return () => {
      unsubscribe();
      clearTimeout(timer);
      clearTimeout(fade);
    };
  }, []);
};
```

- [ ] **Step 2: Write the archive**

`src/features/archive/Archive.tsx`:

```tsx
import { Fragment, useEffect, useState } from 'react';
import type { World } from '@/app/boot';
import { albumsByYear, coverOf, dateSpan, findPage, folderPhotos, plural, whenLabel } from '@/archive/pages';
import type { Journey, PageData } from '@/archive/pages';
import { visitYears } from '@/data/archive';
import { cityPhotos, photoUrl } from '@/data/photos';
import { describeAlbum, photoKey, photoNote } from '@/data/social';
import type { Album, City, Country, PhotoRef } from '@/data/types';
import { MONTHS } from '@/lib/dates';
import { appStore } from '@/state/app-state';
import type { ArchivePage } from '@/state/app-state';
import { backArchive, closeArchive, openArchive, SECTIONS, sectionOf } from '@/state/archive-nav';
import { openPhoto } from '@/state/layers';
import { socialFor, socialStore } from '@/state/social';
import { useStore } from '@/state/store';
import type { Director } from '@/tour/director';
import { showOnMap } from './links';
import './archive.scss';

const go = (page: ArchivePage) => openArchive(appStore, page, false);

/** The archive: a full-screen layer over the paused globe. */
export function Archive({ world, director }: { world: World; director: Director }) {
  const view = useStore(appStore, (s) => s.archive);
  const [shown, setShown] = useState(false);
  const page = view?.stack[view.stack.length - 1];
  const data = page ? findPage(world.archive, page, world.home) : null;

  // fade in after mounting; fade out by dropping the class before the layer goes
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(view !== null));
    return () => cancelAnimationFrame(id);
  }, [view]);

  // a page whose target is gone steps back
  useEffect(() => {
    if (page && !data) backArchive(appStore);
  }, [page, data]);

  if (!view || !page || !data) return null;

  const header = headerOf(data);
  return (
    <section
      className={`archive${shown ? ' is-on' : ''}${view.slow ? ' is-slow' : ''}`}
      aria-label="Archive"
    >
      <div className="archive__head">
        <div className="archive__bar">
          <button type="button" className="archive__round" aria-label="Close" onClick={() => closeArchive(appStore)}>
            ✕
          </button>
          {view.stack.length > 1 && (
            <button type="button" className="archive__round" aria-label="Back" onClick={() => backArchive(appStore)}>
              ←
            </button>
          )}
          <nav className="archive__tabs">
            {SECTIONS.map((section) => (
              <button
                key={section.key}
                type="button"
                className={sectionOf(view.stack[0] ?? page) === section.key ? 'is-on' : undefined}
                onClick={() => openArchive(appStore, { kind: section.key }, true)}
              >
                {section.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="archive__text" key={JSON.stringify(page)}>
          {header.crumbs.length > 0 && (
            <div className="archive__crumbs">
              {header.crumbs.map(([label, to], i) => (
                <span key={label}>
                  {i > 0 && <i>›</i>}
                  <button type="button" onClick={() => go(to)}>
                    {label}
                  </button>
                </span>
              ))}
            </div>
          )}
          <h2>{header.title}</h2>
          {header.sub && <p className="archive__sub">{header.sub}</p>}
          {header.map && (
            <div className="archive__acts">
              <button type="button" className="archive__btn is-star" onClick={() => header.map && showOnMap(director, header.map)}>
                ◎ Show on map
              </button>
            </div>
          )}
        </div>
      </div>
      <div className={`archive__grid${data.kind === 'album' ? ' archive__grid--photos' : ''}`} key={`grid-${JSON.stringify(page)}`}>
        <PageBody data={data} world={world} />
      </div>
    </section>
  );
}

interface Header {
  crumbs: [string, ArchivePage][];
  title: string;
  sub: string;
  map: Parameters<typeof showOnMap>[1] | null;
}

const headerOf = (data: PageData): Header => {
  const photos = (albums: Album[]) => albums.reduce((sum, a) => sum + a.photoCount, 0);
  switch (data.kind) {
    case 'trips':
      return { crumbs: [], title: 'Trips', sub: plural(data.journeys.length, 'trip'), map: null };
    case 'trip': {
      const { journey } = data;
      const places = new Set(journey.albums.map((a) => a.city)).size;
      const start = data.route[0]?.place.replace(/^home · .*/, 'home') ?? 'home';
      const end = data.route[data.route.length - 1]?.place.replace(/^home · .*/, 'home') ?? 'home';
      return {
        crumbs: [['Trips', { kind: 'trips' }]],
        title: journey.name,
        sub: `${dateSpan(journey.albums)} · ${plural(places, 'place')} · ${plural(photos(journey.albums), 'photo')} · from ${start} to ${end}`,
        map: journey.albums.length > 0 && journey.real ? { kind: 'trip', id: journey.id } : null,
      };
    }
    case 'albums':
      return {
        crumbs: [],
        title: 'Albums',
        sub: `${plural(data.albums.length, 'album')} · ${plural(photos(data.albums), 'photo')}`,
        map: null,
      };
    case 'album': {
      const { album, journey } = data;
      const crumbs: [string, ArchivePage][] = [
        [album.city.country.name, { kind: 'country', id: album.city.country.id }],
        [album.city.name, { kind: 'city', key: album.city.key }],
      ];
      if (journey?.real) crumbs.push([`Trip: ${journey.name}`, { kind: 'trip', id: journey.id }]);
      return {
        crumbs,
        title: album.title,
        sub: `${whenLabel(album)} · ${describeAlbum(album)}`,
        map: { kind: 'album', id: album.id },
      };
    }
    case 'countries':
      return { crumbs: [], title: 'Countries', sub: plural(data.countries.length, 'country'), map: null };
    case 'country': {
      const albums = data.cities.reduce((n, c) => n + c.albums.length, 0);
      return {
        crumbs: [['Countries', { kind: 'countries' }]],
        title: data.country.name,
        sub: `${plural(data.cities.length, 'city')} · ${plural(albums, 'album')}`,
        map: null,
      };
    }
    case 'cities':
      return { crumbs: [], title: 'Cities', sub: plural(data.cities.length, 'place'), map: null };
    case 'city':
      return {
        crumbs: [
          ['Cities', { kind: 'cities' }],
          [data.city.country.name, { kind: 'country', id: data.city.country.id }],
        ],
        title: data.city.name,
        sub: `${plural(data.city.albums.length, 'album')} · ${plural(photos(data.city.albums), 'photo')}`,
        map: null,
      };
    case 'years':
      return { crumbs: [], title: 'Years', sub: plural(data.years.length, 'year'), map: null };
    case 'year':
      return {
        crumbs: [['Years', { kind: 'years' }]],
        title: `${data.year} · ${plural(data.albums.length, 'album')}`,
        sub: '',
        map: { kind: 'year', year: data.year },
      };
  }
};

function PageBody({ data, world }: { data: PageData; world: World }) {
  switch (data.kind) {
    case 'trips':
      return <>{data.journeys.map((journey) => <TripCard key={journey.id} journey={journey} />)}</>;
    case 'trip':
      return (
        <>
          {data.route.map((stop) => (
            <Fragment key={`stop-${stop.n}`}>
              <div className="archive__stop">
                <i>{String(stop.n).padStart(2, '0')}</i>
                <b>{stop.label}</b>
                <span>{stop.place}</span>
              </div>
              {stop.albums.map((album) => (
                <Folder key={album.id} album={album} showCity={false} />
              ))}
            </Fragment>
          ))}
        </>
      );
    case 'albums':
      return <YearGroups albums={data.albums} showCity />;
    case 'album':
      return <PhotoGrid album={data.album} />;
    case 'countries':
      return <>{data.countries.map((country) => <CountryCard key={country.id} country={country} />)}</>;
    case 'country':
      return <>{data.cities.map((city) => <CityCard key={city.key} city={city} />)}</>;
    case 'cities':
      return <>{data.cities.map((city) => <CityCard key={city.key} city={city} />)}</>;
    case 'city':
      return <YearGroups albums={data.city.albums} showCity={false} />;
    case 'years':
      return <>{data.years.map((year) => <YearCard key={year} year={year} world={world} />)}</>;
    case 'year':
      return (
        <>
          {[...data.albums].map((album) => (
            <Folder key={album.id} album={album} showCity />
          ))}
        </>
      );
  }
}

function YearGroups({ albums, showCity }: { albums: Album[]; showCity: boolean }) {
  return (
    <>
      {albumsByYear(albums).map((group) => (
        <Fragment key={group.year}>
          <div className="archive__year">{group.year}</div>
          {group.albums.map((album) => (
            <Folder key={album.id} album={album} showCity={showCity} />
          ))}
        </Fragment>
      ))}
    </>
  );
}

function Cover({ photo }: { photo: PhotoRef | undefined }) {
  const url = photo ? photoUrl(photo) : null;
  return url ? <img src={url} alt="" loading="lazy" /> : null;
}

function TripCard({ journey }: { journey: Journey }) {
  const places = [...new Set(journey.albums.map((a) => a.city.name))];
  return (
    <button type="button" className="archive__card" onClick={() => go({ kind: 'trip', id: journey.id })}>
      <Cover photo={coverOf(journey.albums)} />
      <div>
        <b>{journey.name}</b>
        <span>
          {dateSpan(journey.albums)}
          {places.length > 0 ? ` · ${places.join(', ')}` : ''}
        </span>
      </div>
    </button>
  );
}

function CountryCard({ country }: { country: Country }) {
  const cities = country.cities.filter((c) => c.albums.length > 0);
  const albums = cities.reduce((n, c) => n + c.albums.length, 0);
  return (
    <button type="button" className="archive__card" onClick={() => go({ kind: 'country', id: country.id })}>
      <Cover photo={coverOf(cities.flatMap((c) => c.albums))} />
      <div>
        <b>{country.name}</b>
        <span>
          {plural(cities.length, 'city')} · {plural(albums, 'album')}
        </span>
      </div>
    </button>
  );
}

function CityCard({ city }: { city: City }) {
  const years = visitYears(city);
  const first = years[0];
  const last = years[years.length - 1];
  return (
    <button type="button" className="archive__card" onClick={() => go({ kind: 'city', key: city.key })}>
      <Cover photo={cityPhotos(city)[0]} />
      <div>
        <b>{city.name}</b>
        <span>
          {plural(city.albums.length, 'album')} · {first}
          {last !== undefined && last !== first ? `–${last}` : ''}
        </span>
      </div>
    </button>
  );
}

function YearCard({ year, world }: { year: number; world: World }) {
  const albums = world.archive.albums.filter((a) => a.year === year);
  const places = new Set(albums.map((a) => a.city)).size;
  return (
    <button type="button" className="archive__card archive__card--year" onClick={() => go({ kind: 'year', year })}>
      <Cover photo={coverOf(albums)} />
      <div>
        <b>{year}</b>
        <span>
          {plural(albums.length, 'album')} · {plural(places, 'place')}
        </span>
      </div>
    </button>
  );
}

/** A stack of three photos in a folder that fans out on hover. */
function Folder({ album, showCity }: { album: Album; showCity: boolean }) {
  const photos = [...folderPhotos(album)].reverse();
  return (
    <button type="button" className="folder" onClick={() => go({ kind: 'album', id: album.id })}>
      <div className="folder__stack">
        {photos.map((photo, i) => (
          <img key={i} src={photoUrl(photo) ?? undefined} alt="" loading="lazy" />
        ))}
        <div className="folder__front">
          <b>{album.title}</b>
          <span>
            {showCity ? `${album.city.name} · ` : ''}
            {album.day} {MONTHS[album.month - 1]} {album.year} · {plural(album.photoCount, 'photo')}
          </span>
        </div>
      </div>
    </button>
  );
}

function PhotoGrid({ album }: { album: Album }) {
  useStore(socialStore, (s) => s.byKey);
  if (album.photos.length === 0) return <p className="archive__sub">No photos yet.</p>;
  return (
    <>
      {album.photos.map((photo, index) => {
        const key = photoKey(photo);
        const social = socialFor(key);
        return (
          <button
            type="button"
            key={key}
            className="archive__pic"
            onClick={(event) => {
              const frame = event.currentTarget.querySelector('.archive__photo');
              if (!frame) return;
              const { x, y, width, height } = frame.getBoundingClientRect();
              openPhoto(appStore, album.id, index, { x, y, width, height });
            }}
          >
            <div className="archive__photo">
              <img src={photoUrl(photo) ?? undefined} alt="" loading="lazy" data-photo-key={key} />
              <div className="archive__meta">
                <span>
                  {social.liked ? '♥' : '♡'} {social.likes}
                </span>
                <span>{plural(social.comments.length, 'comment')}</span>
              </div>
            </div>
            <p className="archive__cap">{photoNote(photo)}</p>
          </button>
        );
      })}
    </>
  );
}
```

`src/features/archive/archive.scss` (ported from the prototype, lines 168–248, with the mobile rules):

```scss
.archive {
  position: fixed;
  inset: 0;
  z-index: 25;
  overflow-y: auto;
  background: rgb(4 6 13 / 95%);
  backdrop-filter: blur(8px);
  opacity: 0;
  transition: opacity 0.5s ease;
  touch-action: pan-y;

  &.is-on {
    opacity: 1;
  }

  &.is-slow {
    transition-duration: 1.4s;
  }

  &__head {
    position: sticky;
    top: 0;
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: max(22px, var(--safe-top)) 32px 18px;
    background: rgb(4 6 13 / 98.5%);
    box-shadow: 0 18px 22px -6px rgb(4 6 13 / 95%);
  }

  &__bar {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  &__round {
    flex: none;
    width: 44px;
    height: 44px;
    border: 1px solid rgb(127 137 163 / 35%);
    border-radius: 50%;
    background: rgb(12 16 30 / 70%);
    font-size: 16px;

    &:hover {
      border-color: rgb(255 200 107 / 60%);
    }
  }

  &__tabs {
    display: flex;
    gap: 4px;
    min-width: 0;
    padding: 4px;
    overflow-x: auto;
    border-radius: 99px;
    background: rgb(12 16 30 / 80%);
    box-shadow: 0 0 0 1px rgb(127 137 163 / 20%);
    scrollbar-width: none;

    button {
      padding: 8px 14px;
      border: 0;
      border-radius: 99px;
      background: none;
      font-size: 13px;
      color: var(--muted);
      transition:
        background 0.3s,
        color 0.3s;

      &:hover {
        color: var(--text);
      }

      &.is-on {
        background: rgb(255 200 107 / 15%);
        color: var(--lamp);
      }
    }
  }

  &__text {
    min-width: 0;
    animation: archive-in 0.35s ease both;

    h2 {
      margin: 6px 0 0;
      font-family: var(--font-family-display);
      font-style: italic;
      font-weight: 300;
      font-size: clamp(30px, 4vw, 52px);
      line-height: 1;
    }
  }

  &__crumbs {
    font-size: 12px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--lamp);

    i {
      margin: 0 8px;
      font-style: normal;
      color: var(--muted);
    }

    button {
      padding: 0;
      border: 0;
      border-bottom: 1px solid transparent;
      background: none;
      letter-spacing: inherit;
      text-transform: inherit;
      color: var(--lamp);

      &:hover {
        border-color: rgb(255 200 107 / 50%);
      }
    }
  }

  &__sub {
    max-width: 640px;
    margin: 8px 0 0;
    font-size: 13px;
    line-height: 1.5;
    color: var(--muted);
  }

  &__acts {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 14px;
  }

  &__btn {
    padding: 9px 16px;
    border: 1px solid rgb(127 137 163 / 35%);
    border-radius: 99px;
    background: rgb(12 16 30 / 70%);
    font-size: 13px;

    &.is-star {
      border-color: rgb(143 184 255 / 50%);
      color: var(--star);
    }

    &:hover {
      border-color: rgb(255 200 107 / 60%);
    }
  }

  &__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    gap: 44px 34px;
    padding: 26px 32px 60px;
    animation: archive-in 0.45s var(--ease) both;

    &--photos {
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 28px 18px;
    }
  }

  &__year,
  &__stop {
    grid-column: 1 / -1;
    margin: 10px 0 -14px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgb(255 200 107 / 20%);

    &:first-child {
      margin-top: 0;
    }
  }

  &__year {
    font-family: var(--font-family-display);
    font-style: italic;
    font-weight: 300;
    font-size: 34px;
    color: var(--lamp);
  }

  &__stop {
    display: flex;
    gap: 14px;
    align-items: baseline;

    i {
      font-style: normal;
      font-size: 12px;
      letter-spacing: 0.2em;
      color: var(--muted);
    }

    b {
      font-family: var(--font-family-display);
      font-style: italic;
      font-weight: 300;
      font-size: 32px;
      color: var(--lamp);
    }

    span {
      font-size: 12px;
      color: var(--muted);
    }
  }

  &__card {
    position: relative;
    padding: 0;
    overflow: hidden;
    border: 0;
    border-radius: 14px;
    background: #0b1020;
    box-shadow: 0 18px 40px rgb(0 0 0 / 50%);
    aspect-ratio: 4 / 3;
    text-align: left;
    transition: transform 0.5s var(--ease);

    &:hover {
      transform: translateY(-5px);
    }

    img {
      display: block;
      width: 100%;
      height: 100%;
      max-width: none;
      object-fit: cover;
      transition: transform 1.4s var(--ease);
    }

    &:hover img {
      transform: scale(1.06);
    }

    &::after {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(transparent 35%, rgb(4 6 13 / 88%));
    }

    div {
      position: absolute;
      right: 16px;
      bottom: 14px;
      left: 16px;
      z-index: 1;
    }

    b {
      display: block;
      font-family: var(--font-family-display);
      font-style: italic;
      font-weight: 500;
      font-size: 24px;
      line-height: 1.1;
    }

    span {
      display: block;
      margin-top: 5px;
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--lamp);
    }

    &--year b {
      font-weight: 300;
      font-size: 54px;
      line-height: 1;
    }
  }

  &__pic {
    padding: 0;
    border: 0;
    background: none;
    text-align: left;
  }

  &__photo {
    position: relative;
    overflow: hidden;
    border-radius: 10px;
    background: #0b1020;
    box-shadow: 0 14px 30px rgb(0 0 0 / 45%);
    aspect-ratio: 3 / 2;
    transition: transform 0.5s var(--ease);

    img {
      display: block;
      width: 100%;
      height: 100%;
      max-width: none;
      object-fit: cover;
      transition: transform 1.2s var(--ease);
    }
  }

  &__pic:hover &__photo {
    transform: translateY(-4px);

    img {
      transform: scale(1.05);
    }
  }

  &__meta {
    position: absolute;
    right: 10px;
    bottom: 9px;
    display: flex;
    gap: 10px;
    font-size: 12px;
    color: #fff;
    text-shadow: 0 1px 6px rgb(0 0 0 / 90%);

    span {
      padding: 3px 9px;
      border-radius: 99px;
      background: rgb(4 6 13 / 55%);
      backdrop-filter: blur(4px);
    }
  }

  &__cap {
    margin: 10px 0 0;
    font-size: 13px;
    line-height: 1.5;
    color: #c3c9d8;
  }

  @include mobile {
    &__head {
      padding-inline: 16px;
    }

    &__tabs button {
      padding: 7px 11px;
    }

    &__grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 34px 18px;
      padding: 20px 16px 40px;

      &--photos {
        grid-template-columns: 1fr;
      }
    }

    &__card {
      b {
        font-size: 17px;
      }

      span {
        font-size: 10px;
        letter-spacing: 0.08em;
      }

      div {
        right: 12px;
        bottom: 10px;
        left: 12px;
      }

      &--year b {
        font-size: 38px;
      }
    }
  }
}

// a folder: three photos in it, fanning out on hover
.folder {
  position: relative;
  padding: 14px 0 0;
  border: 0;
  background: none;
  text-align: left;

  &__stack {
    position: relative;
    aspect-ratio: 4 / 3;
    isolation: isolate;

    &::before {
      content: '';
      position: absolute;
      top: -12px;
      left: 0;
      z-index: -1;
      width: 42%;
      height: 24px;
      border-radius: 10px 10px 0 0;
      background: #1b2744;
    }

    &::after {
      content: '';
      position: absolute;
      inset: 0;
      z-index: -1;
      border-radius: 4px 12px 12px;
      background: linear-gradient(#1b2744, #121a31);
      box-shadow: 0 18px 40px rgb(0 0 0 / 50%);
    }

    img {
      position: absolute;
      top: 8%;
      left: 8%;
      width: 84%;
      height: 78%;
      max-width: none;
      object-fit: cover;
      border-radius: 6px;
      box-shadow: 0 6px 16px rgb(0 0 0 / 45%);
      transition: transform 0.6s var(--ease);

      &:nth-of-type(1) {
        transform: rotate(-5deg) translateY(-6%);
      }

      &:nth-of-type(2) {
        transform: rotate(4deg) translateY(-9%);
      }

      &:nth-of-type(3) {
        transform: rotate(-1deg) translateY(-12%);
      }
    }
  }

  &:hover &__stack img {
    &:nth-of-type(1) {
      transform: rotate(-12deg) translate(-12%, -22%);
    }

    &:nth-of-type(2) {
      transform: rotate(9deg) translate(12%, -24%);
    }

    &:nth-of-type(3) {
      transform: rotate(-2deg) translateY(-30%);
    }
  }

  &__front {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 1;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    height: 58%;
    padding: 14px 16px;
    border-radius: 12px;
    background: linear-gradient(rgb(34 48 84 / 97%), rgb(22 31 57 / 99%));
    box-shadow:
      0 -6px 16px rgb(0 0 0 / 35%),
      inset 0 1px 0 rgb(255 255 255 / 8%);
    transform-origin: bottom;
    transition: transform 0.6s var(--ease);

    b {
      font-family: var(--font-family-display);
      font-style: italic;
      font-weight: 500;
      font-size: 20px;
      line-height: 1.1;
    }

    span {
      margin-top: 5px;
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--lamp);
    }
  }

  &:hover &__front {
    transform: perspective(600px) rotateX(-14deg);
  }

  @include mobile {
    &__front b {
      font-size: 16px;
    }
  }
}

@keyframes archive-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}
```

- [ ] **Step 3: Put it on the stage and give Esc its step**

`src/app/Stage.tsx`: import `Archive` from `@/features/archive/Archive` and `useArchiveReturn` from `@/features/archive/useArchiveReturn`; call `useArchiveReturn();` after `useKeys(...)`; render `<Archive world={world} director={director} />` right before `<Lightbox ... />` (the photo window opens over the archive).

`src/features/keys/useKeys.ts`: import `backArchive` from `@/state/archive-nav`; in the Esc branch add `else if (layer === 'archive') backArchive(appStore);` before the `else director.escape();`; and after the `if (state.photo) {...}` block add:

```ts
      // the archive is a page: arrows and Space belong to it, not to the globe under it
      if (state.archive) return;
```

- [ ] **Step 4: Run the check and commit**

Run: `npm run check`
Expected: PASS.

```bash
git add src/features/archive src/app/Stage.tsx src/features/keys/useKeys.ts
git commit -m "feat(archive): add the archive with trips, albums, countries, cities, years and their pages"
```

---

### Task 5: Links into the archive

**Files:**
- Modify: `src/features/panel/AlbumPanel.tsx`, `src/features/panel/panel.scss`, `src/features/lightbox/Lightbox.tsx`, `src/features/lightbox/lightbox.scss`, `src/features/timeline/Timeline.tsx`

**Interfaces:**
- Consumes: `goArchive` (Task 4), `journeyOfAlbum` (Task 2).

- [ ] **Step 1: Link the panel**

In `src/features/panel/AlbumPanel.tsx` (import `goArchive` from `@/features/archive/links` and `journeyOfAlbum` from `@/archive/pages`):

1. `PanelHead`, the scope: render a button that opens the year or the trip:

```tsx
        <button
          type="button"
          className="is-current"
          onClick={() =>
            goArchive(
              scope.kind === 'year' && scope.year !== null
                ? { kind: 'year', year: scope.year }
                : scope.tripId
                  ? { kind: 'trip', id: scope.tripId }
                  : { kind: 'trips' },
            )
          }
        >
          {scope.kind === 'year' ? scope.name : `Trip · ${scope.name}`}
        </button>
```

in place of the `<span className="is-current">…</span>`.

2. `PanelHead`, the years: a second click on the current year opens the city:

```tsx
          onClick={() => {
            const album = archive.albums[focus];
            if (year === current && album) {
              goArchive({ kind: 'city', key: album.city.key });
              return;
            }
            const index = list.find((i) => archive.albums[i]?.year === year);
            if (index !== undefined) director.selectAlbum(index);
          }}
```

3. `AlbumCard`: with a mouse, the title on the cover opens the album (it only shows on hover). Add `onPointerDown` tracking is not needed: give the title an `onClick`:

```tsx
      <div
        className="card__title"
        onClick={(event) => {
          if (role !== 'cur') return;
          event.stopPropagation();
          goArchive({ kind: 'album', id: album.id });
        }}
      >
```

and in `panel.scss`, inside `.stack:hover`, add:

```scss
  @media (hover: hover) {
    .card--cur .card__title {
      pointer-events: auto;
      cursor: pointer;

      &:hover {
        color: var(--lamp);
      }
    }
  }
```

4. `Caption` (album): the city opens the city, the country the country, the album the album, the trip the trip:

```tsx
      <button type="button" className="caption__place" onClick={() => goArchive({ kind: 'city', key: album.city.key })}>
        {album.city.name}
      </button>
      <div className="caption__route">
        <button type="button" className="link link--strong" onClick={() => goArchive({ kind: 'country', id: album.city.country.id })}>
          {album.city.country.name}
        </button>{' '}
        ·{' '}
        <button type="button" className="link" onClick={() => goArchive({ kind: 'album', id: album.id })}>
          {album.title}
        </button>{' '}
        · {album.photoCount} photos
      </div>
      <div className="caption__trip">
        {trip && (
          <>
            Trip ·{' '}
            <button type="button" className="link" onClick={() => goArchive({ kind: 'trip', id: trip.id })}>
              {trip.name}
            </button>
          </>
        )}
      </div>
```

5. `Caption` (end card): "from City · Album" and "Trip · name" as links:

```tsx
        <div className="caption__route">
          {city ? city.country.name : home.country} · from{' '}
          <button type="button" className="link" onClick={() => goArchive({ kind: 'city', key: from.city.key })}>
            {from.city.name}
          </button>{' '}
          ·{' '}
          <button type="button" className="link" onClick={() => goArchive({ kind: 'album', id: from.id })}>
            {from.title}
          </button>
        </div>
        <div className="caption__trip">
          {endCard.tour?.kind === 'trip' && endCard.tour.tripId && (
            <>
              Trip ·{' '}
              <button
                type="button"
                className="link"
                onClick={() => endCard.tour?.tripId && goArchive({ kind: 'trip', id: endCard.tour.tripId })}
              >
                {endCard.tour.name}
              </button>
            </>
          )}
        </div>
```

(remove the now unused `trip` constant of the end card). `journeyOfAlbum` is not needed if `tripOfAlbum` already gives the trip; keep `tripOfAlbum`.

6. `panel.scss`: the caption's links look like text until hovered:

```scss
.caption {
  .link {
    padding: 0;
    border: 0;
    border-bottom: 1px solid transparent;
    background: none;
    color: inherit;
    transition:
      color 0.3s,
      border-color 0.3s;

    &:hover {
      border-color: rgb(255 200 107 / 50%);
      color: var(--lamp);
    }

    &--strong {
      font-weight: 500;
      color: var(--text);
    }
  }

  &__place {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    pointer-events: auto;
    transition: color 0.3s;

    &:hover {
      color: var(--lamp);
    }
  }

  &__route,
  &__trip {
    pointer-events: auto;
  }
}
```

(add these next to the existing `.caption` rules; `.caption__place` keeps its type styles).

- [ ] **Step 2: Link the photo window**

In `src/features/lightbox/Lightbox.tsx` (import `goArchive`), the country, city and album become buttons:

```tsx
          <button type="button" className="lightbox__country lightbox__link" onClick={() => goArchive({ kind: 'country', id: album.city.country.id })}>
            {album.city.country.name}
          </button>
          <button type="button" className="lightbox__city lightbox__link" onClick={() => goArchive({ kind: 'city', key: album.city.key })}>
            {album.city.name}
          </button>
          <button type="button" className="lightbox__album lightbox__link" onClick={() => goArchive({ kind: 'album', id: album.id })}>
            {album.title}
          </button>
```

and in `lightbox.scss`:

```scss
  &__link {
    display: block;
    padding: 0;
    border: 0;
    border-bottom: 1px solid transparent;
    background: none;
    text-align: left;
    transition:
      color 0.3s,
      border-color 0.3s;

    &:hover {
      border-color: rgb(255 200 107 / 50%);
      color: var(--lamp);
    }
  }
```

(`goArchive` ends the photo window at once; the photo does not fly back — it is leaving for the archive.)

- [ ] **Step 3: Link the timeline**

In `src/features/timeline/Timeline.tsx` (import `goArchive`), `onYear` becomes:

```ts
  const onYear = (year: number) => {
    const result = director.clickYear(year);
    if (result === 'empty') flash('No albums that year');
    else if (result === 'open') goArchive({ kind: 'year', year });
  };
```

- [ ] **Step 4: Run the check and commit**

Run: `npm run check`
Expected: PASS.

```bash
git add src/features
git commit -m "feat(archive): link the panel, the photo window and the timeline into the archive"
```

---

### Task 6: Check it in the browser

- [ ] **Step 1:** `npm run check && npm run build` — PASS.
- [ ] **Step 2:** With `npm run dev`, write down what you saw:
  1. The panel's city name opens the city page: albums grouped by year, latest first, as folders that fan out on hover. The globe stops (`__globe.state().worldNow` still). Tabs switch sections; ✕ closes; ← and Esc step back.
  2. Trips: 23 cards, newest first ("Japan in autumn" first). A trip page: `00 Start home · Kyiv, Ukraine`, each place once with its folders, `NN End home · Kyiv, Ukraine`; Show on map.
  3. An album page: the photo grid with likes, comments and captions; a tile opens the photo window over the archive and closes back into the tile; Esc closes the photo, then steps back.
  4. Show on map from a year: the archive closes, the year plays; when it ends by itself, 5 s later the year page fades back in slowly. Repeat and press ❚❚ midway: it does not come back.
  5. Show on map from a trip: the plane flies from home through the trip and home; the room shows; 5 s later the trip page returns.
  6. Show on map from an album: its place in focus, no autoplay, no return.
  7. The timeline: the picked year clicked again opens the year page. The panel: the current year again opens the city. The photo window: country, city, album open their pages.
  8. At 390 × 844 the archive shows two columns of cards, the tabs scroll.
