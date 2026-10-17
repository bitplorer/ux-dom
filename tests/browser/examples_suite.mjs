/**
 * Headless Chromium against the live example apps (tests/06_browser/
 * test_examples_browser.py boots them and passes their URLs).
 *
 *   SHOWCASE_URL=... CHANNEL_URL=... WS_URL=... SEARCH_URL=... \
 *     node tests/browser/examples_suite.mjs
 *
 * Prints one JSON report on stdout; exit code 0 only when every check passed.
 * Replaces the manual scripts/ui_dom_live_browser.mjs and
 * scripts/enterprise_live_chaos.mjs, which targeted the old showcase.
 */
import { chromium } from "playwright";

const url = (name) => (process.env[name] || "").replace(/\/$/, "");
const BASES = {
  showcase: url("SHOWCASE_URL"),
  channel: url("CHANNEL_URL"),
  ws: url("WS_URL"),
  search: url("SEARCH_URL"),
};
const fails = [];
const phases = {};
const check = (ok, msg) => {
  if (!ok) fails.push(msg);
};

async function openPage(browser, phase) {
  const page = await browser.newPage();
  const log = { console: [], pageErrors: [] };
  page.on("console", (m) => {
    if (m.type() === "error") log.console.push(m.text());
  });
  page.on("pageerror", (e) => log.pageErrors.push(String(e?.message || e)));
  await page.addInitScript(() => {
    window.__csp = [];
    document.addEventListener("securitypolicyviolation", (e) =>
      window.__csp.push(`${e.violatedDirective} ${e.blockedURI}`),
    );
  });
  phases[phase] = { log };
  return page;
}

async function finish(page, phase) {
  const csp = await page.evaluate(() => window.__csp);
  phases[phase].csp = csp;
  check(csp.length === 0, `${phase}: CSP violations ${JSON.stringify(csp)}`);
  const { pageErrors } = phases[phase].log;
  check(pageErrors.length === 0, `${phase}: page errors ${JSON.stringify(pageErrors)}`);
  await page.close();
}

const text = (page, sel) => page.locator(sel).first().innerText();

async function showcase(browser) {
  const base = BASES.showcase;
  const page = await openPage(browser, "showcase");

  await page.goto(`${base}/cart`, { waitUntil: "networkidle" });
  await page.evaluate(() => (window.__sameDocument = true));
  const before = Number(await page.locator("#cart").getAttribute("data-count"));
  await page.locator("#cart button").click();
  await page.waitForFunction(
    (n) => Number(document.querySelector("#cart")?.dataset.count) === n + 1,
    before,
    { timeout: 10000 },
  );
  const sameDoc = await page.evaluate(() => window.__sameDocument === true);
  phases.showcase.cart = { before, sameDoc };
  check(sameDoc, "showcase: cart click reloaded the page (htmx not active)");

  await page.goto(`${base}/guestbook`, { waitUntil: "networkidle" });
  await page.fill('input[name="name"]', '<img src=x onerror="window.PWNED=1">');
  await page.fill('input[name="website"]', "https://example.com");
  await page.fill('textarea[name="message"]', "**bold** <script>window.PWNED=2</script>");
  await page.locator('form.form button[type="submit"]').click();
  await page.waitForFunction(
    () => document.querySelector("#entries strong")?.textContent.includes("<img"),
    null,
    { timeout: 10000 },
  );
  const gb = await page.evaluate(() => ({
    pwned: window.PWNED ?? null,
    firstName: document.querySelector("#entries strong")?.textContent,
    bold: !!document.querySelector("#entries p strong"),
    imgs: document.querySelectorAll("#entries img").length,
  }));
  phases.showcase.guestbook = gb;
  check(gb.pwned === null, "showcase: guestbook script executed");
  check(gb.imgs === 0, "showcase: guestbook rendered an <img> from user input");
  check(gb.bold, "showcase: guestbook Markdown not rendered");

  await page.goto(`${base}/sse`, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(
    () => /tick #\d+/.test(document.querySelector("#tick")?.textContent || ""),
    null,
    { timeout: 15000 },
  );
  phases.showcase.sse = await text(page, "#tick");

  await finish(page, "showcase");
}

async function channel(browser) {
  const page = await openPage(browser, "channel");
  await page.goto(BASES.channel + "/", { waitUntil: "networkidle" });
  const count = () =>
    page.evaluate(() => Number(document.querySelector("[data-count]")?.dataset.count));
  const start = await count();
  await page.getByRole("button", { name: "+5" }).click();
  await page.waitForFunction(
    (n) => Number(document.querySelector("[data-count]")?.dataset.count) === n + 5,
    start,
    { timeout: 10000 },
  );
  // Forge the arguments of "+1": the signed cap no longer matches.
  await page.evaluate(() => {
    const b = [...document.querySelectorAll("button")].find((x) => x.textContent.trim() === "+1");
    b.setAttribute("data-channel-args", '{"step":1000}');
  });
  await page.getByRole("button", { name: "+1" }).click();
  await page.waitForTimeout(1000);
  const afterForged = await count();
  phases.channel.counts = { start, afterForged };
  check(afterForged === start + 5, `channel: forged args changed the count (${afterForged})`);
  // The refused action logs an error in the console (401); not a failure here.
  await finish(page, "channel");
}

async function ws(browser) {
  const page = await openPage(browser, "ws");
  await page.goto(BASES.ws + "/", { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelector("#n")?.textContent === "0", null, {
    timeout: 10000,
  });
  await page.locator("#bump").click();
  await page.locator("#bump").click();
  await page.waitForFunction(() => document.querySelector("#n")?.textContent === "2", null, {
    timeout: 10000,
  });
  phases.ws.n = await text(page, "#n");
  await finish(page, "ws");
}

async function search(browser) {
  const page = await openPage(browser, "search");
  await page.goto(BASES.search + "/", { waitUntil: "networkidle" });
  await page.evaluate(() => (window.__sameDocument = true));
  await page.fill("#q", "kiwi");
  await page.locator("#sf button").click();
  await page.waitForSelector("#r0", { timeout: 10000 });
  const r = await page.evaluate(() => ({
    first: document.querySelector("#r0")?.textContent,
    hits: document.querySelectorAll(".hit").length,
    sameDoc: window.__sameDocument === true,
  }));
  phases.search.result = r;
  check(r.first === "kiwi-0" && r.hits === 30, `search: unexpected results ${JSON.stringify(r)}`);
  check(r.sameDoc, "search: submit reloaded the page (htmx not active)");
  await finish(page, "search");
}

const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
try {
  for (const [name, fn] of Object.entries({ showcase, channel, ws, search })) {
    if (!BASES[name]) {
      fails.push(`${name}: URL not set`);
      continue;
    }
    try {
      await fn(browser);
    } catch (err) {
      fails.push(`${name}: ${err?.message || err}`);
    }
  }
} finally {
  await browser.close();
}
const report = { ok: fails.length === 0, fails, phases };
console.log(JSON.stringify(report));
process.exit(report.ok ? 0 : 1);
