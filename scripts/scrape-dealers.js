// Scrapes Milwaukee Tool's "Authorized Distributors" locator (https://www.milwaukeetool.com/buy-now)
// by driving the real PriceSpider locator widget embedded on that page: typing each zip/location
// from a sweep list into its search box and reading back the rendered local-dealer results.
//
// Env vars:
//   ZIP_FILE      path to CSV with header `zip,lat,lon` (only `zip` column is used to search)
//   SHARD_INDEX   0-based index of this shard (default 0)
//   SHARD_COUNT   total number of shards (default 1)
//   OUT_FILE      path to write newline-delimited JSON results (default results.jsonl)
//   ERR_FILE      path to write newline-delimited JSON error log (default errors.jsonl)
//   RELOAD_EVERY  reload the page after this many searches, to shed any accumulated widget
//                 state (default 50)

const fs = require('fs');
const { chromium } = require('playwright');

const ZIP_FILE = process.env.ZIP_FILE || 'sweep_zips.csv';
const SHARD_INDEX = parseInt(process.env.SHARD_INDEX || '0', 10);
const SHARD_COUNT = parseInt(process.env.SHARD_COUNT || '1', 10);
const OUT_FILE = process.env.OUT_FILE || 'results.jsonl';
const ERR_FILE = process.env.ERR_FILE || 'errors.jsonl';
const RELOAD_EVERY = parseInt(process.env.RELOAD_EVERY || '50', 10);

const BUY_NOW_URL = 'https://www.milwaukeetool.com/buy-now';
const SEARCH_INPUT_SELECTOR = 'input.ps-map-location-textbox';
const RESULT_SELECTOR = '.ps-local-left .ps-map-pushpin-select[data-store]';

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function loadZips() {
  const text = fs.readFileSync(ZIP_FILE, 'utf8').trim().split('\n');
  const header = text[0].split(',');
  const zipIdx = header.indexOf('zip');
  const all = text.slice(1).map((line) => line.split(',')[zipIdx].trim());
  return all.filter((_, i) => i % SHARD_COUNT === SHARD_INDEX);
}

async function extractResults(page, searchZip) {
  return page.$$eval(
    RESULT_SELECTOR,
    (els, searchZip) =>
      els.map((el) => {
        const storeId = el.getAttribute('data-store') || '';
        const logoEl = el.querySelector('.ps-local-seller-logo');
        let name = '';
        if (logoEl) {
          const clone = logoEl.cloneNode(true);
          clone.querySelectorAll('.ps-seller-error-name').forEach((n) => n.remove());
          name = clone.textContent.trim().replace(/\s+/g, ' ');
        }
        const addrEl = el.querySelector('.ps-address');
        const spans = addrEl ? Array.from(addrEl.querySelectorAll('span')).map((s) => s.textContent.trim()) : [];
        const street = spans[0] || '';
        const cityStateZip = spans[1] || '';
        const distanceEl = el.querySelector('.ps-distance');
        const distance = distanceEl ? distanceEl.textContent.trim() : '';
        return { storeId, name, street, cityStateZip, distance, searchZip };
      }),
    searchZip
  );
}

async function main() {
  const zips = loadZips();
  console.log(`Shard ${SHARD_INDEX}/${SHARD_COUNT}: ${zips.length} zips to search`);

  const outStream = fs.createWriteStream(OUT_FILE, { flags: 'a' });
  const errStream = fs.createWriteStream(ERR_FILE, { flags: 'a' });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    viewport: { width: 1366, height: 900 },
  });
  let page = await context.newPage();

  async function freshLoad() {
    await page.goto(BUY_NOW_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForSelector(SEARCH_INPUT_SELECTOR, { timeout: 30000 });
    await page.waitForTimeout(1500);
  }

  await freshLoad();

  let done = 0;
  let totalFound = 0;
  for (const zip of zips) {
    try {
      if (done > 0 && done % RELOAD_EVERY === 0) {
        await freshLoad();
      }
      const input = page.locator(SEARCH_INPUT_SELECTOR).first();
      await input.click({ timeout: 15000 });
      await input.fill(zip, { timeout: 15000 });
      await page.keyboard.press('Enter');
      await page.waitForTimeout(4500);

      const results = await extractResults(page, zip);
      for (const r of results) {
        outStream.write(JSON.stringify(r) + '\n');
      }
      totalFound += results.length;
    } catch (e) {
      errStream.write(JSON.stringify({ zip, error: e.message }) + '\n');
      // try to recover with a fresh page load before continuing
      try {
        await freshLoad();
      } catch (e2) {
        errStream.write(JSON.stringify({ zip, error: 'reload failed: ' + e2.message }) + '\n');
      }
    }
    done += 1;
    if (done % 25 === 0) {
      console.log(`  ${done}/${zips.length} searched, ${totalFound} results so far`);
    }
    await sleep(400 + Math.random() * 800);
  }

  console.log(`Shard ${SHARD_INDEX} done: ${done} zips searched, ${totalFound} result rows`);
  outStream.end();
  errStream.end();
  await browser.close();
}

main().catch((e) => {
  console.error('FATAL', e);
  process.exit(1);
});
