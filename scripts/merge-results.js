// Merges the per-shard results.jsonl files produced by scrape-dealers.js into one
// deduplicated CSV: name, address, city, state, zip.
//
// Usage: node merge-results.js <outCsv> <inputJsonlFile...>

const fs = require('fs');

const [, , outCsv, ...inputFiles] = process.argv;
if (!outCsv || inputFiles.length === 0) {
  console.error('Usage: node merge-results.js <outCsv> <inputJsonlFile...>');
  process.exit(1);
}

function parseCityStateZip(cityStateZip) {
  // "Milwaukee, WI 53208" -> { city: "Milwaukee", state: "WI", zip: "53208" }
  const m = cityStateZip.match(/^(.*),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?$/);
  if (m) {
    return { city: m[1].trim(), state: m[2], zip: (m[3] || '').trim() };
  }
  return { city: cityStateZip, state: '', zip: '' };
}

const byStoreId = new Map();
const byNameAddr = new Map(); // fallback dedup key for rows missing a storeId

let totalRows = 0;
for (const file of inputFiles) {
  if (!fs.existsSync(file)) continue;
  const lines = fs.readFileSync(file, 'utf8').split('\n').filter(Boolean);
  for (const line of lines) {
    totalRows += 1;
    let row;
    try {
      row = JSON.parse(line);
    } catch {
      continue;
    }
    if (!row.name) continue;
    const { city, state, zip } = parseCityStateZip(row.cityStateZip || '');
    const record = {
      name: row.name,
      street: row.street || '',
      city,
      state,
      zip,
    };
    const key = row.storeId || `${record.name}|${record.street}|${city}|${state}`;
    const map = row.storeId ? byStoreId : byNameAddr;
    if (!map.has(key)) map.set(key, record);
  }
}

const all = [...byStoreId.values(), ...byNameAddr.values()];
// final de-dupe across both maps by name+street+city+state, in case the same dealer
// was seen once with a storeId and once without (shouldn't normally happen, but cheap to guard)
const seen = new Set();
const deduped = [];
for (const r of all) {
  const key = `${r.name}|${r.street}|${r.city}|${r.state}`.toLowerCase();
  if (seen.has(key)) continue;
  seen.add(key);
  deduped.push(r);
}

deduped.sort((a, b) => (a.state + a.city + a.name).localeCompare(b.state + b.city + b.name));

function csvEscape(v) {
  if (v == null) return '';
  const s = String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

const header = ['name', 'street', 'city', 'state', 'zip'];
const lines = [header.join(',')];
for (const r of deduped) {
  lines.push(header.map((h) => csvEscape(r[h])).join(','));
}
fs.writeFileSync(outCsv, lines.join('\n') + '\n');

console.log(`Read ${totalRows} raw result rows from ${inputFiles.length} file(s)`);
console.log(`Wrote ${deduped.length} deduplicated dealers to ${outCsv}`);

const byState = {};
for (const r of deduped) {
  byState[r.state || '??'] = (byState[r.state || '??'] || 0) + 1;
}
console.log('By state:', JSON.stringify(byState, null, 2));
