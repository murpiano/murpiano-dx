// Shared demo data for the three atlas prototypes: one person's travel memories.
// Photos come from Wikimedia Commons (see photos.json for authors and licenses).
window.ATLAS = (() => {
  const DATA = [
    { id: '724', name: 'Spain', cities: [
      { name: 'Barcelona', key: 'barcelona', lat: 41.39, lon: 2.17, albums: [['Gaudí & the sea', 2019, 3, 64], ['New Year on the roof', 2023, 12, 38], ['Sagrada Família, finally', 2023, 6, 52]] },
      { name: 'Madrid', key: 'madrid', lat: 40.42, lon: -3.70, albums: [['Prado afternoons', 2021, 10, 41]] },
      { name: 'Seville', key: 'seville', lat: 37.39, lon: -5.98, albums: [['Orange trees in March', 2024, 3, 69]] } ] },
    { id: '620', name: 'Portugal', cities: [
      { name: 'Lisbon', key: 'lisbon', lat: 38.72, lon: -9.14, albums: [['Tram 28', 2019, 4, 52], ['Pastéis and tiles', 2021, 8, 31]] },
      { name: 'Porto', key: 'porto', lat: 41.15, lon: -8.61, albums: [['Rain on the Douro', 2022, 11, 33]] } ] },
    { id: '380', name: 'Italy', cities: [
      { name: 'Rome', key: 'rome', lat: 41.9, lon: 12.5, albums: [['Seven hills, one week', 2018, 5, 88], ['Trastevere nights', 2024, 10, 44]] },
      { name: 'Florence', key: 'florence', lat: 43.77, lon: 11.25, albums: [['Duomo at dawn', 2018, 5, 27]] },
      { name: 'Venice', key: 'venice', lat: 45.44, lon: 12.33, albums: [['Fog and gondolas', 2025, 1, 46]] } ] },
    { id: '250', name: 'France', cities: [
      { name: 'Paris', key: 'paris', lat: 48.86, lon: 2.35, albums: [['First trip abroad', 2016, 7, 120], ['Paris again', 2022, 4, 35], ['Louvre at closing time', 2022, 4, 29], ['Montmartre sketches', 2025, 9, 40]] } ] },
    { id: '352', name: 'Iceland', cities: [
      { name: 'Reykjavík', key: 'reykjavik', lat: 64.15, lon: -21.94, albums: [['Midnight sun', 2020, 6, 58]] },
      { name: 'Vík', key: 'vik-i-myrdal', lat: 63.42, lon: -19.0, albums: [['Black sand', 2020, 6, 44]] } ] },
    { id: '578', name: 'Norway', cities: [
      { name: 'Bergen', key: 'bergen', lat: 60.39, lon: 5.32, albums: [['Fjords by ferry', 2021, 7, 61]] },
      { name: 'Tromsø', key: 'tromso', lat: 69.65, lon: 18.96, albums: [['Chasing the aurora', 2024, 1, 93]] } ] },
    { id: '392', name: 'Japan', cities: [
      { name: 'Tokyo', key: 'tokyo', lat: 35.68, lon: 139.69, albums: [['Neon and quiet', 2023, 4, 140], ['Shibuya crossing', 2025, 11, 63]] },
      { name: 'Kyoto', key: 'kyoto', lat: 35.01, lon: 135.77, albums: [['Sakura week', 2023, 4, 97], ['Autumn temples', 2025, 11, 54], ['Bamboo grove', 2023, 4, 38]] } ] },
    { id: '554', name: 'New Zealand', cities: [
      { name: 'Auckland', key: 'auckland', lat: -36.85, lon: 174.76, albums: [['Harbour city', 2024, 2, 29]] },
      { name: 'Queenstown', key: 'queenstown-new-zealand', lat: -45.03, lon: 168.66, albums: [['Southern Alps road trip', 2024, 2, 131]] } ] },
    { id: '268', name: 'Georgia', cities: [
      { name: 'Tbilisi', key: 'tbilisi', lat: 41.72, lon: 44.79, albums: [['Wine and balconies', 2022, 9, 48]] } ] },
    { id: '504', name: 'Morocco', cities: [
      { name: 'Marrakesh', key: 'marrakesh', lat: 31.63, lon: -8.0, albums: [['Souks and saffron', 2021, 12, 57]] } ] },
    { id: '840', name: 'United States', cities: [
      { name: 'New York', key: 'manhattan', lat: 40.71, lon: -74.0, albums: [['Seven days in Manhattan', 2017, 10, 102]] },
      { name: 'San Francisco', key: 'san-francisco', lat: 37.77, lon: -122.42, albums: [['Fog over the bridge', 2017, 10, 45]] } ] },
    { id: '604', name: 'Peru', cities: [
      { name: 'Cusco', key: 'cusco', lat: -13.53, lon: -71.97, albums: [['Up to Machu Picchu', 2025, 7, 76]] } ] },
  ];
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const sum = (arr, f) => arr.reduce((s, x) => s + f(x), 0);
  const plural = (n, w) => `${n.toLocaleString('en')} ${n === 1 ? w : w === 'city' ? 'cities' : w + 's'}`;
  const slugOf = (s) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-+$/g, '');
  const seedOf = (str) => { let h = 7; for (const ch of str) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };
  let byId = new Map();

  // Everything lives in one object graph: countries → cities → albums → photos, plus trips.
  // The demo builds it from the lists above; once the owner changes anything, the whole graph is
  // kept in this browser and loaded from there next time.
  function link() {
    byId = new Map(DATA.map((c) => [c.id, c]));
    for (const c of DATA) for (const city of c.cities) { city.country = c; for (const a of city.albums) a.city = city; }
  }
  // demo albums get a day and a time of their own, so a trip keeps its order
  for (const c of DATA) for (const city of c.cities) {
    city.albums = city.albums.map(([title, year, month, photos]) => {
      const s = seedOf(title);
      return { id: `${city.key}/${slugOf(title)}`, title, year, month, day: 1 + s % 26, time: `${String(8 + s % 12).padStart(2, '0')}:${String((s >>> 4) % 60).padStart(2, '0')}`, photos, pics: [] };
    });
  }
  link();

  const cities = () => DATA.flatMap((c) => c.cities).filter((c) => c.albums.length);
  const albums = () => DATA.flatMap((c) => c.cities).flatMap((c) => c.albums);
  const stats = (c) => {
    const al = c.cities.flatMap((x) => x.albums), years = al.map((a) => a.year);
    return { cities: c.cities.length, albums: al.length, photos: sum(al, (a) => a.photos), from: Math.min(...years), to: Math.max(...years) };
  };
  const totals = () => {
    const al = albums();
    return { countries: DATA.filter((c) => c.cities.some((x) => x.albums.length)).length, cities: cities().length, albums: al.length, photos: sum(al, (a) => a.photos), since: Math.min(...al.map((a) => a.year)) };
  };
  const byDate = (a, b) => a.year - b.year || a.month - b.month || a.day - b.day || a.time.localeCompare(b.time) || a.title.localeCompare(b.title);
  // trips in time order, for timelines
  const trips = () => albums().slice().sort(byDate);

  // ---------- photos ----------
  let credits = [], creditOf = new Map(), user = null;
  const urls = new Map();
  const src = (p) => p.url || '/files/' + p.file;
  const picOf = (ref, a) => ref.id
    ? (urls.has(ref.id) ? { file: 'u:' + ref.id, id: ref.id, url: urls.get(ref.id), city: a.city.name, author: user ? user.name : 'you', lic: 'your photo', mine: true, ref } : null)
    : Object.assign({}, creditOf.get(ref.file) || { file: ref.file, author: 'unknown', lic: '' }, { ref });
  const picsOf = (a) => a.pics.map((r) => picOf(r, a)).filter(Boolean);
  const photosOf = (city) => {
    const all = city.albums.flatMap(picsOf), seen = new Set();
    return all.filter((p) => !seen.has(p.file) && seen.add(p.file));
  };

  // ---------- trips: which albums travelled together ----------
  const JOURNEYS = [
    ['First time abroad', ['First trip abroad']], ['American autumn', ['Seven days in Manhattan', 'Fog over the bridge']],
    ['Italy by train', ['Seven hills, one week', 'Duomo at dawn']], ['Iberian spring', ['Gaudí & the sea', 'Tram 28']],
    ['Iceland in June', ['Midnight sun', 'Black sand']], ['Fjords by ferry', ['Fjords by ferry']], ['Lisbon, again', ['Pastéis and tiles']],
    ['A weekend in Madrid', ['Prado afternoons']], ['Marrakesh before New Year', ['Souks and saffron']], ['Paris in April', ['Paris again', 'Louvre at closing time']],
    ['Tbilisi', ['Wine and balconies']], ['Porto in the rain', ['Rain on the Douro']], ['Japan in bloom', ['Neon and quiet', 'Sakura week', 'Bamboo grove']],
    ['Barcelona summer', ['Sagrada Família, finally']], ['New Year in Barcelona', ['New Year on the roof']], ['Chasing the aurora', ['Chasing the aurora']],
    ['New Zealand road trip', ['Harbour city', 'Southern Alps road trip']], ['Seville in March', ['Orange trees in March']], ['Rome in October', ['Trastevere nights']],
    ['Venice in fog', ['Fog and gondolas']], ['Peru', ['Up to Machu Picchu']], ['Paris, sketching', ['Montmartre sketches']], ['Japan in autumn', ['Autumn temples', 'Shibuya crossing']],
  ];
  // [{ id, name, start: 'home' | city key, end: 'home' | city key, albums: [album id] }]
  let TRIPS = [];
  const cityByKey = (k) => DATA.flatMap((c) => c.cities).find((c) => c.key === k);
  const endOf = (v) => (!v || v === 'home' ? { home: true } : { city: cityByKey(v) || null, home: !cityByKey(v) });
  const albumById = (id) => albums().find((a) => a.id === id);
  function journeys() {
    const used = new Set(), out = [];
    for (const t of TRIPS) {
      const list = t.albums.map(albumById).filter(Boolean).sort(byDate);
      list.forEach((a) => used.add(a));
      const start = endOf(t.start), end = endOf(t.end);
      out.push({ id: t.id, name: t.name, start, end, startKey: t.start || 'home', endKey: t.end || 'home', home: end.home, albums: list, from: list[0] || null, to: list[list.length - 1] || null, real: true });
    }
    // an album that belongs to no trip is a trip of its own
    for (const a of albums()) if (!used.has(a)) out.push({ id: 'a:' + a.id, name: `${a.city.name} ${a.year}`, start: { home: true }, end: { home: true }, startKey: 'home', endKey: 'home', home: true, albums: [a], from: a, to: a, real: false });
    // newest first; a trip that has no albums yet stays on top
    return out.sort((x, y) => !x.from ? -1 : !y.from ? 1 : byDate(y.from, x.from));
  }
  const journeyOf = (a) => journeys().find((j) => j.albums.includes(a));

  // ---------- places to pick from: a home base, or a new city ----------
  // [name, country, ISO numeric id, lat, lon]
  const GAZETTEER = [
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
  ].map(([name, country, id, lat, lon]) => ({ name, country, id, lat, lon }));
  // places already on the map come first, then the list above
  function places(q) {
    q = (q || '').trim().toLowerCase();
    const mine = cities().map((c) => ({ name: c.name, country: c.country.name, id: c.country.id, lat: c.lat, lon: c.lon, city: c }));
    const seen = new Set(mine.map((p) => p.name + '|' + p.country));
    const all = mine.concat(GAZETTEER.filter((p) => !seen.has(p.name + '|' + p.country)));
    return q ? all.filter((p) => p.name.toLowerCase().includes(q) || p.country.toLowerCase().includes(q)).slice(0, 8) : all.slice(0, 8);
  }

  // ---------- keeping it: localStorage for the graph, IndexedDB for photo files ----------
  const KEY = 'cloudpix-store-v2';
  function snapshot() {
    return { countries: DATA.map((c) => ({ id: c.id, name: c.name, cities: c.cities.map((x) => ({ name: x.name, key: x.key, lat: x.lat, lon: x.lon, albums: x.albums.map((a) => ({ id: a.id, title: a.title, year: a.year, month: a.month, day: a.day, time: a.time, photos: a.photos, pics: a.pics })) })) })), trips: TRIPS };
  }
  const save = () => { if (!user) return; try { localStorage.setItem(KEY, JSON.stringify(snapshot())); localStorage.setItem('cloudpix-user', JSON.stringify(user)); } catch {} };
  const db = () => new Promise((ok, no) => { const r = indexedDB.open('cloudpix', 1); r.onupgradeneeded = () => r.result.createObjectStore('photos'); r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });
  async function idb(mode, fn) { const d = await db(); return new Promise((ok, no) => { const t = d.transaction('photos', mode); const req = fn(t.objectStore('photos')); t.oncomplete = () => ok(req && req.result); t.onerror = () => no(t.error); }); }

  // Logged out, the app runs the demo: a sample traveller, nothing saved. Logged in, it opens the
  // owner's own archive (seeded from the demo the first time) and keeps every change.
  const DEMO_HOME = { name: 'Kyiv', country: 'Ukraine', lat: 50.45, lon: 30.52 };
  const home = () => (user && user.home) || DEMO_HOME;
  const load = async () => {
    try { credits = await (await fetch('/files/photos.json', { cache: 'no-store' })).json(); } catch { credits = []; }
    creditOf = new Map(credits.map((p) => [p.file, p]));
    try { user = JSON.parse(localStorage.getItem('cloudpix-user') || 'null'); } catch { user = null; }
    let kept = null;
    if (user) try { kept = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch {}
    if (kept) {
      DATA.splice(0, DATA.length, ...kept.countries); link();
      TRIPS = (kept.trips || []).map((t) => ({ id: t.id, name: t.name, start: t.start || 'home', end: t.end || (t.home === false ? (t.albums.length ? '' : 'home') : 'home'), albums: t.albums }));
      try {
        const d = await db();
        const ids = albums().flatMap((a) => a.pics.filter((r) => r.id).map((r) => r.id));
        await Promise.all(ids.map((id) => new Promise((ok) => { const r = d.transaction('photos').objectStore('photos').get(id); r.onsuccess = () => { if (r.result) urls.set(id, URL.createObjectURL(r.result)); ok(); }; r.onerror = () => ok(); })));
      } catch {}
    } else {
      // the demo: each album of a city starts from a different stock photo of that city
      const byCity = new Map();
      for (const p of credits) { const k = slugOf(p.city); if (!byCity.has(k)) byCity.set(k, []); byCity.get(k).push(p); }
      for (const city of DATA.flatMap((c) => c.cities)) {
        const pool = byCity.get(city.key) || credits.slice(0, 2);
        city.albums.forEach((a, k) => { const r = k % Math.max(1, pool.length); a.pics = pool.slice(r).concat(pool.slice(0, r)).map((p) => ({ file: p.file })); });
      }
      TRIPS = JOURNEYS.map(([name, titles], i) => ({ id: 'd' + i, name, start: 'home', end: 'home', albums: titles.map((t) => albums().find((a) => a.title === t)).filter(Boolean).map((a) => a.id) }));
    }
  };

  // ---------- what the owner can change ----------
  function countryFor(id, name) {
    let c = DATA.find((x) => x.id === id) || DATA.find((x) => x.name === name);
    if (!c) { c = { id, name, cities: [] }; DATA.push(c); byId.set(id, c); }
    return c;
  }
  function placeCity(p) {
    if (p.city) return p.city;
    const key = slugOf(p.name);
    const found = DATA.flatMap((c) => c.cities).find((c) => c.key === key);
    if (found) return found;
    const country = countryFor(p.id, p.country);
    const city = { name: p.name, key, lat: p.lat, lon: p.lon, albums: [], country };
    country.cities.push(city);
    return city;
  }
  function tripOf(a) { return TRIPS.find((t) => t.albums.includes(a.id)); }
  function setTrip(a, tripId) {
    for (const t of TRIPS) t.albums = t.albums.filter((id) => id !== a.id);
    const t = TRIPS.find((x) => x.id === tripId); if (t) t.albums.push(a.id);
  }
  const parseDate = (d) => { const [year, month, day] = d.split('-').map(Number); return { year, month, day }; };
  function addAlbum({ title, date, time, place, trip }) {
    const city = placeCity(place);
    const a = Object.assign({ id: 'u' + Date.now().toString(36), title, time: time || '12:00', photos: 0, pics: [], city }, parseDate(date));
    city.albums.push(a);
    if (trip) setTrip(a, trip);
    save();
    return a;
  }
  function updateAlbum(a, { title, date, time, place, trip }) {
    Object.assign(a, { title, time: time || a.time }, parseDate(date));
    const city = placeCity(place);
    if (city !== a.city) { a.city.albums.splice(a.city.albums.indexOf(a), 1); city.albums.push(a); a.city = city; }
    if (trip !== undefined) setTrip(a, trip);
    save();
  }
  async function deleteAlbum(a) {
    a.city.albums.splice(a.city.albums.indexOf(a), 1);
    for (const t of TRIPS) t.albums = t.albums.filter((id) => id !== a.id);
    for (const r of a.pics) if (r.id) { try { await idb('readwrite', (st) => st.delete(r.id)); } catch {} }
    save();
  }
  // photos are made smaller before they are kept: the long side at most 1600 px
  async function shrink(file) {
    const bmp = await createImageBitmap(file);
    const k = Math.min(1, 1600 / Math.max(bmp.width, bmp.height)), c = document.createElement('canvas');
    c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    return new Promise((ok) => c.toBlob(ok, 'image/jpeg', .86));
  }
  async function addPhotos(a, files) {
    for (const f of files) {
      if (!f.type.startsWith('image/')) continue;
      const blob = await shrink(f), id = Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
      await idb('readwrite', (st) => st.put(blob, id));
      urls.set(id, URL.createObjectURL(blob));
      a.pics.push({ id, name: f.name });
      a.photos += 1;
    }
    save();
  }
  async function removePhoto(a, ref) {
    const k = a.pics.indexOf(ref); if (k < 0) return;
    a.pics.splice(k, 1); a.photos = Math.max(a.pics.length, a.photos - 1);
    if (ref.id) { try { await idb('readwrite', (st) => st.delete(ref.id)); } catch {} }
    save();
  }
  function addJourney(name, list, start = 'home', end = 'home') { const t = { id: 'u' + Date.now().toString(36), name, start, end, albums: [] }; TRIPS.push(t); list.forEach((a) => setTrip(a, t.id)); save(); return t.id; }
  function updateJourney(id, { name, start, end, list }) {
    const t = TRIPS.find((x) => x.id === id); if (!t) return;
    t.name = name; t.start = start; t.end = end;
    t.albums = [];
    for (const a of list) setTrip(a, id);
    save();
  }
  function deleteJourney(id) { TRIPS = TRIPS.filter((t) => t.id !== id); save(); }
  function login(name, email, home) { user = { name, email, home }; try { localStorage.setItem('cloudpix-user', JSON.stringify(user)); } catch {} }
  function logout() { user = null; try { localStorage.setItem('cloudpix-user', 'null'); } catch {} }
  function updateAccount(fields) { if (!user) return; Object.assign(user, fields); save(); }
  // a photo's own line: the owner can write it, otherwise the demo line stays
  function setCaption(a, ref, text) { ref.caption = text.trim() || undefined; save(); }
  function setHome(home) { if (user) { user.home = home; save(); } }
  function resetDemo() { try { localStorage.removeItem(KEY); indexedDB.deleteDatabase('cloudpix'); } catch {} }

  return { DATA, MONTHS, sum, plural, get byId() { return byId; }, cities, albums, stats, totals, trips, load, photosOf, src, credits: () => credits,
    journeys, journeyOf, tripOf, places, picsOf, byDate, user: () => user, home, login, logout, setHome, updateAccount, setCaption,
    addAlbum, updateAlbum, deleteAlbum, addPhotos, removePhoto, addJourney, updateJourney, deleteJourney, resetDemo };
})();
