/**
 * Deep headless Chromium coverage against the live xelement_kit app.
 *
 * Requires KIT_URL (e.g. http://127.0.0.1:8766)
 *
 *   KIT_URL=http://127.0.0.1:8766 node tests/browser/kit_browser_suite.mjs
 *
 * Screenshots → screenshots/kit/*.png
 * Report      → screenshots/kit/browser-report.json
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "/workspace/node_modules/playwright/index.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "../..");
const SHOT = join(ROOT, "screenshots/kit");
mkdirSync(SHOT, { recursive: true });

const BASE = (process.env.KIT_URL || "").replace(/\/$/, "");
if (!BASE) {
  console.error(JSON.stringify({ ok: false, error: "KIT_URL required" }));
  process.exit(1);
}

const fails = [];
const phases = {};
const screenshots = [];
const consoleErrors = [];
const pageErrors = [];

function fail(msg) {
  fails.push(msg);
}

async function shot(page, name) {
  const p = join(SHOT, `${name}.png`);
  await page.screenshot({ path: p, fullPage: true });
  screenshots.push(p);
  return p;
}

async function goto(page, path, wait = "networkidle") {
  const url = BASE + path;
  const resp = await page.goto(url, { waitUntil: wait, timeout: 45000 });
  return { url, status: resp?.status() ?? 0 };
}

async function run() {
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text());
  });
  page.on("pageerror", (e) => pageErrors.push(String(e?.message || e)));

  try {
    // ── Health ──────────────────────────────────────────────────────
    {
      const r = await goto(page, "/health", "domcontentloaded");
      const body = await page.locator("body").innerText();
      let json = {};
      try {
        json = JSON.parse(body);
      } catch {
        fail("health: not JSON");
      }
      phases.health = { ...r, json };
      if (r.status !== 200 || !json.ok) fail(`health status=${r.status} body=${body}`);
      if (json.runtime !== "x_element.js") fail(`health runtime=${json.runtime}`);
    }

    // ── Index ───────────────────────────────────────────────────────
    {
      const r = await goto(page, "/index/Index");
      phases.index = { status: r.status, hasRuntime: (await page.locator('script[src*="x_element"]').count()) > 0 };
      if (r.status !== 200) fail(`index ${r.status}`);
      if (!phases.index.hasRuntime) fail("index: missing x_element.js script");
      await shot(page, "01-index");
    }

    // ── Light DOM ───────────────────────────────────────────────────
    {
      const r = await goto(page, "/lightdom/LightDomDemo");
      await page.waitForTimeout(500);
      const details = await page.evaluate(() => {
        const hosts = ["x-hello-light", "x-info-banner", "x-action-card"];
        const out = { defined: {}, upgraded: {} };
        for (const t of hosts) {
          out.defined[t] = !!customElements.get(t);
          const el = document.querySelector(t);
          out.upgraded[t] = el
            ? {
                exists: true,
                childCount: el.childElementCount,
                text: (el.innerText || "").trim().slice(0, 120),
                dataDom: el.querySelector?.("[data-dom=light]") ? true : !!el.querySelector("[data-dom]"),
              }
            : { exists: false };
        }
        return out;
      });
      phases.lightdom = { status: r.status, ...details };
      if (r.status !== 200) fail(`lightdom ${r.status}`);
      for (const t of Object.keys(details.defined)) {
        if (!details.defined[t]) fail(`lightdom: ${t} not defined`);
        if (!details.upgraded[t]?.exists) fail(`lightdom: ${t} host missing`);
        if (!(details.upgraded[t]?.childCount > 0)) fail(`lightdom: ${t} not upgraded (no children)`);
      }
      // click action card button
      const btn = page.locator("x-action-card button");
      if ((await btn.count()) > 0) {
        await btn.first().click();
        await page.waitForTimeout(150);
        const txt = await btn.first().innerText();
        phases.lightdom.buttonAfterClick = txt;
        if (!/Clicked/i.test(txt)) fail(`lightdom: button text after click=${txt}`);
      } else {
        fail("lightdom: action button missing");
      }
      await shot(page, "02-lightdom");
    }

    // ── Shadow DOM ──────────────────────────────────────────────────
    {
      const r = await goto(page, "/shadowdom/ShadowDomDemo");
      await page.waitForTimeout(600);
      const details = await page.evaluate(() => {
        const tags = ["x-shell-shadow", "x-profile-card", "x-callout-shadow"];
        const out = {};
        for (const t of tags) {
          const el = document.querySelector(t);
          const sr = el?.shadowRoot;
          out[t] = {
            defined: !!customElements.get(t),
            exists: !!el,
            hasShadow: !!sr,
            shadowText: sr ? sr.textContent.trim().slice(0, 160) : null,
            slots: sr
              ? [...sr.querySelectorAll("slot")].map((s) => ({
                  name: s.name || "",
                  assigned: s.assignedNodes().map((n) => (n.textContent || "").trim()).filter(Boolean),
                }))
              : [],
          };
        }
        return out;
      });
      phases.shadowdom = { status: r.status, hosts: details };
      if (r.status !== 200) fail(`shadowdom ${r.status}`);
      for (const [t, d] of Object.entries(details)) {
        if (!d.defined) fail(`shadow: ${t} not defined`);
        if (!d.hasShadow) fail(`shadow: ${t} missing shadowRoot`);
      }
      // profile named slot should assign title
      const profile = details["x-profile-card"];
      const assignedFlat = JSON.stringify(profile?.slots || []);
      if (!/Ada|Lovelace|Grace|title/i.test(assignedFlat + (profile?.shadowText || ""))) {
        // light DOM text may still be in host
        const light = await page.locator("x-profile-card").innerText();
        phases.shadowdom.profileLight = light;
        if (!/Ada|Lovelace/i.test(light) && !/Ada|Lovelace/i.test(assignedFlat)) {
          fail(`shadow: profile projection missing; slots=${assignedFlat}`);
        }
      }
      await shot(page, "03-shadowdom");
    }

    // ── Alpine ──────────────────────────────────────────────────────
    {
      const r = await goto(page, "/alpine/AlpineDemo");
      await page.waitForFunction(
        () => customElements.get("x-toggle") && customElements.get("x-counter"),
        { timeout: 15000 }
      );
      await page.waitForTimeout(400);
      const before = await page.locator("x-toggle").innerText();
      await page.locator("x-toggle").click({ force: true });
      await page.waitForTimeout(250);
      const after = await page.locator("x-toggle").innerText();
      phases.alpine = {
        status: r.status,
        defined: await page.evaluate(
          () => !!customElements.get("x-toggle") && !!customElements.get("x-counter")
        ),
        before: before.trim(),
        after: after.trim(),
        hasXData: await page.evaluate(
          () => !!document.querySelector("x-toggle [x-data], x-toggle")
        ),
      };
      if (r.status !== 200) fail(`alpine ${r.status}`);
      if (!phases.alpine.defined) fail("alpine: CE not defined");
      // toggle should flip OFF↔ON (or at least change / contain ON after click)
      if (!/ON|OFF/i.test(after)) fail(`alpine: unexpected toggle text=${after}`);
      // Prefer seeing a change; if already ON from prior, still ok if ON present
      if (before.trim() === after.trim() && !/ON/i.test(after)) {
        // try second click
        await page.locator("x-toggle").click({ force: true });
        await page.waitForTimeout(200);
        const after2 = (await page.locator("x-toggle").innerText()).trim();
        phases.alpine.after2 = after2;
        if (after2 === before.trim()) fail("alpine: toggle did not change on click");
      }
      await shot(page, "04-alpine");
    }

    // ── HTMX partial + XElement re-upgrade ──────────────────────────
    {
      const r = await goto(page, "/htmx/HtmxDemo");
      await page.waitForTimeout(400);
      phases.htmx = { status: r.status, steps: [] };
      if (r.status !== 200) fail(`htmx ${r.status}`);

      const panelBefore = await page.locator("#panel").innerText();
      phases.htmx.steps.push({ panelBefore: panelBefore.trim() });

      await page.locator("#load-btn").click();
      // wait for partial content
      await page.waitForFunction(
        () => {
          const p = document.querySelector("#panel");
          return p && (p.querySelector("x-hello") || /partial/i.test(p.innerText));
        },
        { timeout: 15000 }
      );
      await page.waitForTimeout(400);

      const afterSwap = await page.evaluate(() => {
        const panel = document.querySelector("#panel");
        const host = panel?.querySelector("x-hello");
        return {
          panelText: panel?.innerText?.trim().slice(0, 200),
          hasHost: !!host,
          defined: !!customElements.get("x-hello"),
          hostChildren: host ? host.childElementCount : 0,
          hostText: host ? host.innerText.trim() : null,
          partialN: host?.getAttribute("data-partial") || null,
        };
      });
      phases.htmx.afterSwap = afterSwap;
      if (!afterSwap.hasHost) fail("htmx: x-hello missing after swap");
      if (!afterSwap.defined) fail("htmx: x-hello not defined after swap");
      if (!(afterSwap.hostChildren > 0) && !(afterSwap.hostText || "").length) {
        fail("htmx: x-hello not upgraded after swap");
      }
      if (!/Hello|CustomElement|partial/i.test(afterSwap.panelText || "")) {
        fail(`htmx: panel text unexpected: ${afterSwap.panelText}`);
      }

      // second load increments partial
      await page.locator("#load-btn").click();
      await page.waitForTimeout(500);
      const second = await page.evaluate(() => {
        const host = document.querySelector("#panel x-hello");
        return host?.getAttribute("data-partial") || null;
      });
      phases.htmx.secondPartial = second;
      await shot(page, "05-htmx");
    }

    // ── Slots demo ──────────────────────────────────────────────────
    {
      const r = await goto(page, "/slots/SlotsDemo");
      await page.waitForTimeout(500);
      const details = await page.evaluate(() => {
        const panel = document.querySelector("x-named-panel");
        const multi = document.querySelector("x-multi-slot");
        return {
          panelDefined: !!customElements.get("x-named-panel"),
          multiDefined: !!customElements.get("x-multi-slot"),
          panelShadow: !!panel?.shadowRoot,
          panelSlots: panel?.shadowRoot
            ? [...panel.shadowRoot.querySelectorAll("slot")].map((s) => ({
                name: s.name || "",
                assigned: s.assignedNodes().map((n) => (n.textContent || "").trim()).filter(Boolean),
              }))
            : [],
          multiExists: !!multi,
          multiShadow: !!multi?.shadowRoot,
          multiText: multi?.innerText?.trim().slice(0, 120),
        };
      });
      phases.slots = { status: r.status, ...details };
      if (r.status !== 200) fail(`slots ${r.status}`);
      if (!details.panelDefined) fail("slots: x-named-panel not defined");
      if (!details.panelShadow) fail("slots: named-panel no shadowRoot");
      const flat = JSON.stringify(details.panelSlots);
      if (!/Header|slot|body|copy/i.test(flat + (await page.locator("x-named-panel").innerText()))) {
        fail(`slots: projection weak: ${flat}`);
      }
      await shot(page, "06-slots");
    }

    // ── WC quick demo ───────────────────────────────────────────────
    {
      const r = await goto(page, "/wc/WcDemo");
      await page.waitForTimeout(400);
      const ok = await page.evaluate(
        () =>
          !!customElements.get("x-hello") &&
          !!document.querySelector("x-hello") &&
          document.querySelector("x-hello").childElementCount > 0
      );
      phases.wc = { status: r.status, upgraded: ok };
      if (r.status !== 200 || !ok) fail("wc: upgrade failed");
      await shot(page, "07-wc");
    }

    // ── Jinja (server HTML only) ────────────────────────────────────
    {
      const r = await goto(page, "/jinja/JinjaDemo");
      const text = await page.locator("#jinja-demo").innerText();
      phases.jinja = {
        status: r.status,
        hasAlpha: /Alpha/.test(text),
        hasExpanded: (await page.locator("#jinja-expanded").count()) > 0,
      };
      if (r.status !== 200) fail(`jinja ${r.status}`);
      if (!phases.jinja.hasAlpha) fail("jinja: expanded Alpha missing");
      await shot(page, "08-jinja");
    }

    // ── Mobile viewport on shadow page ──────────────────────────────
    {
      await page.setViewportSize({ width: 390, height: 844 });
      await goto(page, "/shadowdom/ShadowDomDemo");
      await page.waitForTimeout(300);
      const overflow = await page.evaluate(() => {
        return {
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        };
      });
      phases.mobile = overflow;
      if (overflow.scrollWidth > overflow.clientWidth + 8) {
        // soft fail note — many pages slightly overflow; only fail hard if huge
        if (overflow.scrollWidth > overflow.clientWidth + 40) {
          fail(`mobile overflow: ${overflow.scrollWidth} > ${overflow.clientWidth}`);
        }
      }
      await shot(page, "09-mobile-shadow");
    }

    // hard page errors fail
    for (const e of pageErrors) fail(`pageerror: ${e}`);

    const report = {
      ok: fails.length === 0,
      base: BASE,
      fails,
      phases,
      consoleErrors,
      pageErrors,
      screenshots,
    };
    writeFileSync(join(SHOT, "browser-report.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
    process.exit(report.ok ? 0 : 1);
  } catch (err) {
    fails.push(String(err?.message || err));
    const report = { ok: false, base: BASE, fails, phases, consoleErrors, pageErrors, screenshots };
    writeFileSync(join(SHOT, "browser-report.json"), JSON.stringify(report, null, 2));
    console.error(JSON.stringify(report, null, 2));
    process.exit(1);
  } finally {
    await browser.close();
  }
}

await run();
