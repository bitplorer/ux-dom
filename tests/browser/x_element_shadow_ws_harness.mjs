/**
 * Headless Chromium: x_element.js shadow attribute + WebSocket behavior.
 *
 * No network: the page and x_element.js are served by page.route and every
 * WebSocket is answered by page.routeWebSocket. Prints one JSON report.
 *
 *   node tests/browser/x_element_shadow_ws_harness.mjs
 */
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const runtimeJs = readFileSync(join(ROOT, "src/ux_dom/scripts/x_element.js"), "utf8");
const BASE = "http://uxdom.test";

const PAGE = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>x_element shadow/ws</title></head>
<body>
  <template x-tagname="sr-open" shadowroot="true"><p>open shadow</p><slot></slot></template>
  <template x-tagname="sr-closed" shadowroot="closed"><p>closed shadow</p></template>
  <template x-tagname="sd-only" shadowdom="open"><p>synonym</p></template>
  <template x-tagname="light"><p>light body</p></template>
  <template x-tagname="live"><p>live</p></template>
  <template x-tagname="sender"><p>sender</p></template>

  <x-sr-open id="sr-open"><span>projected</span></x-sr-open>
  <x-sr-closed id="sr-closed"></x-sr-closed>
  <x-sd-only id="sd-only"></x-sd-only>
  <x-light id="light"></x-light>
  <x-live id="live" ws="/ws-live" count="0" data-count="0" aria-label="old" value="old"
    href="/old" src="/old" action="/old" formaction="/old" xlink:href="/old"
    hx-get="/old" srcset="/old.png" srcdoc="old" style="color: red" onclick="void 0"></x-live>
  <x-sender id="sender" ws="/ws-send" ws_send='{"hello":1}'></x-sender>
  <script src="/x_element.js"></script>
</body></html>`;

// Benign declared attributes are applied. URL, srcdoc, style and on* ones,
// declared or not, are refused with a console warning.
const APPLIED = { count: "5", "data-count": "5", "aria-label": "new", value: "new" };
const REFUSED = {
  href: "javascript:alert(1)",
  src: "javascript:alert(1)",
  action: "javascript:alert(1)",
  formaction: "javascript:alert(1)",
  "xlink:href": "javascript:alert(1)",
  "XLINK:HREF": "javascript:alert(1)",
  "hx-get": "https://evil.example/",
  srcset: "javascript:alert(1)",
  srcdoc: "<script>alert(1)</script>",
  style: "background: url(javascript:alert(1))",
  onclick: "alert(1)",
  ONCLICK: "alert(1)",
  "data-new": "added",
};
const LIVE_MESSAGES = Object.entries({ ...APPLIED, ...REFUSED }).map(([attr, newVal]) => ({
  id: "live",
  attr,
  newVal,
}));

const sockets = {}; // path -> { opened, received: [], closed }

const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const report = { pageErrors: [], warnings: [], liveMessages: LIVE_MESSAGES };
try {
  const page = await browser.newPage();
  page.on("pageerror", (e) => report.pageErrors.push(String(e?.message || e)));
  page.on("console", (m) => m.type() === "warning" && report.warnings.push(m.text()));
  await page.route(`${BASE}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/x_element.js") {
      return route.fulfill({ contentType: "application/javascript", body: runtimeJs });
    }
    return route.fulfill({ contentType: "text/html", body: PAGE });
  });
  await page.routeWebSocket(/\/ws-/, (ws) => {
    const path = new URL(ws.url()).pathname;
    const rec = (sockets[path] = sockets[path] || { opened: 0, received: [], closed: false });
    rec.opened += 1;
    ws.onMessage((m) => rec.received.push(String(m)));
    ws.onClose(() => (rec.closed = true));
    if (path === "/ws-live") {
      setTimeout(() => {
        for (const msg of LIVE_MESSAGES) ws.send(JSON.stringify(msg));
      }, 200);
    }
  });

  await page.goto(`${BASE}/`);
  await page.waitForFunction(() => customElements.get("x-sender"));
  await page.waitForTimeout(800);

  report.dom = await page.evaluate(() => {
    const info = (id) => {
      const el = document.getElementById(id);
      const root = el.shadowRoot;
      return {
        openShadowRoot: !!root,
        runtimeShadow: !!el.shadow,
        shadowText: root ? root.textContent.trim() : null,
        lightText: el.textContent.trim(),
      };
    };
    return {
      srOpen: info("sr-open"),
      srClosed: info("sr-closed"),
      sdOnly: info("sd-only"),
      light: info("light"),
      live: Object.fromEntries(
        document.getElementById("live").getAttributeNames().map((n) => [
          n,
          document.getElementById("live").getAttribute(n),
        ])
      ),
    };
  });
  await page.evaluate(() => document.getElementById("live").remove());
  await page.waitForTimeout(300);
  report.sockets = sockets;
} catch (err) {
  report.error = String(err?.message || err);
} finally {
  await browser.close();
}
console.log(JSON.stringify(report));
process.exit(report.error ? 1 : 0);
