# Travel globe, plan 5: owner mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the read-only demo into an archive the owner can log into, edit and keep: login with a home base, a repository behind localStorage and IndexedDB, forms for trips, albums and photos, edit buttons in the archive, and a README that describes the new app.

**Architecture:** A `Repository` is the single storage seam: `demo-repository` (logged out, read-only, built from `buildDemo`) and `local-repository` (the owner: the graph in localStorage, photo blobs in IndexedDB). Every change runs as a pure edit on `ArchiveData` (`src/data/edits.ts`), then `relinkInto` rebuilds the linked graph **in the same `Archive` object**, so the director and the engine — which read `archive.albums` every frame — need no change; a revision counter in a store tells React to render again. Forms are one more layer in the app state, above the photo window in the Esc chain.

**Tech Stack:** React 19, TypeScript 6 strict, Vite 8, SCSS/BEM, Vitest (node), localStorage + IndexedDB, canvas `toBlob` for resizing.

**Spec:** `docs/design/2026-09-29-travel-globe.md` (sections 2, 6, 7, 8); prototype `docs/design/prototype/flight.html` and `atlas-data.js`.

## Global Constraints

- Every user-visible string in English, quiet and plain; comments explain *why*, not *what*.
- TypeScript strict with `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`: an optional field is omitted, not set to `undefined`; every index read is checked.
- Tests are Vitest in the node environment, named `*.test.ts` next to the code. No DOM-only code in tested modules: IndexedDB, canvas and `URL.createObjectURL` live in thin untested shells.
- localStorage keys go through `@/lib/storage` (prefix `cloudpix:`); IndexedDB database `cloudpix`, store `photos`.
- Photos are resized to at most 1600 px on the long side, JPEG quality 0.86, before they are stored.
- Destructive buttons ask once more before acting ("Delete it?"), and revert after 3 s.
- `npm run check` (tsc + eslint + vitest) and `npm run build` must pass at the end of every task.
- Never push to `main`: every push there deploys. Merge only when the user says so.

## Review Focus

1. Kept JSON edited by hand or written by an older build must not break the page: `cleanArchive` drops anything malformed and falls back to the demo copy (Task 3).
2. A photo whose blob is missing from IndexedDB (cleared site data) must render as a blank tile, never as a broken page (Task 3).
3. An edit while an album is in focus or a tour is playing must not leave the director pointing at an index that no longer exists (Task 4).
4. Two cities with the same slug in different countries (Task 2 `cityFor`) must not merge into one light.
5. Logging out must leave the owner's archive untouched in storage and show the demo again (Task 4).

---

### Task 1: The place picker list

**Files:**
- Create: `src/data/places.ts`
- Test: `src/data/places.test.ts`

**Interfaces:**
- Consumes: `Archive` from `@/data/archive`, `Place` from `@/data/types`.
- Produces: `GAZETTEER: Place[]`; `interface PickedPlace extends Place { cityKey?: string }`; `searchPlaces(archive: Archive, query: string): PickedPlace[]` (at most 8, places already on the map first).

- [ ] **Step 1: Write the failing test**

```ts
// src/data/places.test.ts
import { describe, expect, it } from 'vitest';
import { linkArchive } from './archive';
import { GAZETTEER, searchPlaces } from './places';
import type { ArchiveData } from './types';

const data = (): ArchiveData => ({
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
            { id: 'a1', title: 'Roofs', year: 2022, month: 5, day: 3, time: '10:00', photoCount: 2, photos: [] },
          ],
        },
      ],
    },
  ],
  trips: [],
});

describe('searchPlaces', () => {
  it('puts the places already on the map first', () => {
    const found = searchPlaces(linkArchive(data()), '');
    expect(found[0]).toMatchObject({ name: 'Paris', country: 'France', cityKey: 'paris' });
    expect(found).toHaveLength(8);
  });

  it('lists a city on the map once, not twice', () => {
    const found = searchPlaces(linkArchive(data()), 'paris');
    expect(found.filter((place) => place.name === 'Paris')).toHaveLength(1);
    expect(found[0]?.cityKey).toBe('paris');
  });

  it('matches the country as well as the city', () => {
    const found = searchPlaces(linkArchive(data()), 'japan');
    expect(found.map((place) => place.name)).toContain('Tokyo');
  });

  it('gives every gazetteer place a country code the world map knows', () => {
    for (const place of GAZETTEER) {
      expect(place.countryId).toMatch(/^\d{3}$/);
    }
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npx vitest run src/data/places.test.ts`
Expected: FAIL — cannot resolve `./places`.

- [ ] **Step 3: Write `src/data/places.ts`**

```ts
import type { Archive } from './archive';
import type { Place } from './types';

/** A place the picker offers: from the map (then it carries its city key) or from the list. */
export interface PickedPlace extends Place {
  cityKey?: string;
}

// [name, country, ISO 3166 numeric, lat, lon] — about 70 cities, enough to pick a home base.
const RAW: [string, string, string, number, number][] = [
  ['Kyiv', 'Ukraine', '804', 50.45, 30.52], ['Lviv', 'Ukraine', '804', 49.84, 24.03], ['Odesa', 'Ukraine', '804', 46.48, 30.72],
  ['Warsaw', 'Poland', '616', 52.23, 21.01], ['Kraków', 'Poland', '616', 50.06, 19.94], ['Berlin', 'Germany', '276', 52.52, 13.4],
  ['Munich', 'Germany', '276', 48.14, 11.58], ['Hamburg', 'Germany', '276', 53.55, 9.99], ['Prague', 'Czechia', '203', 50.08, 14.44],
  ['Vienna', 'Austria', '040', 48.21, 16.37], ['Budapest', 'Hungary', '348', 47.5, 19.04], ['Amsterdam', 'Netherlands', '528', 52.37, 4.9],
  ['Brussels', 'Belgium', '056', 50.85, 4.35], ['London', 'United Kingdom', '826', 51.51, -0.13], ['Edinburgh', 'United Kingdom', '826', 55.95, -3.19],
  ['Dublin', 'Ireland', '372', 53.35, -6.26], ['Paris', 'France', '250', 48.86, 2.35], ['Nice', 'France', '250', 43.7, 7.27],
  ['Lyon', 'France', '250', 45.76, 4.84], ['Zurich', 'Switzerland', '756', 47.38, 8.54], ['Milan', 'Italy', '380', 45.46, 9.19],
  ['Naples', 'Italy', '380', 40.85, 14.27], ['Rome', 'Italy', '380', 41.9, 12.5], ['Madrid', 'Spain', '724', 40.42, -3.7],
  ['Valencia', 'Spain', '724', 39.47, -0.38], ['Barcelona', 'Spain', '724', 41.39, 2.17], ['Lisbon', 'Portugal', '620', 38.72, -9.14],
  ['Athens', 'Greece', '300', 37.98, 23.73], ['Istanbul', 'Turkey', '792', 41.01, 28.98], ['Copenhagen', 'Denmark', '208', 55.68, 12.57],
  ['Stockholm', 'Sweden', '752', 59.33, 18.07], ['Oslo', 'Norway', '578', 59.91, 10.75], ['Helsinki', 'Finland', '246', 60.17, 24.94],
  ['Tallinn', 'Estonia', '233', 59.44, 24.75], ['Riga', 'Latvia', '428', 56.95, 24.11], ['Vilnius', 'Lithuania', '440', 54.69, 25.28],
  ['Tbilisi', 'Georgia', '268', 41.72, 44.79], ['Yerevan', 'Armenia', '051', 40.18, 44.51], ['Dubai', 'United Arab Emirates', '784', 25.2, 55.27],
  ['Cairo', 'Egypt', '818', 30.04, 31.24], ['Marrakesh', 'Morocco', '504', 31.63, -8.0], ['Cape Town', 'South Africa', '710', -33.92, 18.42],
  ['Nairobi', 'Kenya', '404', -1.29, 36.82], ['Delhi', 'India', '356', 28.61, 77.21], ['Mumbai', 'India', '356', 19.08, 72.88],
  ['Bangkok', 'Thailand', '764', 13.76, 100.5], ['Singapore', 'Singapore', '702', 1.35, 103.82], ['Bali', 'Indonesia', '360', -8.65, 115.22],
  ['Seoul', 'South Korea', '410', 37.57, 126.98], ['Tokyo', 'Japan', '392', 35.68, 139.69], ['Kyoto', 'Japan', '392', 35.01, 135.77],
  ['Beijing', 'China', '156', 39.9, 116.4], ['Hong Kong', 'China', '156', 22.32, 114.17], ['Sydney', 'Australia', '036', -33.87, 151.21],
  ['Melbourne', 'Australia', '036', -37.81, 144.96], ['Auckland', 'New Zealand', '554', -36.85, 174.76], ['New York', 'United States', '840', 40.71, -74.0],
  ['Los Angeles', 'United States', '840', 34.05, -118.24], ['San Francisco', 'United States', '840', 37.77, -122.42], ['Chicago', 'United States', '840', 41.88, -87.63],
  ['Miami', 'United States', '840', 25.76, -80.19], ['Toronto', 'Canada', '124', 43.65, -79.38], ['Vancouver', 'Canada', '124', 49.28, -123.12],
  ['Mexico City', 'Mexico', '484', 19.43, -99.13], ['Havana', 'Cuba', '192', 23.11, -82.37], ['Bogotá', 'Colombia', '170', 4.71, -74.07],
  ['Lima', 'Peru', '604', -12.05, -77.04], ['Cusco', 'Peru', '604', -13.53, -71.97], ['Rio de Janeiro', 'Brazil', '076', -22.91, -43.17],
  ['Buenos Aires', 'Argentina', '032', -34.6, -58.38], ['Santiago', 'Chile', '152', -33.45, -70.67], ['Reykjavík', 'Iceland', '352', 64.15, -21.94],
];

export const GAZETTEER: Place[] = RAW.map(([name, country, countryId, lat, lon]) => ({
  name,
  country,
  countryId,
  lat,
  lon,
}));

const LIMIT = 8;

/** The places to pick from: the ones already on the map first, then the built-in list. */
export const searchPlaces = (archive: Archive, query: string): PickedPlace[] => {
  const mine: PickedPlace[] = archive.countries.flatMap((country) =>
    country.cities.map((city) => ({
      name: city.name,
      country: country.name,
      countryId: country.id,
      lat: city.lat,
      lon: city.lon,
      cityKey: city.key,
    })),
  );
  const seen = new Set(mine.map((place) => `${place.name}|${place.country}`));
  const all = [...mine, ...GAZETTEER.filter((place) => !seen.has(`${place.name}|${place.country}`))];
  const needle = query.trim().toLowerCase();
  const hits = needle
    ? all.filter(
        (place) =>
          place.name.toLowerCase().includes(needle) || place.country.toLowerCase().includes(needle),
      )
    : all;
  return hits.slice(0, LIMIT);
};
```

- [ ] **Step 4: Run the test**

Run: `npx vitest run src/data/places.test.ts`
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add src/data/places.ts src/data/places.test.ts
git commit -m "feat(data): add the place picker list and its search"
```

---

### Task 2: Edits on the stored graph

**Files:**
- Create: `src/data/edits.ts`
- Test: `src/data/edits.test.ts`

**Interfaces:**
- Consumes: `ArchiveData`, `AlbumData`, `CityData`, `PhotoRef`, `Trip`, `Endpoint`, `Id` from `@/data/types`; `slugOf` from `@/data/order`; `photoKey` from `@/data/social`; `PickedPlace` from `@/data/places`.
- Produces:
  - `freshId(prefix: string, now?: number, random?: () => number): Id`
  - `cityFor(data: ArchiveData, place: PickedPlace): CityData`
  - `AlbumFields = { title: string; year: number; month: number; day: number; time: string; place: PickedPlace; tripId: string | null }`
  - `addAlbum(data, id: Id, fields: AlbumFields): AlbumData`
  - `updateAlbum(data, albumId: Id, fields: AlbumFields): void`
  - `deleteAlbum(data, albumId: Id): PhotoRef[]`
  - `addPhotos(data, albumId: Id, refs: PhotoRef[]): void`
  - `removePhoto(data, albumId: Id, key: string): PhotoRef | null`
  - `setCaption(data, albumId: Id, key: string, text: string): void`
  - `TripFields = { name: string; start: Endpoint; end: Endpoint; albumIds: Id[] }`
  - `addTrip(data, id: Id, fields: TripFields): Trip`
  - `updateTrip(data, tripId: Id, fields: TripFields): void`
  - `deleteTrip(data, tripId: Id): void`

- [ ] **Step 1: Write the failing test**

```ts
// src/data/edits.test.ts
import { describe, expect, it } from 'vitest';
import {
  addAlbum,
  addPhotos,
  addTrip,
  cityFor,
  deleteAlbum,
  deleteTrip,
  freshId,
  removePhoto,
  setCaption,
  updateAlbum,
  updateTrip,
} from './edits';
import type { AlbumFields } from './edits';
import type { ArchiveData, PhotoRef } from './types';

const PARIS = { name: 'Paris', country: 'France', countryId: '250', lat: 48.86, lon: 2.35 };
const ROME = { name: 'Rome', country: 'Italy', countryId: '380', lat: 41.9, lon: 12.5 };

const fields = (over: Partial<AlbumFields> = {}): AlbumFields => ({
  title: 'Roofs',
  year: 2022,
  month: 5,
  day: 3,
  time: '10:00',
  place: PARIS,
  tripId: null,
  ...over,
});

const empty = (): ArchiveData => ({ countries: [], trips: [] });

describe('freshId', () => {
  it('makes an id with the prefix, the time and some noise', () => {
    expect(freshId('u', 1_700_000_000_000, () => 0.5)).toMatch(/^u[a-z0-9]+$/);
    expect(freshId('u', 1, () => 0.1)).not.toBe(freshId('u', 1, () => 0.9));
  });
});

describe('cityFor', () => {
  it('makes the country and the city when the place is new', () => {
    const data = empty();
    const city = cityFor(data, PARIS);
    expect(city).toMatchObject({ key: 'paris', name: 'Paris', albums: [] });
    expect(data.countries.map((c) => c.id)).toEqual(['250']);
  });

  it('gives back the city the place already points at', () => {
    const data = empty();
    const first = cityFor(data, PARIS);
    addAlbum(data, 'a1', fields());
    expect(cityFor(data, { ...PARIS, cityKey: 'paris' })).toBe(first);
    expect(data.countries).toHaveLength(1);
  });

  it('keeps two cities of the same name in different countries apart', () => {
    const data = empty();
    const one = cityFor(data, { name: 'Santiago', country: 'Chile', countryId: '152', lat: -33.45, lon: -70.67 });
    const two = cityFor(data, { name: 'Santiago', country: 'Cuba', countryId: '192', lat: 20.02, lon: -75.82 });
    expect(one).not.toBe(two);
    expect(one.key).not.toBe(two.key);
  });
});

describe('albums', () => {
  it('adds an album to its city with no photos yet', () => {
    const data = empty();
    const album = addAlbum(data, 'a1', fields());
    expect(album).toMatchObject({ id: 'a1', title: 'Roofs', photoCount: 0, photos: [] });
    expect(data.countries[0]?.cities[0]?.albums).toEqual([album]);
  });

  it('puts a new album into the trip it was given', () => {
    const data = empty();
    addTrip(data, 't1', { name: 'Spring', start: { home: true }, end: { home: true }, albumIds: [] });
    addAlbum(data, 'a1', fields({ tripId: 't1' }));
    expect(data.trips[0]?.albumIds).toEqual(['a1']);
  });

  it('moves the album when its place changes, and only then', () => {
    const data = empty();
    addAlbum(data, 'a1', fields());
    updateAlbum(data, 'a1', fields({ title: 'Roofs again' }));
    expect(data.countries).toHaveLength(1);
    updateAlbum(data, 'a1', fields({ place: ROME }));
    const cities = data.countries.flatMap((country) => country.cities);
    expect(cities.find((city) => city.key === 'paris')?.albums).toEqual([]);
    expect(cities.find((city) => city.key === 'rome')?.albums[0]?.title).toBe('Roofs');
  });

  it('takes the album out of its old trip when the trip changes', () => {
    const data = empty();
    addTrip(data, 't1', { name: 'Spring', start: { home: true }, end: { home: true }, albumIds: [] });
    addTrip(data, 't2', { name: 'Autumn', start: { home: true }, end: { home: true }, albumIds: [] });
    addAlbum(data, 'a1', fields({ tripId: 't1' }));
    updateAlbum(data, 'a1', fields({ tripId: 't2' }));
    expect(data.trips[0]?.albumIds).toEqual([]);
    expect(data.trips[1]?.albumIds).toEqual(['a1']);
  });

  it('deletes the album, drops it from its trip and hands back its photos', () => {
    const data = empty();
    addTrip(data, 't1', { name: 'Spring', start: { home: true }, end: { home: true }, albumIds: [] });
    addAlbum(data, 'a1', fields({ tripId: 't1' }));
    const own: PhotoRef = { kind: 'own', id: 'p1', name: 'one.jpg' };
    addPhotos(data, 'a1', [own]);
    expect(deleteAlbum(data, 'a1')).toEqual([own]);
    expect(data.countries[0]?.cities[0]?.albums).toEqual([]);
    expect(data.trips[0]?.albumIds).toEqual([]);
  });
});

describe('photos', () => {
  const withPhoto = (): ArchiveData => {
    const data = empty();
    addAlbum(data, 'a1', fields());
    addPhotos(data, 'a1', [{ kind: 'own', id: 'p1', name: 'one.jpg' }]);
    return data;
  };
  const albumOf = (data: ArchiveData) => data.countries[0]?.cities[0]?.albums[0];

  it('counts the photos it adds', () => {
    const data = withPhoto();
    expect(albumOf(data)).toMatchObject({ photoCount: 1 });
  });

  it('never counts fewer photos than it carries', () => {
    const data = empty();
    addAlbum(data, 'a1', fields());
    const album = albumOf(data);
    if (album) album.photoCount = 40;
    addPhotos(data, 'a1', [{ kind: 'own', id: 'p1', name: 'one.jpg' }]);
    expect(removePhoto(data, 'a1', 'p1')).toEqual({ kind: 'own', id: 'p1', name: 'one.jpg' });
    expect(albumOf(data)?.photoCount).toBe(40);
    expect(albumOf(data)?.photos).toEqual([]);
  });

  it('writes a caption, and an empty one takes it away', () => {
    const data = withPhoto();
    setCaption(data, 'a1', 'p1', '  Early light  ');
    expect(albumOf(data)?.photos[0]?.caption).toBe('Early light');
    setCaption(data, 'a1', 'p1', '   ');
    expect(albumOf(data)?.photos[0]).not.toHaveProperty('caption');
  });
});

describe('trips', () => {
  it('creates a trip with its albums and takes them from other trips', () => {
    const data = empty();
    addTrip(data, 't1', { name: 'Spring', start: { home: true }, end: { home: true }, albumIds: [] });
    addAlbum(data, 'a1', fields({ tripId: 't1' }));
    const trip = addTrip(data, 't2', {
      name: 'Autumn',
      start: { home: true },
      end: { cityKey: 'paris' },
      albumIds: ['a1'],
    });
    expect(trip.end).toEqual({ cityKey: 'paris' });
    expect(data.trips[0]?.albumIds).toEqual([]);
    expect(data.trips[1]?.albumIds).toEqual(['a1']);
  });

  it('rewrites a trip and leaves the albums alone when it is deleted', () => {
    const data = empty();
    addAlbum(data, 'a1', fields());
    addTrip(data, 't1', { name: 'Spring', start: { home: true }, end: { home: true }, albumIds: ['a1'] });
    updateTrip(data, 't1', { name: 'Spring break', start: { cityKey: 'paris' }, end: { home: true }, albumIds: [] });
    expect(data.trips[0]).toMatchObject({ name: 'Spring break', start: { cityKey: 'paris' }, albumIds: [] });
    deleteTrip(data, 't1');
    expect(data.trips).toEqual([]);
    expect(data.countries[0]?.cities[0]?.albums).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npx vitest run src/data/edits.test.ts`
Expected: FAIL — cannot resolve `./edits`.

- [ ] **Step 3: Write `src/data/edits.ts`**

```ts
import type { PickedPlace } from './places';
import { slugOf } from './order';
import { photoKey } from './social';
import type { AlbumData, ArchiveData, CityData, CountryData, Endpoint, Id, PhotoRef, Trip } from './types';

/** An id nothing else will take: the time in base 36 plus a little noise. */
export const freshId = (prefix: string, now = Date.now(), random: () => number = Math.random): Id =>
  `${prefix}${now.toString(36)}${Math.floor(random() * 1e6).toString(36)}`;

const countryFor = (data: ArchiveData, id: Id, name: string): CountryData => {
  const found = data.countries.find((country) => country.id === id || country.name === name);
  if (found) return found;
  const country: CountryData = { id, name, cities: [] };
  data.countries.push(country);
  return country;
};

const allCities = (data: ArchiveData): CityData[] =>
  data.countries.flatMap((country) => country.cities);

/** The city a picked place points at, made if it is new. A new place becomes a new light. */
export const cityFor = (data: ArchiveData, place: PickedPlace): CityData => {
  const country = countryFor(data, place.countryId, place.country);
  if (place.cityKey !== undefined) {
    const known = country.cities.find((city) => city.key === place.cityKey);
    if (known) return known;
  }
  // the key is the slug, kept apart per country: two Santiagos are two lights
  const base = slugOf(place.name);
  const mine = country.cities.find((city) => city.name === place.name);
  if (mine) return mine;
  const taken = new Set(allCities(data).map((city) => city.key));
  const key = taken.has(base) ? `${base}-${slugOf(place.country)}` : base;
  const city: CityData = { key, name: place.name, lat: place.lat, lon: place.lon, albums: [] };
  country.cities.push(city);
  return city;
};

const findAlbum = (data: ArchiveData, albumId: Id): { city: CityData; album: AlbumData } | null => {
  for (const city of allCities(data)) {
    const album = city.albums.find((one) => one.id === albumId);
    if (album) return { city, album };
  }
  return null;
};

const detach = (data: ArchiveData, albumId: Id) => {
  for (const trip of data.trips) {
    trip.albumIds = trip.albumIds.filter((id) => id !== albumId);
  }
};

const attach = (data: ArchiveData, albumId: Id, tripId: Id | null) => {
  detach(data, albumId);
  if (tripId === null) return;
  const trip = data.trips.find((one) => one.id === tripId);
  if (trip) trip.albumIds.push(albumId);
};

export interface AlbumFields {
  title: string;
  year: number;
  month: number;
  day: number;
  time: string;
  place: PickedPlace;
  tripId: Id | null;
}

export const addAlbum = (data: ArchiveData, id: Id, fields: AlbumFields): AlbumData => {
  const city = cityFor(data, fields.place);
  const album: AlbumData = {
    id,
    title: fields.title,
    year: fields.year,
    month: fields.month,
    day: fields.day,
    time: fields.time,
    photoCount: 0,
    photos: [],
  };
  city.albums.push(album);
  attach(data, id, fields.tripId);
  return album;
};

export const updateAlbum = (data: ArchiveData, albumId: Id, fields: AlbumFields): void => {
  const found = findAlbum(data, albumId);
  if (!found) return;
  const { city, album } = found;
  album.title = fields.title;
  album.year = fields.year;
  album.month = fields.month;
  album.day = fields.day;
  album.time = fields.time;
  const next = cityFor(data, fields.place);
  if (next !== city) {
    city.albums.splice(city.albums.indexOf(album), 1);
    next.albums.push(album);
  }
  attach(data, albumId, fields.tripId);
};

/** Deletes the album and hands back the photos, so the caller can drop their blobs. */
export const deleteAlbum = (data: ArchiveData, albumId: Id): PhotoRef[] => {
  const found = findAlbum(data, albumId);
  if (!found) return [];
  found.city.albums.splice(found.city.albums.indexOf(found.album), 1);
  detach(data, albumId);
  return found.album.photos;
};

export const addPhotos = (data: ArchiveData, albumId: Id, refs: PhotoRef[]): void => {
  const found = findAlbum(data, albumId);
  if (!found) return;
  found.album.photos.push(...refs);
  found.album.photoCount += refs.length;
};

/** Takes a photo out; a demo album that claims more photos than it carries keeps its claim. */
export const removePhoto = (data: ArchiveData, albumId: Id, key: string): PhotoRef | null => {
  const found = findAlbum(data, albumId);
  if (!found) return null;
  const index = found.album.photos.findIndex((photo) => photoKey(photo) === key);
  if (index < 0) return null;
  const [gone] = found.album.photos.splice(index, 1);
  found.album.photoCount = Math.max(found.album.photos.length, found.album.photoCount - 1);
  return gone ?? null;
};

export const setCaption = (data: ArchiveData, albumId: Id, key: string, text: string): void => {
  const found = findAlbum(data, albumId);
  const photo = found?.album.photos.find((one) => photoKey(one) === key);
  if (!photo) return;
  const caption = text.trim();
  if (caption) photo.caption = caption;
  else delete photo.caption;
};

export interface TripFields {
  name: string;
  start: Endpoint;
  end: Endpoint;
  albumIds: Id[];
}

export const addTrip = (data: ArchiveData, id: Id, fields: TripFields): Trip => {
  const trip: Trip = { id, name: fields.name, start: fields.start, end: fields.end, albumIds: [] };
  data.trips.push(trip);
  for (const albumId of fields.albumIds) attach(data, albumId, id);
  return trip;
};

export const updateTrip = (data: ArchiveData, tripId: Id, fields: TripFields): void => {
  const trip = data.trips.find((one) => one.id === tripId);
  if (!trip) return;
  trip.name = fields.name;
  trip.start = fields.start;
  trip.end = fields.end;
  trip.albumIds = [];
  for (const albumId of fields.albumIds) attach(data, albumId, tripId);
};

/** The trip goes; its albums stay where they are. */
export const deleteTrip = (data: ArchiveData, tripId: Id): void => {
  data.trips = data.trips.filter((trip) => trip.id !== tripId);
};
```

- [ ] **Step 4: Run the test**

Run: `npx vitest run src/data/edits.test.ts`
Expected: PASS, 13 tests.

- [ ] **Step 5: Commit**

```bash
git add src/data/edits.ts src/data/edits.test.ts
git commit -m "feat(data): add the owner's edits on the stored graph"
```

---

### Task 3: The repository: demo, local storage, blobs, resizing

**Files:**
- Create: `src/data/repository.ts`, `src/data/demo-repository.ts`, `src/data/local-repository.ts`, `src/data/blobs.ts`, `src/data/image.ts`
- Modify: `src/data/photos.ts` (own photos get their url from the blob registry)
- Test: `src/data/repository.test.ts`, `src/data/photos.test.ts`

**Interfaces:**
- Consumes: `buildDemo` from `@/data/demo`; `edits.ts`; `readJSON`/`writeJSON` from `@/lib/storage`.
- Produces:
  - `interface Repository { readonly editable: boolean; load(): Promise<ArchiveData>; save(data: ArchiveData): void; addPhoto(blob: Blob, name: string): Promise<PhotoRef>; dropPhotos(refs: PhotoRef[]): Promise<void>; clear(): Promise<void> }`
  - `cleanArchive(raw: unknown): ArchiveData | null`
  - `demoRepository(credits: Credit[]): Repository`
  - `localRepository(credits: Credit[]): Repository`
  - `blobs.ts`: `putPhoto(id, blob)`, `getPhoto(id)`, `deletePhoto(id)`, `dropDatabase()`, `rememberUrl(id, blob)`, `ownUrl(id): string | null`, `loadOwnUrls(data)`
  - `image.ts`: `shrink(file: Blob): Promise<Blob>`

- [ ] **Step 1: Write the failing test**

```ts
// src/data/repository.test.ts
import { describe, expect, it } from 'vitest';
import { cleanArchive } from './repository';

const good = {
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
              id: 'a1',
              title: 'Roofs',
              year: 2022,
              month: 5,
              day: 3,
              time: '10:00',
              photoCount: 2,
              photos: [{ kind: 'own', id: 'p1', name: 'one.jpg', caption: 'Light' }],
            },
          ],
        },
      ],
    },
  ],
  trips: [{ id: 't1', name: 'Spring', start: { home: true }, end: { cityKey: 'paris' }, albumIds: ['a1'] }],
};

describe('cleanArchive', () => {
  it('keeps a sound archive whole', () => {
    expect(cleanArchive(structuredClone(good))).toEqual(good);
  });

  it('turns anything that is not an archive into nothing', () => {
    expect(cleanArchive(null)).toBeNull();
    expect(cleanArchive('{}')).toBeNull();
    expect(cleanArchive({ trips: [] })).toBeNull();
  });

  it('drops the parts that are broken and keeps the rest', () => {
    const raw = structuredClone(good) as Record<string, unknown>;
    const countries = raw.countries as Record<string, unknown>[];
    countries.push({ id: 7, name: 'Nowhere', cities: [] });
    const city = (countries[0]?.cities as Record<string, unknown>[])[0] as Record<string, unknown>;
    (city.albums as Record<string, unknown>[]).push({ id: 'a2', title: 'No date' });
    (city.albums as Record<string, unknown>[])[0]!.photos = [
      { kind: 'own', id: 'p1', name: 'one.jpg', caption: 'Light' },
      { kind: 'stock' },
      { kind: 'ghost', id: 'p2' },
    ];
    (raw.trips as unknown[]).push({ id: 't2' });
    const clean = cleanArchive(raw);
    expect(clean?.countries).toHaveLength(1);
    expect(clean?.countries[0]?.cities[0]?.albums).toHaveLength(1);
    expect(clean?.countries[0]?.cities[0]?.albums[0]?.photos).toHaveLength(1);
    expect(clean?.trips).toHaveLength(1);
  });

  it('never lets a photo count fall below the photos that are there', () => {
    const raw = structuredClone(good);
    raw.countries[0]!.cities[0]!.albums[0]!.photoCount = -3;
    expect(cleanArchive(raw)?.countries[0]?.cities[0]?.albums[0]?.photoCount).toBe(1);
  });
});
```

And, in `src/data/photos.test.ts`, add:

```ts
import { rememberOwnUrl, forgetOwnUrls } from './blobs';

describe('photoUrl for the owner', () => {
  it('gives back the url the blob was registered under', () => {
    forgetOwnUrls();
    rememberOwnUrl('p1', 'blob:fake');
    expect(photoUrl({ kind: 'own', id: 'p1', name: 'one.jpg' })).toBe('blob:fake');
  });

  it('gives back nothing when the blob is gone, so the tile stays blank', () => {
    forgetOwnUrls();
    expect(photoUrl({ kind: 'own', id: 'p1', name: 'one.jpg' })).toBeNull();
  });
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `npx vitest run src/data/repository.test.ts src/data/photos.test.ts`
Expected: FAIL — cannot resolve `./repository`, cannot resolve `./blobs`.

- [ ] **Step 3: Write `src/data/blobs.ts`**

```ts
import type { ArchiveData, Id, PhotoRef } from './types';

const DB = 'cloudpix';
const STORE = 'photos';

/** Object urls of the owner's photos, by id. The UI reads them through `photoUrl`. */
const urls = new Map<Id, string>();

export const rememberOwnUrl = (id: Id, url: string): void => {
  urls.set(id, url);
};

export const ownUrl = (id: Id): string | null => urls.get(id) ?? null;

export const forgetOwnUrls = (): void => {
  for (const url of urls.values()) {
    try {
      URL.revokeObjectURL(url);
    } catch {
      // nothing to revoke in a browser that never made one
    }
  }
  urls.clear();
};

const open = (): Promise<IDBDatabase> =>
  new Promise((ok, no) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => ok(request.result);
    request.onerror = () => no(request.error);
  });

const run = async <T>(mode: IDBTransactionMode, fn: (store: IDBObjectStore) => IDBRequest<T>) => {
  const db = await open();
  return new Promise<T | undefined>((ok, no) => {
    const transaction = db.transaction(STORE, mode);
    const request = fn(transaction.objectStore(STORE));
    transaction.oncomplete = () => ok(request.result);
    transaction.onerror = () => no(transaction.error);
  });
};

export const putPhoto = (id: Id, blob: Blob): Promise<unknown> =>
  run('readwrite', (store) => store.put(blob, id));

export const deletePhoto = (id: Id): Promise<unknown> =>
  run('readwrite', (store) => store.delete(id));

export const dropDatabase = (): Promise<void> =>
  new Promise((ok) => {
    forgetOwnUrls();
    const request = indexedDB.deleteDatabase(DB);
    request.onsuccess = () => ok();
    request.onerror = () => ok();
    request.onblocked = () => ok();
  });

/** Makes a url for every own photo of the archive. A blob that is gone leaves a blank tile. */
export const loadOwnUrls = async (data: ArchiveData): Promise<void> => {
  const refs: PhotoRef[] = data.countries
    .flatMap((country) => country.cities)
    .flatMap((city) => city.albums)
    .flatMap((album) => album.photos);
  for (const ref of refs) {
    if (ref.kind !== 'own' || urls.has(ref.id)) continue;
    try {
      const blob = await run<Blob>('readonly', (store) => store.get(ref.id) as IDBRequest<Blob>);
      if (blob) rememberOwnUrl(ref.id, URL.createObjectURL(blob));
    } catch {
      // no database, no photo: the tile stays blank
    }
  }
};
```

- [ ] **Step 4: Write `src/data/image.ts`**

```ts
const LONG_SIDE = 1600;
const QUALITY = 0.86;

/** Photos are made smaller before they are kept: the long side at most 1600 px, JPEG. */
export const shrink = async (file: Blob): Promise<Blob> => {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, LONG_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext('2d')?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return new Promise((ok) => {
    canvas.toBlob((blob) => ok(blob ?? file), 'image/jpeg', QUALITY);
  });
};
```

- [ ] **Step 5: Write `src/data/repository.ts`**

```ts
import { buildDemo } from './demo';
import type { AlbumData, ArchiveData, CityData, CountryData, Credit, Endpoint, PhotoRef, Trip } from './types';

/** The single seam for storage. A backend swaps the implementation, not the app. */
export interface Repository {
  /** Can the owner change what is in it? */
  readonly editable: boolean;
  load(): Promise<ArchiveData>;
  save(data: ArchiveData): void;
  addPhoto(blob: Blob, name: string): Promise<PhotoRef>;
  dropPhotos(refs: PhotoRef[]): Promise<void>;
  /** Throws everything away: the archive starts again from the demo. */
  clear(): Promise<void>;
}

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const str = (value: unknown): value is string => typeof value === 'string';
const num = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

const cleanPhoto = (raw: unknown): PhotoRef | null => {
  if (!isObject(raw)) return null;
  const caption = str(raw.caption) ? { caption: raw.caption } : {};
  if (raw.kind === 'stock' && str(raw.file)) return { kind: 'stock', file: raw.file, ...caption };
  if (raw.kind === 'own' && str(raw.id) && str(raw.name))
    return { kind: 'own', id: raw.id, name: raw.name, ...caption };
  return null;
};

const cleanAlbum = (raw: unknown): AlbumData | null => {
  if (!isObject(raw)) return null;
  if (!str(raw.id) || !str(raw.title) || !str(raw.time)) return null;
  if (!num(raw.year) || !num(raw.month) || !num(raw.day)) return null;
  const photos = Array.isArray(raw.photos)
    ? raw.photos.map(cleanPhoto).filter((photo): photo is PhotoRef => photo !== null)
    : [];
  const claimed = num(raw.photoCount) ? Math.round(raw.photoCount) : 0;
  return {
    id: raw.id,
    title: raw.title,
    year: Math.round(raw.year),
    month: Math.round(raw.month),
    day: Math.round(raw.day),
    time: raw.time,
    photoCount: Math.max(photos.length, claimed),
    photos,
  };
};

const cleanCity = (raw: unknown): CityData | null => {
  if (!isObject(raw)) return null;
  if (!str(raw.key) || !str(raw.name) || !num(raw.lat) || !num(raw.lon)) return null;
  const albums = Array.isArray(raw.albums)
    ? raw.albums.map(cleanAlbum).filter((album): album is AlbumData => album !== null)
    : [];
  return { key: raw.key, name: raw.name, lat: raw.lat, lon: raw.lon, albums };
};

const cleanCountry = (raw: unknown): CountryData | null => {
  if (!isObject(raw) || !str(raw.id) || !str(raw.name)) return null;
  const cities = Array.isArray(raw.cities)
    ? raw.cities.map(cleanCity).filter((city): city is CityData => city !== null)
    : [];
  return { id: raw.id, name: raw.name, cities };
};

const cleanEnd = (raw: unknown): Endpoint | null => {
  if (!isObject(raw)) return null;
  if (raw.home === true) return { home: true };
  return str(raw.cityKey) ? { cityKey: raw.cityKey } : null;
};

const cleanTrip = (raw: unknown): Trip | null => {
  if (!isObject(raw) || !str(raw.id) || !str(raw.name)) return null;
  const start = cleanEnd(raw.start);
  const end = cleanEnd(raw.end);
  if (!start || !end) return null;
  const albumIds = Array.isArray(raw.albumIds) ? raw.albumIds.filter(str) : [];
  return { id: raw.id, name: raw.name, start, end, albumIds };
};

/** Kept JSON, maybe from an older build or an editing hand, made safe to use. */
export const cleanArchive = (raw: unknown): ArchiveData | null => {
  if (!isObject(raw) || !Array.isArray(raw.countries)) return null;
  const countries = raw.countries
    .map(cleanCountry)
    .filter((country): country is CountryData => country !== null);
  const trips = Array.isArray(raw.trips)
    ? raw.trips.map(cleanTrip).filter((trip): trip is Trip => trip !== null)
    : [];
  return { countries, trips };
};

export const freshDemo = (credits: Credit[]): ArchiveData => buildDemo(credits);
```

- [ ] **Step 6: Write `src/data/demo-repository.ts` and `src/data/local-repository.ts`**

```ts
// src/data/demo-repository.ts
import { buildDemo } from './demo';
import type { Repository } from './repository';
import type { Credit } from './types';

/** Logged out: the sample traveller, read-only, nothing kept. */
export const demoRepository = (credits: Credit[]): Repository => ({
  editable: false,
  load: () => Promise.resolve(buildDemo(credits)),
  save: () => {},
  addPhoto: () => Promise.reject(new Error('the demo keeps nothing')),
  dropPhotos: () => Promise.resolve(),
  clear: () => Promise.resolve(),
});
```

```ts
// src/data/local-repository.ts
import { readJSON, writeJSON } from '@/lib/storage';
import { deletePhoto, dropDatabase, loadOwnUrls, putPhoto, rememberOwnUrl } from './blobs';
import { buildDemo } from './demo';
import { freshId } from './edits';
import { cleanArchive } from './repository';
import type { Repository } from './repository';
import type { Credit, PhotoRef } from './types';

const KEY = 'archive';

/** The owner: the graph in localStorage, the photo files in IndexedDB. */
export const localRepository = (credits: Credit[]): Repository => ({
  editable: true,
  async load() {
    // the first login starts from a copy of the demo, so there is something to explore
    const data = cleanArchive(readJSON<unknown>(KEY, null)) ?? buildDemo(credits);
    await loadOwnUrls(data);
    return data;
  },
  save(data) {
    writeJSON(KEY, data);
  },
  async addPhoto(blob, name) {
    const id = freshId('p');
    await putPhoto(id, blob);
    rememberOwnUrl(id, URL.createObjectURL(blob));
    return { kind: 'own', id, name };
  },
  async dropPhotos(refs: PhotoRef[]) {
    for (const ref of refs) {
      if (ref.kind !== 'own') continue;
      try {
        await deletePhoto(ref.id);
      } catch {
        // the file is already gone; the archive no longer points at it either
      }
    }
  },
  async clear() {
    writeJSON(KEY, null);
    await dropDatabase();
  },
});
```

- [ ] **Step 7: Own photos get their url — modify `src/data/photos.ts`**

```ts
import { demoUrl } from '@/lib/assets';
import { ownUrl } from './blobs';
import type { City, Credit, PhotoRef } from './types';

/** A stock photo comes from the bundle; the owner's comes from the blob registered on load. */
export const photoUrl = (photo: PhotoRef): string | null =>
  photo.kind === 'stock' ? demoUrl(`photos/${photo.file}`) : ownUrl(photo.id);
```

- [ ] **Step 8: Run the tests**

Run: `npx vitest run src/data/repository.test.ts src/data/photos.test.ts`
Expected: PASS — 4 new repository tests, the photo tests including the two new ones.

- [ ] **Step 9: Run the whole check**

Run: `npm run check`
Expected: tsc, eslint and the whole suite pass.

- [ ] **Step 10: Commit**

```bash
git add src/data/repository.ts src/data/repository.test.ts src/data/demo-repository.ts src/data/local-repository.ts src/data/blobs.ts src/data/image.ts src/data/photos.ts src/data/photos.test.ts
git commit -m "feat(data): add the repository seam, the local store and photo resizing"
```

---

### Task 4: The session: who is logged in, and one live archive

**Files:**
- Modify: `src/data/archive.ts` (relink in place), `src/app/boot.ts` (pick the repository), `src/app/Stage.tsx` (let go of the focus after an edit)
- Create: `src/state/user.ts`, `src/state/owner.ts`
- Test: `src/data/archive.test.ts` (add), `src/state/user.test.ts`, `src/state/owner.test.ts`

**Interfaces:**
- Consumes: `Repository` from `@/data/repository`; `linkArchive` from `@/data/archive`.
- Produces:
  - `relinkInto(archive: Archive, data: ArchiveData): Archive`
  - `src/state/user.ts`: `cleanUser(raw: unknown): User | null`, `userStore: Store<{ user: User | null }>`, `logIn(user: User)`, `logOut()`, `saveAccount(patch: Partial<User>)`
  - `src/state/owner.ts`: `ownerStore: Store<{ rev: number }>`, `setSource(archive: Archive, repo: Repository)`, `canEdit(): boolean`, `repository(): Repository | null`, `editArchive(fn: (data: ArchiveData, repo: Repository) => void | Promise<void>): Promise<void>`

- [ ] **Step 1: Write the failing tests**

```ts
// src/data/archive.test.ts — add
import { linkArchive, relinkInto } from './archive';

describe('relinkInto', () => {
  it('rebuilds the graph in the same object, so everything holding it sees the change', () => {
    const data = demoish();                       // the file's existing fixture builder
    const archive = linkArchive(data);
    const before = archive.albums.length;
    data.countries[0]!.cities[0]!.albums.push({
      id: 'new',
      title: 'Later',
      year: 2030,
      month: 1,
      day: 1,
      time: '09:00',
      photoCount: 0,
      photos: [],
    });
    const same = relinkInto(archive, data);
    expect(same).toBe(archive);
    expect(archive.albums).toHaveLength(before + 1);
    expect(archive.albumById.get('new')?.title).toBe('Later');
  });
});
```

```ts
// src/state/user.test.ts
import { describe, expect, it } from 'vitest';
import { cleanUser, logIn, logOut, saveAccount, userStore } from './user';

const HOME = { name: 'Kyiv', country: 'Ukraine', countryId: '804', lat: 50.45, lon: 30.52 };

describe('cleanUser', () => {
  it('keeps a whole user', () => {
    expect(cleanUser({ name: 'Ada', email: 'a@b.c', home: HOME })).toEqual({
      name: 'Ada',
      email: 'a@b.c',
      home: HOME,
    });
  });

  it('turns anything else into nobody', () => {
    expect(cleanUser(null)).toBeNull();
    expect(cleanUser({ name: 'Ada' })).toBeNull();
    expect(cleanUser({ name: 'Ada', email: 'a@b.c', home: { name: 'Kyiv' } })).toBeNull();
  });
});

describe('the session', () => {
  it('logs in, changes the account and logs out again', () => {
    logIn({ name: 'Ada', email: 'a@b.c', home: HOME });
    expect(userStore.get().user?.name).toBe('Ada');
    saveAccount({ name: 'Ada L' });
    expect(userStore.get().user).toMatchObject({ name: 'Ada L', email: 'a@b.c' });
    logOut();
    expect(userStore.get().user).toBeNull();
  });

  it('changes nothing when nobody is logged in', () => {
    logOut();
    saveAccount({ name: 'Nobody' });
    expect(userStore.get().user).toBeNull();
  });
});
```

```ts
// src/state/owner.test.ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { linkArchive } from '@/data/archive';
import { addAlbum } from '@/data/edits';
import type { Repository } from '@/data/repository';
import type { ArchiveData } from '@/data/types';
import { canEdit, editArchive, ownerStore, setSource } from './owner';

const data = (): ArchiveData => ({ countries: [], trips: [] });
const PARIS = { name: 'Paris', country: 'France', countryId: '250', lat: 48.86, lon: 2.35 };
const fake = (editable: boolean): Repository => ({
  editable,
  load: () => Promise.resolve(data()),
  save: vi.fn(),
  addPhoto: vi.fn(),
  dropPhotos: vi.fn(),
  clear: vi.fn(),
});

describe('editArchive', () => {
  beforeEach(() => {
    ownerStore.set({ rev: 0 });
  });

  it('runs the edit, relinks the same archive, saves it and counts a change', async () => {
    const archive = linkArchive(data());
    const repo = fake(true);
    setSource(archive, repo);
    expect(canEdit()).toBe(true);
    await editArchive((current) => {
      addAlbum(current, 'a1', {
        title: 'Roofs',
        year: 2022,
        month: 5,
        day: 3,
        time: '10:00',
        place: PARIS,
        tripId: null,
      });
    });
    expect(archive.albums.map((album) => album.id)).toEqual(['a1']);
    expect(repo.save).toHaveBeenCalledWith(archive.data);
    expect(ownerStore.get().rev).toBe(1);
  });

  it('does nothing at all when the archive is the read-only demo', async () => {
    const archive = linkArchive(data());
    const repo = fake(false);
    setSource(archive, repo);
    expect(canEdit()).toBe(false);
    await editArchive((current) => {
      addAlbum(current, 'a1', {
        title: 'Roofs',
        year: 2022,
        month: 5,
        day: 3,
        time: '10:00',
        place: PARIS,
        tripId: null,
      });
    });
    expect(archive.albums).toEqual([]);
    expect(repo.save).not.toHaveBeenCalled();
    expect(ownerStore.get().rev).toBe(0);
  });
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `npx vitest run src/data/archive.test.ts src/state/user.test.ts src/state/owner.test.ts`
Expected: FAIL — `relinkInto` is not exported, `./user` and `./owner` do not resolve.

- [ ] **Step 3: Relink in place — modify `src/data/archive.ts`**

Keep the body of the current `linkArchive` as a private `build`, then:

```ts
export const linkArchive = (data: ArchiveData): Archive => build(data);

/**
 * Rebuilds the graph inside the archive that is already there. The director and the engine hold
 * this object and read it every frame, so an edit must not hand them a new one.
 */
export const relinkInto = (archive: Archive, data: ArchiveData): Archive =>
  Object.assign(archive, build(data));
```

- [ ] **Step 4: Write `src/state/user.ts`**

```ts
import type { Place, User } from '@/data/types';
import { readJSON, writeJSON } from '@/lib/storage';
import { createStore } from './store';

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const cleanPlace = (raw: unknown): Place | null => {
  if (!isObject(raw)) return null;
  const { name, country, countryId, lat, lon } = raw;
  if (typeof name !== 'string' || typeof country !== 'string' || typeof countryId !== 'string') {
    return null;
  }
  if (typeof lat !== 'number' || typeof lon !== 'number') return null;
  return { name, country, countryId, lat, lon };
};

/** Who the browser remembers. Anything else is nobody: the demo runs instead. */
export const cleanUser = (raw: unknown): User | null => {
  if (!isObject(raw)) return null;
  const home = cleanPlace(raw.home);
  if (typeof raw.name !== 'string' || typeof raw.email !== 'string' || !home) return null;
  return { name: raw.name, email: raw.email, home };
};

export const userStore = createStore<{ user: User | null }>({
  user: cleanUser(readJSON<unknown>('user', null)),
});

const keep = (user: User | null) => {
  userStore.set({ user });
  writeJSON('user', user);
};

// the password is never stored: there is no server to check it against yet
export const logIn = (user: User): void => keep(user);

export const logOut = (): void => keep(null);

export const saveAccount = (patch: Partial<User>): void => {
  const { user } = userStore.get();
  if (!user) return;
  keep({ ...user, ...patch });
};
```

- [ ] **Step 5: Write `src/state/owner.ts`**

```ts
import { relinkInto } from '@/data/archive';
import type { Archive } from '@/data/archive';
import type { Repository } from '@/data/repository';
import type { ArchiveData } from '@/data/types';
import { createStore } from './store';

/** Counts the changes the owner made: React reads it to render the archive again. */
export const ownerStore = createStore<{ rev: number }>({ rev: 0 });

let source: { archive: Archive; repo: Repository } | null = null;

export const setSource = (archive: Archive, repo: Repository): void => {
  source = { archive, repo };
};

export const canEdit = (): boolean => source?.repo.editable ?? false;

export const repository = (): Repository | null => source?.repo ?? null;

/** Runs one edit on the stored graph, relinks it in place, saves it and counts it. */
export const editArchive = async (
  fn: (data: ArchiveData, repo: Repository) => void | Promise<void>,
): Promise<void> => {
  if (!source || !source.repo.editable) return;
  const { archive, repo } = source;
  await fn(archive.data, repo);
  relinkInto(archive, archive.data);
  repo.save(archive.data);
  ownerStore.set({ rev: ownerStore.get().rev + 1 });
};
```

- [ ] **Step 6: Run the tests**

Run: `npx vitest run src/data/archive.test.ts src/state/user.test.ts src/state/owner.test.ts`
Expected: PASS.

- [ ] **Step 7: Pick the repository on boot — modify `src/app/boot.ts`**

```ts
import { demoRepository } from '@/data/demo-repository';
import { localRepository } from '@/data/local-repository';
import { setSource } from '@/state/owner';
import { userStore } from '@/state/user';

export const loadWorld = async (): Promise<World> => {
  const [topology, credits] = await Promise.all([
    fetchJson<WorldTopology>('countries-110m.json'),
    fetchJson<Credit[]>('photos.json'),
  ]);
  const earth = earthFromTopology(topology);
  const { user } = userStore.get();
  // logged out it is the demo traveller, read-only; logged in it is the owner's own archive
  const repo = user ? localRepository(credits) : demoRepository(credits);
  const archive = linkArchive(await repo.load());
  setSource(archive, repo);
  return {
    earth,
    lights: buildLights(earth.land),
    archive,
    home: user?.home ?? DEMO_HOME,
    credits: new Map(credits.map((credit) => [credit.file, credit])),
  };
};
```

- [ ] **Step 8: Let go of the focus after an edit — modify `src/app/Stage.tsx`**

```tsx
  const rev = useStore(ownerStore, (state) => state.rev);
  // an edit can move or remove the album in focus: the director lets go and the tour stops
  useEffect(() => {
    if (rev === 0) return;
    director.deselect();
    director.stop();
    appStore.set({ tour: null, lastTour: null });
  }, [rev, director]);
```

- [ ] **Step 9: Run the whole check and the build**

Run: `npm run check && npm run build`
Expected: both pass.

- [ ] **Step 10: Commit**

```bash
git add src/data/archive.ts src/data/archive.test.ts src/state/user.ts src/state/user.test.ts src/state/owner.ts src/state/owner.test.ts src/app/boot.ts src/app/Stage.tsx
git commit -m "feat(state): add the session, the live archive and the repository choice on boot"
```

---

### Task 5: The form layer in the app state

**Files:**
- Modify: `src/state/app-state.ts` (`form`), `src/state/layers.ts` (`openForm`, `closeForm`, `pausedFor`, `escapeTarget`), `src/features/keys/useKeys.ts`
- Test: `src/state/layers.test.ts` (add)

**Interfaces:**
- Produces:
  - `type FormView = { kind: 'login'; why: string | null } | { kind: 'account' } | { kind: 'trip'; id: string | null; albumIds: string[] } | { kind: 'album'; id: string | null; cityKey: string | null; tripId: string | null } | { kind: 'photo'; albumId: string; photoKey: string }`
  - `AppState.form: FormView | null`
  - `openForm(store, form: FormView)`, `closeForm(store)`
  - `EscapeTarget` gains `'form'`, first in the chain.

- [ ] **Step 1: Write the failing test**

```ts
// src/state/layers.test.ts — add
import { closeForm, openForm } from './layers';

describe('the form layer', () => {
  it('opens over everything, closes the menu and stops the world clock', () => {
    const store = createStore<AppState>({ ...INITIAL_STATE, menu: 'nav' });
    openForm(store, { kind: 'login', why: null });
    expect(store.get()).toMatchObject({ form: { kind: 'login' }, menu: null, paused: true });
    closeForm(store);
    expect(store.get()).toMatchObject({ form: null, paused: false });
  });

  it('leaves the clock stopped when the archive is still open under it', () => {
    const store = createStore<AppState>({ ...INITIAL_STATE, archive: { stack: [{ kind: 'trips' }], slow: false } });
    openForm(store, { kind: 'account' });
    closeForm(store);
    expect(store.get().paused).toBe(true);
  });

  it('Esc closes the form before the menu, the photo or the archive', () => {
    const state: AppState = {
      ...INITIAL_STATE,
      form: { kind: 'account' },
      menu: 'nav',
      archive: { stack: [{ kind: 'trips' }], slow: false },
    };
    expect(escapeTarget(state)).toBe('form');
    expect(escapeTarget({ ...state, form: null })).toBe('menu');
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npx vitest run src/state/layers.test.ts`
Expected: FAIL — `openForm` is not exported.

- [ ] **Step 3: Add the layer — modify `src/state/app-state.ts`**

```ts
/** A modal sheet over everything: logging in, the account, a trip, an album, a photo. */
export type FormView =
  | { kind: 'login'; why: string | null }
  | { kind: 'account' }
  | { kind: 'trip'; id: string | null; albumIds: string[] }
  | { kind: 'album'; id: string | null; cityKey: string | null; tripId: string | null }
  | { kind: 'photo'; albumId: string; photoKey: string };
```

Add `form: FormView | null;` to `AppState` (documented: "The form sheet, open over everything") and `form: null` to `INITIAL_STATE`.

- [ ] **Step 4: Add the actions — modify `src/state/layers.ts`**

```ts
/** The world clock stops while a form, the photo window or the archive is open. */
export const pausedFor = (state: AppState): boolean =>
  state.form !== null || state.photo !== null || state.archive !== null;

export const openForm = (store: AppStore, form: FormView) => {
  store.set({ form, menu: null });
  store.set({ paused: pausedFor(store.get()) });
};

export const closeForm = (store: AppStore) => {
  store.set({ form: null });
  store.set({ paused: pausedFor(store.get()) });
};

/** What Esc closes, innermost first: form, menu, photo, archive (one step), the journey. */
export type EscapeTarget = 'form' | 'menu' | 'photo' | 'archive' | 'journey';

export const escapeTarget = (state: AppState): EscapeTarget =>
  state.form ? 'form' : state.menu ? 'menu' : state.photo ? 'photo' : state.archive ? 'archive' : 'journey';
```

- [ ] **Step 5: Esc and the keys — modify `src/features/keys/useKeys.ts`**

In the `Escape` branch, before the menu:

```ts
        if (layer === 'form') closeForm(appStore);
        else if (layer === 'menu') appStore.set({ menu: null });
```

And right after `const state = appStore.get();`, so a form swallows the rest of the keys:

```ts
      // a form is modal: only Esc reaches past it
      if (state.form && event.key !== 'Escape') return;
```

- [ ] **Step 6: Run the tests**

Run: `npx vitest run src/state/layers.test.ts`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/state/app-state.ts src/state/layers.ts src/state/layers.test.ts src/features/keys/useKeys.ts
git commit -m "feat(state): add the form layer and put it first in the Esc chain"
```

---

### Task 6: The sheet, the place field, logging in and the account

**Files:**
- Create: `src/features/forms/fields.ts`, `src/features/forms/fields.test.ts`, `src/features/forms/Sheet.tsx`, `src/features/forms/ConfirmButton.tsx`, `src/features/forms/PlaceField.tsx`, `src/features/forms/LoginForm.tsx`, `src/features/forms/AccountForm.tsx`, `src/features/forms/Forms.tsx`, `src/features/forms/forms.scss`
- Modify: `src/app/Stage.tsx` (mount `<Forms />`)

**Interfaces:**
- Consumes: `openForm`/`closeForm` from `@/state/layers`; `searchPlaces`/`PickedPlace` from `@/data/places`; `logIn`/`logOut`/`saveAccount`/`userStore` from `@/state/user`; `repository` from `@/state/owner`.
- Produces:
  - `fields.ts`: `dateInput(album: { year: number; month: number; day: number }): string`, `parseDate(value: string): { year: number; month: number; day: number } | null`, `placeLabel(place: PickedPlace): string`, `samePlace(a: PickedPlace | null, b: PickedPlace | null): boolean`
  - `Sheet({ title, lead, children, onClose })`, `ConfirmButton({ label, ask, onConfirm })`, `PlaceField({ id, label, archive, value, onPick })`, `Forms({ world })`

- [ ] **Step 1: Write the failing test**

```ts
// src/features/forms/fields.test.ts
import { describe, expect, it } from 'vitest';
import { dateInput, parseDate, placeLabel, samePlace } from './fields';

const PARIS = { name: 'Paris', country: 'France', countryId: '250', lat: 48.86, lon: 2.35 };

describe('the form fields', () => {
  it('writes a date the way an input wants it', () => {
    expect(dateInput({ year: 2022, month: 5, day: 3 })).toBe('2022-05-03');
  });

  it('reads a date back, and refuses one that is not a date', () => {
    expect(parseDate('2022-05-03')).toEqual({ year: 2022, month: 5, day: 3 });
    expect(parseDate('')).toBeNull();
    expect(parseDate('2022-13-40')).toBeNull();
  });

  it('shows a place as its city and country', () => {
    expect(placeLabel(PARIS)).toBe('Paris, France');
  });

  it('tells two places apart by name and country, not by object', () => {
    expect(samePlace(PARIS, { ...PARIS })).toBe(true);
    expect(samePlace(PARIS, { ...PARIS, country: 'Texas', countryId: '840' })).toBe(false);
    expect(samePlace(null, PARIS)).toBe(false);
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npx vitest run src/features/forms/fields.test.ts`
Expected: FAIL — cannot resolve `./fields`.

- [ ] **Step 3: Write `src/features/forms/fields.ts`**

```ts
import type { PickedPlace } from '@/data/places';
import { pad2 } from '@/lib/math';

export const dateInput = (when: { year: number; month: number; day: number }): string =>
  `${when.year}-${pad2(when.month)}-${pad2(when.day)}`;

/** "YYYY-MM-DD" from a date input, or nothing when the field is empty or impossible. */
export const parseDate = (value: string): { year: number; month: number; day: number } | null => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  return { year, month, day };
};

export const placeLabel = (place: PickedPlace): string => `${place.name}, ${place.country}`;

export const samePlace = (a: PickedPlace | null, b: PickedPlace | null): boolean =>
  a !== null && b !== null && a.name === b.name && a.country === b.country;
```

- [ ] **Step 4: Run the test**

Run: `npx vitest run src/features/forms/fields.test.ts`
Expected: PASS, 4 tests.

- [ ] **Step 5: Write `src/features/forms/Sheet.tsx`**

```tsx
import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import './forms.scss';

/** A modal sheet over everything. A press on the dim closes it; Esc is handled by `useKeys`. */
export function Sheet({
  title,
  lead,
  onClose,
  children,
}: {
  title: string;
  lead?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const sheet = useRef<HTMLDivElement>(null);
  const heading = `sheet-${title.replace(/\W+/g, '-').toLowerCase()}`;

  // the first field takes the cursor, once the sheet has slid in
  useEffect(() => {
    const id = setTimeout(() => {
      sheet.current?.querySelector<HTMLElement>('input:not([type=file]), textarea')?.focus();
    }, 80);
    return () => clearTimeout(id);
  }, []);

  return (
    <div
      className="modal is-on"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="sheet" ref={sheet} role="dialog" aria-modal="true" aria-labelledby={heading}>
        <h3 id={heading}>{title}</h3>
        {lead && <p className="sheet__lead">{lead}</p>}
        {children}
      </div>
    </div>
  );
}

export function Acts({ children }: { children: ReactNode }) {
  return <div className="sheet__acts">{children}</div>;
}
```

- [ ] **Step 6: Write `src/features/forms/ConfirmButton.tsx`**

```tsx
import { useEffect, useState } from 'react';

const BACK_MS = 3000;

/** A button for what cannot be undone: the first press asks, the second one does it. */
export function ConfirmButton({
  label,
  ask,
  onConfirm,
}: {
  label: string;
  ask: string;
  onConfirm: () => void;
}) {
  const [sure, setSure] = useState(false);

  useEffect(() => {
    if (!sure) return;
    const id = setTimeout(() => setSure(false), BACK_MS);
    return () => clearTimeout(id);
  }, [sure]);

  return (
    <button
      type="button"
      className={`sheet__btn is-danger${sure ? ' is-sure' : ''}`}
      onClick={() => (sure ? onConfirm() : setSure(true))}
    >
      {sure ? ask : label}
    </button>
  );
}
```

- [ ] **Step 7: Write `src/features/forms/PlaceField.tsx`**

```tsx
import { useState } from 'react';
import type { Archive } from '@/data/archive';
import { searchPlaces } from '@/data/places';
import type { PickedPlace } from '@/data/places';
import { placeLabel } from './fields';

/** A city field: the places already on the map first, then the built-in list. */
export function PlaceField({
  id,
  label,
  archive,
  value,
  onPick,
}: {
  id: string;
  label: string;
  archive: Archive;
  value: PickedPlace | null;
  onPick: (place: PickedPlace | null) => void;
}) {
  const [text, setText] = useState(value ? placeLabel(value) : '');
  const [open, setOpen] = useState(false);
  const found = searchPlaces(archive, value && placeLabel(value) === text ? '' : text);

  const choose = (place: PickedPlace) => {
    setText(placeLabel(place));
    setOpen(false);
    onPick(place);
  };

  return (
    <label className="sheet__field" htmlFor={id}>
      {label}
      <input
        id={id}
        autoComplete="off"
        placeholder="Start typing a city"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setOpen(true);
          onPick(null);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(event) => {
          const first = found[0];
          if (event.key === 'Enter' && !value && first) {
            event.preventDefault();
            choose(first);
          }
        }}
      />
      {open && found.length > 0 && (
        <div className="sheet__sugg">
          {found.map((place) => (
            <button
              key={`${place.name}|${place.country}`}
              type="button"
              // pointerdown, not click: the field's blur would take the list away first
              onPointerDown={(event) => {
                event.preventDefault();
                choose(place);
              }}
            >
              {place.name}
              <small>
                {place.country}
                {place.cityKey ? ' · on your map' : ''}
              </small>
            </button>
          ))}
        </div>
      )}
    </label>
  );
}
```

- [ ] **Step 8: Write `src/features/forms/LoginForm.tsx` and `AccountForm.tsx`**

```tsx
// src/features/forms/LoginForm.tsx
import { useState } from 'react';
import type { Archive } from '@/data/archive';
import type { PickedPlace } from '@/data/places';
import { logIn } from '@/state/user';
import { Acts, Sheet } from './Sheet';
import { PlaceField } from './PlaceField';

/** Logging in swaps the demo for the owner's archive, so the page opens again with it. */
export function LoginForm({ archive, why, onClose }: { archive: Archive; why: string | null; onClose: () => void }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [home, setHome] = useState<PickedPlace | null>(null);

  const submit = () => {
    if (!name.trim() || !home) return;
    const { name: city, country, countryId, lat, lon } = home;
    logIn({ name: name.trim(), email: email.trim(), home: { name: city, country, countryId, lat, lon } });
    location.reload();
  };

  return (
    <Sheet
      title="Log in"
      lead={`${why ? `${why} ` : ''}Your home base is where every trip starts and where it comes back to.`}
      onClose={onClose}
    >
      <label className="sheet__field" htmlFor="fName">
        Name
        <input id="fName" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="sheet__field" htmlFor="fMail">
        Email
        <input id="fMail" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="sheet__field" htmlFor="fPass">
        Password
        <input id="fPass" type="password" autoComplete="current-password" />
      </label>
      <PlaceField id="fHome" label="Home base" archive={archive} value={home} onPick={setHome} />
      <Acts>
        <button type="button" className="sheet__btn" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="sheet__btn is-main" disabled={!name.trim() || !home} onClick={submit}>
          Log in
        </button>
      </Acts>
      <p className="sheet__note">
        There is no server yet. Your archive stays in this browser; it starts as a copy of the demo,
        so there is something to play with.
      </p>
    </Sheet>
  );
}
```

```tsx
// src/features/forms/AccountForm.tsx
import { useState } from 'react';
import type { Archive } from '@/data/archive';
import type { PickedPlace } from '@/data/places';
import { repository } from '@/state/owner';
import { saveAccount, userStore } from '@/state/user';
import { ConfirmButton } from './ConfirmButton';
import { Acts, Sheet } from './Sheet';
import { PlaceField } from './PlaceField';

export function AccountForm({ archive, onClose }: { archive: Archive; onClose: () => void }) {
  const user = userStore.get().user;
  const [name, setName] = useState(user?.name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [pass, setPass] = useState('');
  const [again, setAgain] = useState('');
  const [home, setHome] = useState<PickedPlace | null>(user?.home ?? null);
  if (!user) return null;

  const mismatch = pass !== again;
  const submit = () => {
    if (!name.trim() || !home || mismatch) return;
    const { name: city, country, countryId, lat, lon } = home;
    saveAccount({ name: name.trim(), email: email.trim(), home: { name: city, country, countryId, lat, lon } });
    onClose();
    // the home base moves the house on the globe and every flight that starts from it
    location.reload();
  };

  return (
    <Sheet
      title="Account"
      lead="Your home base is where every trip starts and comes back to, unless a trip says otherwise."
      onClose={onClose}
    >
      <label className="sheet__field" htmlFor="fName">
        Name
        <input id="fName" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="sheet__field" htmlFor="fMail">
        Email
        <input id="fMail" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <div className="sheet__row">
        <label className="sheet__field" htmlFor="fPass">
          New password
          <input id="fPass" type="password" autoComplete="new-password" value={pass} onChange={(e) => setPass(e.target.value)} />
        </label>
        <label className="sheet__field" htmlFor="fPass2">
          Repeat it
          <input id="fPass2" type="password" autoComplete="new-password" value={again} onChange={(e) => setAgain(e.target.value)} />
        </label>
      </div>
      <PlaceField id="fHome" label="Home base" archive={archive} value={home} onPick={setHome} />
      <Acts>
        <ConfirmButton
          label="Reset archive to the demo"
          ask="Lose every change?"
          onConfirm={() => {
            void repository()
              ?.clear()
              .then(() => location.reload());
          }}
        />
        <button type="button" className="sheet__btn" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="sheet__btn is-main" disabled={!name.trim() || !home || mismatch} onClick={submit}>
          Save
        </button>
      </Acts>
      <p className="sheet__note">
        {mismatch ? 'The two passwords do not match.' : 'The password is not stored anywhere yet.'}
      </p>
    </Sheet>
  );
}
```

- [ ] **Step 9: Write `src/features/forms/Forms.tsx` and mount it**

```tsx
import type { World } from '@/app/boot';
import { appStore } from '@/state/app-state';
import { closeForm } from '@/state/layers';
import { useStore } from '@/state/store';
import { AccountForm } from './AccountForm';
import { LoginForm } from './LoginForm';

const close = () => closeForm(appStore);

/** The one form that is open, if any. */
export function Forms({ world }: { world: World }) {
  const form = useStore(appStore, (state) => state.form);
  if (!form) return null;
  switch (form.kind) {
    case 'login':
      return <LoginForm archive={world.archive} why={form.why} onClose={close} />;
    case 'account':
      return <AccountForm archive={world.archive} onClose={close} />;
    default:
      // the trip, album and photo sheets arrive in the next task
      return null;
  }
}
```

In `src/app/Stage.tsx`, render `<Forms world={world} />` last, after `<Lightbox />`.

- [ ] **Step 10: Write `src/features/forms/forms.scss`**

```scss
.modal {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgb(2 4 10 / 72%);
  backdrop-filter: blur(6px);
  opacity: 0;
  transition: opacity 0.35s var(--ease);

  &.is-on {
    opacity: 1;
  }
}

.sheet {
  width: min(460px, 100%);
  max-height: calc(100dvh - 32px);
  padding: 26px 26px 22px;
  overflow-y: auto;
  background: #0c1122;
  border-radius: 18px;
  box-shadow: 0 30px 80px rgb(0 0 0 / 60%), 0 0 0 1px rgb(255 255 255 / 7%);

  h3 {
    font-family: var(--font-family-display);
    font-size: 32px;
    font-style: italic;
    font-weight: 300;
    line-height: 1.05;
  }

  &__lead,
  &__note {
    margin-top: 8px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
  }

  &__field {
    display: block;
    position: relative;
    margin-top: 14px;
    color: var(--muted);
    font-size: 12px;
    letter-spacing: 0.04em;
    text-transform: uppercase;

    input,
    select,
    textarea {
      display: block;
      width: 100%;
      margin-top: 6px;
      padding: 10px 12px;
      border: 1px solid rgb(255 255 255 / 12%);
      border-radius: 10px;
      background: rgb(255 255 255 / 4%);
      color: var(--text);
      font: inherit;
      font-size: 15px;
      text-transform: none;
      letter-spacing: normal;

      &:focus-visible {
        outline: 2px solid var(--star);
      }
    }

    textarea {
      min-height: 76px;
      resize: vertical;
    }
  }

  &__row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  &__sugg {
    position: absolute;
    z-index: 2;
    left: 0;
    right: 0;
    max-height: 240px;
    overflow-y: auto;
    border-radius: 10px;
    background: #141a30;
    box-shadow: 0 18px 40px rgb(0 0 0 / 55%);

    button {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      width: 100%;
      padding: 9px 12px;
      border: 0;
      background: none;
      color: var(--text);
      font: inherit;
      text-align: left;
      text-transform: none;
      letter-spacing: normal;
      cursor: pointer;

      small {
        color: var(--muted);
      }

      &:hover,
      &:focus-visible {
        background: rgb(255 255 255 / 7%);
      }
    }
  }

  &__acts {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 20px;
  }

  &__btn {
    padding: 10px 16px;
    border: 1px solid rgb(255 255 255 / 14%);
    border-radius: 999px;
    background: none;
    color: var(--text);
    font: inherit;
    font-size: 14px;
    cursor: pointer;

    &.is-main {
      border-color: transparent;
      background: var(--lamp);
      color: #1a1204;
    }

    &.is-danger {
      margin-right: auto;
      border-color: rgb(255 120 120 / 35%);
      color: #ff9a9a;
    }

    &.is-sure {
      background: rgb(255 120 120 / 18%);
    }

    &:disabled {
      opacity: 0.45;
      cursor: default;
    }
  }
}

@media (width <= 560px) {
  .sheet__row {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 11: Check and commit**

Run: `npm run check && npm run build`
Expected: both pass.

```bash
git add src/features/forms src/app/Stage.tsx
git commit -m "feat(forms): add the modal sheet, the place picker, logging in and the account"
```

---

### Task 7: The trip, album and photo sheets

**Files:**
- Create: `src/features/forms/TripForm.tsx`, `src/features/forms/AlbumForm.tsx`, `src/features/forms/PhotoForm.tsx`, `src/features/forms/DropZone.tsx`, `src/features/forms/endpoints.ts`, `src/features/forms/endpoints.test.ts`
- Modify: `src/features/forms/Forms.tsx`

**Interfaces:**
- Consumes: `editArchive` from `@/state/owner`; `addAlbum`/`updateAlbum`/`deleteAlbum`/`addPhotos`/`removePhoto`/`setCaption`/`addTrip`/`updateTrip`/`deleteTrip`/`freshId` from `@/data/edits`; `shrink` from `@/data/image`; `photoKey` from `@/data/social`.
- Produces: `endpoints.ts`: `endpointOptions(archive: Archive, home: Place): { value: string; label: string }[]`, `endpointOf(value: string): Endpoint`, `endpointValue(end: Endpoint): string`.

- [ ] **Step 1: Write the failing test**

```ts
// src/features/forms/endpoints.test.ts
import { describe, expect, it } from 'vitest';
import { linkArchive } from '@/data/archive';
import type { ArchiveData } from '@/data/types';
import { endpointOf, endpointOptions, endpointValue } from './endpoints';

const HOME = { name: 'Kyiv', country: 'Ukraine', countryId: '804', lat: 50.45, lon: 30.52 };
const data: ArchiveData = {
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
          albums: [{ id: 'a1', title: 'Roofs', year: 2022, month: 5, day: 3, time: '10:00', photoCount: 0, photos: [] }],
        },
      ],
    },
  ],
  trips: [],
};

describe('the trip endpoints', () => {
  it('offers home first, then the cities on the map', () => {
    const options = endpointOptions(linkArchive(data), HOME);
    expect(options[0]).toEqual({ value: 'home', label: 'Home · Kyiv' });
    expect(options[1]).toEqual({ value: 'paris', label: 'Paris, France' });
  });

  it('reads a value back into an endpoint and writes it out again', () => {
    expect(endpointOf('home')).toEqual({ home: true });
    expect(endpointOf('paris')).toEqual({ cityKey: 'paris' });
    expect(endpointValue({ home: true })).toBe('home');
    expect(endpointValue({ cityKey: 'paris' })).toBe('paris');
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npx vitest run src/features/forms/endpoints.test.ts`
Expected: FAIL — cannot resolve `./endpoints`.

- [ ] **Step 3: Write `src/features/forms/endpoints.ts`**

```ts
import type { Archive } from '@/data/archive';
import type { Endpoint, Place } from '@/data/types';

/** Where a trip starts and ends: home, or any city already on the map. */
export const endpointOptions = (
  archive: Archive,
  home: Place,
): { value: string; label: string }[] => [
  { value: 'home', label: `Home · ${home.name}` },
  ...archive.cities
    .map((city) => ({ value: city.key, label: `${city.name}, ${city.country.name}` }))
    .sort((a, b) => a.label.localeCompare(b.label)),
];

export const endpointOf = (value: string): Endpoint =>
  value === 'home' ? { home: true } : { cityKey: value };

export const endpointValue = (end: Endpoint): string => ('home' in end ? 'home' : end.cityKey);
```

- [ ] **Step 4: Run the test**

Run: `npx vitest run src/features/forms/endpoints.test.ts`
Expected: PASS, 2 tests.

- [ ] **Step 5: Write `src/features/forms/DropZone.tsx`**

```tsx
import { useRef, useState } from 'react';

/** Photos to add: dropped on the zone, or chosen from the file dialog. */
export function DropZone({ onFiles }: { onFiles: (files: File[]) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const take = (list: FileList | null) => {
    const files = [...(list ?? [])].filter((file) => file.type.startsWith('image/'));
    if (files.length) onFiles(files);
  };

  return (
    <button
      type="button"
      className={`sheet__drop${over ? ' is-over' : ''}`}
      onClick={() => input.current?.click()}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        take(event.dataTransfer.files);
      }}
    >
      Drop photos here, or click to choose
      <input
        ref={input}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(event) => {
          take(event.target.files);
          event.target.value = '';
        }}
      />
    </button>
  );
}
```

- [ ] **Step 6: Write `src/features/forms/AlbumForm.tsx`**

```tsx
import { useState } from 'react';
import type { World } from '@/app/boot';
import { addAlbum, addPhotos, deleteAlbum, freshId, updateAlbum } from '@/data/edits';
import { shrink } from '@/data/image';
import type { PickedPlace } from '@/data/places';
import { editArchive, repository } from '@/state/owner';
import { ConfirmButton } from './ConfirmButton';
import { DropZone } from './DropZone';
import { dateInput, parseDate } from './fields';
import { Acts, Sheet } from './Sheet';
import { PlaceField } from './PlaceField';

const today = (): string => dateInput({ year: new Date().getFullYear(), month: new Date().getMonth() + 1, day: new Date().getDate() });

/** New or edit: a title, a place, a day and a trip. A new place becomes a new light. */
export function AlbumForm({
  world,
  id,
  cityKey,
  tripId,
  onClose,
}: {
  world: World;
  id: string | null;
  cityKey: string | null;
  tripId: string | null;
  onClose: () => void;
}) {
  const { archive } = world;
  const album = id ? (archive.albumById.get(id) ?? null) : null;
  const city = album?.city ?? (cityKey ? (archive.cityByKey.get(cityKey) ?? null) : null);
  const [title, setTitle] = useState(album?.title ?? '');
  const [date, setDate] = useState(album ? dateInput(album) : today());
  const [time, setTime] = useState(album?.time ?? '12:00');
  const [trip, setTrip] = useState(
    album ? (archive.trips.find((one) => one.albumIds.includes(album.id))?.id ?? '') : (tripId ?? ''),
  );
  const [place, setPlace] = useState<PickedPlace | null>(
    city
      ? {
          name: city.name,
          country: city.country.name,
          countryId: city.country.id,
          lat: city.lat,
          lon: city.lon,
          cityKey: city.key,
        }
      : null,
  );
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);

  const when = parseDate(date);
  const ready = Boolean(title.trim() && place && when) && !busy;

  const submit = async () => {
    if (!place || !when) return;
    setBusy(true);
    const fields = { title: title.trim(), ...when, time: time || '12:00', place, tripId: trip || null };
    await editArchive(async (data, repo) => {
      if (album) {
        updateAlbum(data, album.id, fields);
        return;
      }
      const made = addAlbum(data, freshId('a'), fields);
      // the files are made smaller and kept before the album is saved
      const refs = [];
      for (const file of files) refs.push(await repo.addPhoto(await shrink(file), file.name));
      addPhotos(data, made.id, refs);
    });
    onClose();
  };

  return (
    <Sheet
      title={album ? 'Edit album' : 'New album'}
      lead={
        album
          ? 'Change its name, place, date or trip.'
          : 'A place, a day, and the photos from it. A new place becomes a new light on the globe.'
      }
      onClose={onClose}
    >
      <label className="sheet__field" htmlFor="fName">
        Title
        <input id="fName" placeholder="Rooftops at sunset" value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <PlaceField id="fPlace" label="Place" archive={archive} value={place} onPick={setPlace} />
      <div className="sheet__row">
        <label className="sheet__field" htmlFor="fDate">
          Date
          <input id="fDate" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label className="sheet__field" htmlFor="fTime">
          Time
          <input id="fTime" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </label>
      </div>
      <label className="sheet__field" htmlFor="fTrip">
        Trip
        <select id="fTrip" value={trip} onChange={(e) => setTrip(e.target.value)}>
          <option value="">Not part of a trip</option>
          {archive.trips.map((one) => (
            <option key={one.id} value={one.id}>
              {one.name}
            </option>
          ))}
        </select>
      </label>
      {!album && (
        <>
          <DropZone onFiles={(added) => setFiles([...files, ...added])} />
          {files.length > 0 && <p className="sheet__note">{files.length} photo{files.length === 1 ? '' : 's'} ready.</p>}
        </>
      )}
      <Acts>
        {album && (
          <ConfirmButton
            label="Delete album"
            ask="Delete it and its photos?"
            onConfirm={() => {
              void editArchive(async (data, repo) => {
                await repo.dropPhotos(deleteAlbum(data, album.id));
              }).then(onClose);
            }}
          />
        )}
        <button type="button" className="sheet__btn" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="sheet__btn is-main" disabled={!ready} onClick={() => void submit()}>
          {busy ? 'Saving…' : album ? 'Save' : 'Create album'}
        </button>
      </Acts>
      {repository()?.editable === false && <p className="sheet__note">The demo keeps nothing.</p>}
    </Sheet>
  );
}
```

- [ ] **Step 7: Write `src/features/forms/TripForm.tsx`**

```tsx
import { useState } from 'react';
import type { World } from '@/app/boot';
import { addTrip, deleteTrip, freshId, updateTrip } from '@/data/edits';
import { MONTHS } from '@/lib/dates';
import { editArchive } from '@/state/owner';
import { ConfirmButton } from './ConfirmButton';
import { endpointOf, endpointOptions, endpointValue } from './endpoints';
import { Acts, Sheet } from './Sheet';

/** New or edit: a name, where it starts and ends, and the albums that belong to it. */
export function TripForm({
  world,
  id,
  albumIds,
  onClose,
}: {
  world: World;
  id: string | null;
  albumIds: string[];
  onClose: () => void;
}) {
  const { archive } = world;
  const trip = id ? (archive.trips.find((one) => one.id === id) ?? null) : null;
  const options = endpointOptions(archive, world.home);
  const [name, setName] = useState(trip?.name ?? '');
  const [start, setStart] = useState(endpointValue(trip?.start ?? { home: true }));
  const [end, setEnd] = useState(endpointValue(trip?.end ?? { home: true }));
  const [picked, setPicked] = useState<string[]>(trip ? [...trip.albumIds] : albumIds);
  const newest = [...archive.albums].reverse();

  const toggle = (albumId: string) =>
    setPicked(picked.includes(albumId) ? picked.filter((one) => one !== albumId) : [...picked, albumId]);

  const submit = () => {
    const fields = { name: name.trim(), start: endpointOf(start), end: endpointOf(end), albumIds: picked };
    void editArchive((data) => {
      if (trip) updateTrip(data, trip.id, fields);
      else addTrip(data, freshId('t'), fields);
    }).then(onClose);
  };

  return (
    <Sheet
      title={trip ? 'Edit trip' : 'New trip'}
      lead="A name, where it starts and ends, and the albums that belong to it."
      onClose={onClose}
    >
      <label className="sheet__field" htmlFor="fName">
        Name
        <input id="fName" placeholder="Summer holiday 2023" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <div className="sheet__row">
        <label className="sheet__field" htmlFor="fStart">
          Starts from
          <select id="fStart" value={start} onChange={(e) => setStart(e.target.value)}>
            {options.map((one) => (
              <option key={one.value} value={one.value}>
                {one.label}
              </option>
            ))}
          </select>
        </label>
        <label className="sheet__field" htmlFor="fEnd">
          Ends at
          <select id="fEnd" value={end} onChange={(e) => setEnd(e.target.value)}>
            {options.map((one) => (
              <option key={one.value} value={one.value}>
                {one.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="sheet__field">
        Albums
        <div className="sheet__checks">
          {newest.map((album) => (
            <label key={album.id}>
              <input type="checkbox" checked={picked.includes(album.id)} onChange={() => toggle(album.id)} />
              <span>
                {album.title} · {album.city.name}
              </span>
              <small>
                {album.day} {MONTHS[album.month - 1]} {album.year}
              </small>
            </label>
          ))}
        </div>
      </div>
      <Acts>
        {trip && (
          <ConfirmButton
            label="Delete trip"
            ask="Delete this trip? Its albums stay."
            onConfirm={() => {
              void editArchive((data) => deleteTrip(data, trip.id)).then(onClose);
            }}
          />
        )}
        <button type="button" className="sheet__btn" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="sheet__btn is-main" disabled={!name.trim()} onClick={submit}>
          {trip ? 'Save' : 'Create trip'}
        </button>
      </Acts>
    </Sheet>
  );
}
```

- [ ] **Step 8: Write `src/features/forms/PhotoForm.tsx`**

```tsx
import { useState } from 'react';
import type { World } from '@/app/boot';
import { removePhoto, setCaption } from '@/data/edits';
import { photoUrl } from '@/data/photos';
import { photoKey, photoNote } from '@/data/social';
import { editArchive } from '@/state/owner';
import { ConfirmButton } from './ConfirmButton';
import { Acts, Sheet } from './Sheet';

/** One photo: its own line, or away with it. */
export function PhotoForm({
  world,
  albumId,
  photoKey: key,
  onClose,
}: {
  world: World;
  albumId: string;
  photoKey: string;
  onClose: () => void;
}) {
  const album = world.archive.albumById.get(albumId);
  const photo = album?.photos.find((one) => photoKey(one) === key);
  const [caption, setText] = useState(photo?.caption ?? '');
  if (!photo) return null;
  const url = photoUrl(photo);

  return (
    <Sheet title="Edit photo" onClose={onClose}>
      {url && <img className="sheet__pic" src={url} alt="" />}
      <label className="sheet__field" htmlFor="fCap">
        Caption
        <textarea
          id="fCap"
          placeholder={photoNote(photo)}
          value={caption}
          onChange={(event) => setText(event.target.value)}
        />
      </label>
      <Acts>
        <ConfirmButton
          label="Delete photo"
          ask="Delete it from the album?"
          onConfirm={() => {
            void editArchive(async (data, repo) => {
              const gone = removePhoto(data, albumId, key);
              if (gone) await repo.dropPhotos([gone]);
            }).then(onClose);
          }}
        />
        <button type="button" className="sheet__btn" onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          className="sheet__btn is-main"
          onClick={() => {
            void editArchive((data) => setCaption(data, albumId, key, caption)).then(onClose);
          }}
        >
          Save
        </button>
      </Acts>
    </Sheet>
  );
}
```

- [ ] **Step 9: Route them — modify `src/features/forms/Forms.tsx`**

Replace the `default:` branch with:

```tsx
    case 'trip':
      return <TripForm world={world} id={form.id} albumIds={form.albumIds} onClose={close} />;
    case 'album':
      return <AlbumForm world={world} id={form.id} cityKey={form.cityKey} tripId={form.tripId} onClose={close} />;
    case 'photo':
      return <PhotoForm world={world} albumId={form.albumId} photoKey={form.photoKey} onClose={close} />;
```

- [ ] **Step 10: Add the styles the sheets need to `forms.scss`**

```scss
.sheet {
  &__drop {
    display: block;
    width: 100%;
    margin-top: 14px;
    padding: 22px 12px;
    border: 1px dashed rgb(255 255 255 / 20%);
    border-radius: 12px;
    background: none;
    color: var(--muted);
    font: inherit;
    font-size: 14px;
    cursor: pointer;

    &.is-over {
      border-color: var(--lamp);
      color: var(--text);
    }
  }

  &__checks {
    max-height: 190px;
    margin-top: 6px;
    overflow-y: auto;
    border: 1px solid rgb(255 255 255 / 10%);
    border-radius: 10px;

    label {
      display: flex;
      gap: 8px;
      align-items: baseline;
      padding: 7px 10px;
      color: var(--text);
      font-size: 14px;
      text-transform: none;
      letter-spacing: normal;
      cursor: pointer;

      small {
        margin-left: auto;
        color: var(--muted);
        white-space: nowrap;
      }
    }
  }

  &__pic {
    display: block;
    width: 100%;
    max-height: 280px;
    margin-top: 14px;
    border-radius: 12px;
    object-fit: cover;
  }
}
```

- [ ] **Step 11: Check and commit**

Run: `npm run check && npm run build`
Expected: both pass.

```bash
git add src/features/forms
git commit -m "feat(forms): add the trip, album and photo sheets"
```

---

### Task 8: The login gate, the edit buttons and the owner's menu

**Files:**
- Modify: `src/features/archive/links.ts` (gate), `src/features/archive/Archive.tsx` (edit buttons, render again after an edit), `src/features/archive/archive.scss`, `src/features/header/Header.tsx` (the owner's menu), `src/features/header/header.scss`
- Create: `src/features/header/HouseIcon.tsx`, `src/features/archive/links.test.ts`

**Interfaces:**
- Consumes: `canEdit` and `ownerStore` from `@/state/owner`; `userStore` from `@/state/user`; `openForm` from `@/state/layers`; `HOUSE`, `ROOF`, `GLASS` from `@/render/house`.
- Produces: `goArchive` asks a visitor to log in instead of opening the archive; `HouseIcon()`.

- [ ] **Step 1: Write the failing test**

```ts
// src/features/archive/links.test.ts
import { beforeEach, describe, expect, it } from 'vitest';
import { appStore, INITIAL_STATE } from '@/state/app-state';
import { logIn, logOut } from '@/state/user';
import { goArchive } from './links';

const HOME = { name: 'Kyiv', country: 'Ukraine', countryId: '804', lat: 50.45, lon: 30.52 };

describe('goArchive', () => {
  beforeEach(() => {
    appStore.set({ ...INITIAL_STATE });
  });

  it('asks a visitor to log in, and leaves the archive shut', () => {
    logOut();
    goArchive({ kind: 'trips' });
    expect(appStore.get().archive).toBeNull();
    expect(appStore.get().form).toMatchObject({ kind: 'login' });
    expect((appStore.get().form as { why: string }).why).toMatch(/archive/i);
  });

  it('opens the archive for the owner', () => {
    logIn({ name: 'Ada', email: 'a@b.c', home: HOME });
    goArchive({ kind: 'trips' });
    expect(appStore.get().archive?.stack).toEqual([{ kind: 'trips' }]);
    expect(appStore.get().form).toBeNull();
    logOut();
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npx vitest run src/features/archive/links.test.ts`
Expected: FAIL — the archive opens for a visitor too.

- [ ] **Step 3: Gate the way in — modify `src/features/archive/links.ts`**

```ts
import { closeForm, finishPhoto, openForm } from '@/state/layers';
import { userStore } from '@/state/user';

/** The one way into the archive from the main screen and the photo window. */
export const goArchive = (page: ArchivePage) => {
  if (!userStore.get().user) {
    // the demo has no archive of its own to show
    openForm(appStore, {
      kind: 'login',
      why: 'Log in to open your archive. Until then the globe runs a demo traveller.',
    });
    return;
  }
  if (appStore.get().photo) finishPhoto(appStore);
  closeForm(appStore);
  openArchive(appStore, page, true);
};
```

- [ ] **Step 4: Run the test**

Run: `npx vitest run src/features/archive/links.test.ts`
Expected: PASS, 2 tests.

- [ ] **Step 5: Edit buttons in the archive — modify `src/features/archive/Archive.tsx`**

At the top of `Archive`, so an edit shows at once:

```tsx
  useStore(ownerStore, (state) => state.rev);
  const owner = canEdit();
```

Give `Header` a second field and fill it in `headerOf` — keep `headerOf(data)` as it is and add a small function beside it:

```tsx
/** What the owner can do on this page. */
const editsOf = (data: PageData): { label: string; form: FormView }[] => {
  switch (data.kind) {
    case 'trips':
      return [{ label: '+ New trip', form: { kind: 'trip', id: null, albumIds: [] } }];
    case 'trip':
      return [
        { label: '✎ Edit trip', form: { kind: 'trip', id: data.journey.id, albumIds: [] } },
        { label: '+ New album', form: { kind: 'album', id: null, cityKey: null, tripId: data.journey.id } },
      ];
    case 'albums':
    case 'years':
    case 'year':
    case 'countries':
    case 'cities':
      return [{ label: '+ New album', form: { kind: 'album', id: null, cityKey: null, tripId: null } }];
    case 'country':
      return [{ label: '+ New album', form: { kind: 'album', id: null, cityKey: null, tripId: null } }];
    case 'city':
      return [{ label: '+ New album', form: { kind: 'album', id: null, cityKey: data.city.key, tripId: null } }];
    case 'album':
      return [{ label: '✎ Edit album', form: { kind: 'album', id: data.album.id, cityKey: null, tripId: null } }];
  }
};
```

A trip page edit must carry the trip's albums, so the sheet opens with them ticked — pass `albumIds: data.journey.albums.map((album) => album.id)` there.

In the `archive__acts` row, after "Show on map" (and render the row when either the map button or an edit exists):

```tsx
          {(header.map || owner) && (
            <div className="archive__acts">
              {header.map && (
                <button type="button" className="archive__btn is-star" onClick={() => header.map && showOnMap(director, header.map)}>
                  ◎ Show on map
                </button>
              )}
              {owner &&
                editsOf(data).map((edit) => (
                  <button
                    key={edit.label}
                    type="button"
                    className="archive__btn"
                    onClick={() => openForm(appStore, edit.form)}
                  >
                    {edit.label}
                  </button>
                ))}
            </div>
          )}
```

An album page also takes photos. Give `PhotoGrid` the owner flag and, under the grid, a drop zone that adds them:

```tsx
    case 'album':
      return <PhotoGrid album={data.album} owner={owner} />;
```

```tsx
function PhotoGrid({ album, owner }: { album: Album; owner: boolean }) {
  useStore(socialStore, (s) => s.byKey);
  const add = async (files: File[]) => {
    await editArchive(async (data, repo) => {
      const refs = [];
      for (const file of files) refs.push(await repo.addPhoto(await shrink(file), file.name));
      addPhotos(data, album.id, refs);
    });
  };
  return (
    <>
      {album.photos.map((photo, index) => {
        /* …the existing tile… */
      })}
      {owner && (
        <div className="archive__add">
          <DropZone onFiles={(files) => void add(files)} />
        </div>
      )}
    </>
  );
}
```

And each tile gets a pencil for the owner, inside `.archive__photo`, above the meta line:

```tsx
              {owner && (
                <button
                  type="button"
                  className="archive__pencil"
                  aria-label="Edit photo"
                  onClick={(event) => {
                    event.stopPropagation();
                    openForm(appStore, { kind: 'photo', albumId: album.id, photoKey: key });
                  }}
                >
                  ✎
                </button>
              )}
```

The tile itself is a `<button>`, so the pencil cannot be one inside it. Turn the tile into a `<div role="button" tabIndex={0}>` with `onClick` and an `onKeyDown` that opens the photo on Enter and Space, and keep the pencil a real button.

- [ ] **Step 6: Style them — add to `src/features/archive/archive.scss`**

```scss
.archive {
  &__pencil {
    position: absolute;
    z-index: 2;
    top: 8px;
    right: 8px;
    width: 30px;
    height: 30px;
    border: 0;
    border-radius: 50%;
    background: rgb(4 6 13 / 70%);
    color: var(--text);
    font-size: 14px;
    line-height: 1;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  &__pic:hover &__pencil,
  &__pencil:focus-visible {
    opacity: 1;
  }

  &__add {
    grid-column: 1 / -1;
  }
}
```

(`.archive__photo` already sets `position: relative`; if it does not, add it.)

- [ ] **Step 7: The owner's menu — create `src/features/header/HouseIcon.tsx`**

```tsx
import { GLASS, HOUSE, ROOF } from '@/render/house';

const numbers = HOUSE.parts
  .flatMap((part) => part.d.match(/-?[\d.]+ -?[\d.]+/g) ?? [])
  .map((pair) => pair.split(' ').map(Number));
const xs = numbers.map((pair) => pair[0] ?? 0);
const ys = numbers.map((pair) => pair[1] ?? 0);
const box = [Math.min(...xs) - 1, Math.min(...ys) - 1, Math.max(...xs) - Math.min(...xs) + 2, Math.max(...ys) - Math.min(...ys) + 2];

/** The same little house the globe draws at home, as a flat icon for the menu. */
export function HouseIcon() {
  const [[x1, y1], [x2, y2]] = HOUSE.roof;
  return (
    <svg className="header__house" viewBox={box.join(' ')} aria-hidden="true">
      <defs>
        <linearGradient id="menu-roof" gradientUnits="userSpaceOnUse" x1={x1} y1={y1} x2={x2} y2={y2}>
          <stop offset="0" stopColor="#5b44ab" />
          <stop offset="1" stopColor="#957fe6" />
        </linearGradient>
      </defs>
      {HOUSE.parts.map((part, index) => (
        <path
          key={index}
          d={part.d}
          fill={part.fill === ROOF ? 'url(#menu-roof)' : part.fill === GLASS ? '#ffd27a' : part.fill}
        />
      ))}
    </svg>
  );
}
```

- [ ] **Step 8: The menu items — modify `src/features/header/Header.tsx`**

Replace the disabled "Log in" block with:

```tsx
      <nav className={`header__menu header__nav${menu === 'nav' ? ' is-on' : ''}`} inert={menu !== 'nav'}>
        <NavMenu world={world} />
      </nav>
```

```tsx
function NavMenu({ world }: { world: World | null }) {
  const user = useStore(userStore, (state) => state.user);
  useStore(ownerStore, (state) => state.rev);

  if (!user) {
    return (
      <>
        <button
          type="button"
          className="header__item is-primary"
          onClick={() => openForm(appStore, { kind: 'login', why: null })}
        >
          Log in
        </button>
        <p>You are watching a demo traveller. Log in to keep your own trips, albums and photos.</p>
      </>
    );
  }

  return (
    <>
      <div className="header__who">
        <b>{user.name}</b>
        <span>
          <HouseIcon />
          <em>{`${user.home.name}, ${user.home.country}`}</em>
        </span>
      </div>
      <button type="button" className="header__item" onClick={() => goArchive({ kind: 'trips' })}>
        <span>Archive</span>
        <small>{plural(world?.archive.trips.length ?? 0, 'trip')}</small>
      </button>
      <button type="button" className="header__item" onClick={() => openForm(appStore, { kind: 'account' })}>
        <span>Account settings</span>
        <small>email, password, home</small>
      </button>
      <hr />
      <button
        type="button"
        className="header__item"
        onClick={() => {
          logOut();
          location.reload();
        }}
      >
        <span>Log out</span>
      </button>
    </>
  );
}
```

- [ ] **Step 9: Style the menu — add to `src/features/header/header.scss`**

```scss
.header {
  &__who {
    padding: 4px 14px 12px;

    b {
      display: block;
      font-size: 17px;
    }

    span {
      display: flex;
      gap: 6px;
      align-items: center;
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }

    em {
      font-style: normal;
    }
  }

  &__house {
    width: 18px;
    height: 18px;
  }

  hr {
    margin: 8px 0;
    border: 0;
    border-top: 1px solid rgb(255 255 255 / 10%);
  }
}
```

- [ ] **Step 10: Check, build and commit**

Run: `npm run check && npm run build`
Expected: both pass.

```bash
git add src/features/archive src/features/header
git commit -m "feat(owner): gate the archive behind logging in, add the edit buttons and the owner's menu"
```

---

### Task 9: A README for the new app, and a walk through the browser

**Files:**
- Modify: `README.md`
- Create: `scratchpad/pw/owner.mjs` (not committed: the scratchpad is outside the repo)

**Interfaces:** none.

- [ ] **Step 1: Walk the whole owner mode in a browser**

```bash
npm run dev -- --port 3001 &
```

Write `scratchpad/pw/owner.mjs` after the pattern of `scratchpad/pw/archive.mjs` (playwright-core, the Chromium in `~/.cache/ms-playwright/chromium-1243`, viewport 1440×900, console errors collected) and walk:

1. logged out: the burger menu shows "Log in"; a click on a caption link into the archive opens the login sheet instead of the archive, and the sheet says why;
2. log in as "Ada", home base "Lisbon": the page reloads, the house sits on Lisbon, the archive opens, the menu shows the name and the home;
3. new album: title, a place that is not on the map yet ("Reykjavík"), a date, two photos from disk (`page.setInputFiles` on the hidden input); the album page opens with two tiles, and the globe has a new light;
4. edit that album: change its title and its place to a city already on the map, and see the archive page follow;
5. photo: the pencil opens the sheet, a caption is saved and shows under the tile, then the photo is deleted (two presses);
6. new trip with those albums, "Show on map" plays it;
7. account: change the name, then "Reset archive to the demo" (two presses) and see the demo back with the owner still logged in;
8. log out: the demo traveller is back and the archive asks to log in again;
9. reload after step 3 without resetting: the own photos are still there (IndexedDB), and no console errors anywhere.

Expected: every line above holds. Anything that does not is a bug to fix here, each with a failing test first.

- [ ] **Step 2: Rewrite `README.md`**

Write it for someone who has never seen the app: what it is (a personal travel archive on a night globe), the two modes, what you can do (drag and throw the globe, scroll to zoom, the timeline range, tours, the album panel, the photo window, the archive, logging in and editing), how it works (the frame loop and the world clock; the blend projection from globe to flat map; the director as the brain of the journey; the store shared by React and the canvas; the repository seam with localStorage and IndexedDB), how to run it (`npm run dev`, `npm run check`, `npm run build`, Node 22.12+), where things live (the `src/` tree from the spec, trimmed to what exists), and what is not there yet (no server: likes, comments and photos live in this browser only). Keep the tone of the old README: plain, specific, no marketing. Replace the screenshot line with `docs/screenshot.jpg` only if a new screenshot has been taken; otherwise drop the image.

- [ ] **Step 3: Full check and build**

Run: `npm run check && npm run build`
Expected: both pass.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: rewrite the README for the travel globe"
```

- [ ] **Step 5: Stop the dev server**

```bash
pkill -f "[v]ite --port 3001" || true
```
