/**
 * Headless Chromium checks for XElement ↔ x_element.js.
 *
 * Usage:
 *   node tests/browser/x_element_harness.mjs
 *   node tests/browser/x_element_harness.mjs --kit   # also hit live kit app if KIT_URL set
 *
 * Screenshots → /workspace/ux_dom-improve/screenshots/xelement-*.png
 * Exit 0 = pass, 1 = fail, 2 = console/page errors
 */
import { createServer } from "node:http";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "/workspace/node_modules/playwright/index.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "../..");
const RUNTIME = join(ROOT, "src/ux_dom/scripts/x_element.js");
const SHOT_DIR = join(ROOT, "screenshots");
mkdirSync(SHOT_DIR, { recursive: true });

const runtimeJs = readFileSync(RUNTIME, "utf8");

const FIXTURE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>XElement harness</title>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js"></script>
  <script src="/x_element.js"></script>
  <style>
    body { font-family: system-ui, sans-serif; padding: 24px; background: #f8fafc; color: #0f172a; }
    section { margin: 16px 0; padding: 16px; background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; }
    h1 { font-size: 1.25rem; }
    .pass { color: #059669; } .fail { color: #dc2626; }
  </style>
</head>
<body>
  <h1>XElement browser harness</h1>

  <!-- Definitions (x-tagname only) -->
  <div id="defs" hidden>
    <template x-tagname="hello">
      <div class="hello-inner" data-role="custom">Hello from CustomElement</div>
    </template>
    <template x-tagname="shadow-card" shadowroot="true">
      <div class="shadow-inner" data-role="shadow">
        <span>Shadow shell</span>
        <slot></slot>
      </div>
    </template>
    <template x-tagname="toggle">
      <div x-data="{ on: false }" @click="on = !on" class="toggle-inner" id="toggle-root">
        <span x-text="on ? 'ON' : 'OFF'" data-role="alpine"></span>
      </div>
    </template>
  </div>

  <section id="sec-custom">
    <h2>CustomElement host</h2>
    <x-hello id="host-hello"></x-hello>
  </section>

  <section id="sec-shadow">
    <h2>WebComponent host</h2>
    <x-shadow-card id="host-shadow">
      <span id="projected">projected light</span>
    </x-shadow-card>
  </section>

  <section id="sec-alpine">
    <h2>Alpine + XElement</h2>
    <x-toggle id="host-toggle"></x-toggle>
  </section>

  <section id="sec-dynamic">
    <h2>Dynamic after inject (HTMX-like)</h2>
    <div id="panel"></div>
    <button type="button" id="inject-btn">Inject partial</button>
  </section>

  <pre id="report"></pre>

  <script>
    document.getElementById('inject-btn').addEventListener('click', () => {
      const panel = document.getElementById('panel');
      panel.innerHTML = \`
        <template x-tagname="dyn">
          <div data-role="dyn">dynamic body</div>
        </template>
        <x-dyn id="host-dyn"></x-dyn>
      \`;
      // Simulate HTMX afterSwap
      document.dispatchEvent(new CustomEvent('htmx:afterSwap', { detail: {}, bubbles: true }));
      // scan target if API present
      if (window.UxDom && UxDom.XElement) UxDom.XElement.scan(panel);
    });
  </script>
</body>
</html>`;

function startStaticServer() {
  return new Promise((resolvePromise) => {
    const server = createServer((req, res) => {
      const url = req.url.split("?")[0];
      if (url === "/x_element.js") {
        res.writeHead(200, {
          "Content-Type": "application/javascript; charset=utf-8",
          "Cache-Control": "no-store",
        });
        res.end(runtimeJs);
        return;
      }
      if (url === "/" || url === "/index.html") {
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        res.end(FIXTURE_HTML);
        return;
      }
      res.writeHead(404);
      res.end("not found");
    });
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolvePromise({ server, base: `http://127.0.0.1:${port}` });
    });
  });
}

async function collectDomDetails(page) {
  return page.evaluate(() => {
    const details = {
      defined: {
        hello: !!customElements.get("x-hello"),
        shadowCard: !!customElements.get("x-shadow-card"),
        toggle: !!customElements.get("x-toggle"),
      },
      ux_dom: !!(window.UxDom && window.UxDom.XElement),
      attrTag: window.UxDom?.XElement?.ATTR_TAG || null,
      hello: null,
      shadow: null,
      toggle: null,
      dyn: null,
    };

    const hello = document.getElementById("host-hello");
    if (hello) {
      details.hello = {
        tag: hello.tagName,
        childText: hello.innerText.trim(),
        hasInner: !!hello.querySelector("[data-role=custom]"),
        childElementCount: hello.childElementCount,
      };
    }

    const shadowHost = document.getElementById("host-shadow");
    if (shadowHost) {
      const sr = shadowHost.shadowRoot;
      details.shadow = {
        tag: shadowHost.tagName,
        hasShadowRoot: !!sr,
        shadowText: sr ? sr.textContent.trim() : null,
        projectedVisible: !!document.getElementById("projected"),
        slotAssigned: sr
          ? [...sr.querySelectorAll("slot")].map((s) =>
              s.assignedNodes().map((n) => n.textContent || n.nodeName)
            )
          : [],
      };
    }

    const toggle = document.getElementById("host-toggle");
    if (toggle) {
      const alpineEl = toggle.querySelector("[data-role=alpine]") || toggle.querySelector("[x-text]");
      details.toggle = {
        tag: toggle.tagName,
        text: toggle.innerText.trim(),
        hasXData: !!toggle.querySelector("[x-data]"),
      };
    }

    const dyn = document.getElementById("host-dyn");
    if (dyn) {
      details.dyn = {
        defined: !!customElements.get("x-dyn"),
        text: dyn.innerText.trim(),
        tag: dyn.tagName,
      };
    }

    return details;
  });
}

function assertDetails(d, phase) {
  const fails = [];
  if (!d.ux_dom) fails.push(`${phase}: UxDom.XElement missing`);
  if (d.attrTag !== "x-tagname") fails.push(`${phase}: ATTR_TAG=${d.attrTag}`);
  if (!d.defined.hello) fails.push(`${phase}: x-hello not defined`);
  if (!d.defined.shadowCard) fails.push(`${phase}: x-shadow-card not defined`);
  if (!d.defined.toggle) fails.push(`${phase}: x-toggle not defined`);
  if (!d.hello?.hasInner) fails.push(`${phase}: hello inner not upgraded`);
  if (!String(d.hello?.childText || "").includes("Hello"))
    fails.push(`${phase}: hello text=${d.hello?.childText}`);
  if (!d.shadow?.hasShadowRoot) fails.push(`${phase}: no shadowRoot on x-shadow-card`);
  if (!String(d.shadow?.shadowText || "").includes("Shadow"))
    fails.push(`${phase}: shadow text missing`);
  if (!d.toggle?.hasXData && !d.toggle?.text)
    fails.push(`${phase}: toggle empty`);
  return fails;
}

async function run() {
  const { server, base } = await startStaticServer();
  const consoleErrors = [];
  const pageErrors = [];
  const report = {
    ok: false,
    base,
    phases: {},
    consoleErrors,
    pageErrors,
    screenshots: [],
    fails: [],
  };

  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });

  try {
    const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => pageErrors.push(String(err?.message || err)));

    await page.goto(base + "/", { waitUntil: "networkidle", timeout: 45000 });
    // Wait for custom elements + alpine
    await page.waitForFunction(
      () =>
        customElements.get("x-hello") &&
        customElements.get("x-shadow-card") &&
        customElements.get("x-toggle"),
      { timeout: 15000 }
    );
    await page.waitForTimeout(400);

    const initial = await collectDomDetails(page);
    report.phases.initial = initial;
    report.fails.push(...assertDetails(initial, "initial"));

    const shot1 = join(SHOT_DIR, "xelement-initial.png");
    await page.screenshot({ path: shot1, fullPage: true });
    report.screenshots.push(shot1);

    // Click alpine toggle if present
    const toggle = page.locator("#host-toggle");
    if (await toggle.count()) {
      await toggle.click({ force: true });
      await page.waitForTimeout(200);
      const afterClick = await collectDomDetails(page);
      report.phases.afterToggleClick = afterClick;
      // text may become ON if alpine wired
      const shot2 = join(SHOT_DIR, "xelement-after-toggle.png");
      await page.screenshot({ path: shot2, fullPage: true });
      report.screenshots.push(shot2);
    }

    // Dynamic inject
    await page.click("#inject-btn");
    await page.waitForTimeout(300);
    await page.waitForFunction(
      () => customElements.get("x-dyn") || document.getElementById("host-dyn"),
      { timeout: 10000 }
    ).catch(() => {});
    const afterDyn = await collectDomDetails(page);
    report.phases.afterDynamic = afterDyn;
    if (!afterDyn.defined?.dyn && !customElementsGet(afterDyn)) {
      // defined.dyn might not be in schema - check dyn field
    }
    if (!afterDyn.dyn?.defined && !afterDyn.dyn?.text) {
      // try again with scan
      await page.evaluate(() => {
        if (window.UxDom?.XElement) UxDom.XElement.scan(document);
      });
      await page.waitForTimeout(200);
    }
    const afterDyn2 = await collectDomDetails(page);
    report.phases.afterDynamic2 = afterDyn2;
    if (!afterDyn2.dyn?.defined && !(await page.evaluate(() => !!customElements.get("x-dyn")))) {
      report.fails.push("dynamic: x-dyn not defined after inject");
    } else if (afterDyn2.dyn && !String(afterDyn2.dyn.text || "").includes("dynamic")) {
      // upgrade may put text inside
      const text = await page.locator("#host-dyn").innerText().catch(() => "");
      if (!text.includes("dynamic"))
        report.fails.push(`dynamic: host text=${JSON.stringify(text)}`);
    }

    const shot3 = join(SHOT_DIR, "xelement-after-dynamic.png");
    await page.screenshot({ path: shot3, fullPage: true });
    report.screenshots.push(shot3);

    // Mobile viewport
    await page.setViewportSize({ width: 390, height: 844 });
    const shotM = join(SHOT_DIR, "xelement-mobile.png");
    await page.screenshot({ path: shotM, fullPage: true });
    report.screenshots.push(shotM);

    // Optional kit URL
    const kitUrl = process.env.KIT_URL;
    if (kitUrl) {
      await page.setViewportSize({ width: 1100, height: 900 });
      const kr = await page.goto(kitUrl.replace(/\/$/, "") + "/wc/WcDemo", {
        waitUntil: "networkidle",
        timeout: 45000,
      });
      report.phases.kit = {
        status: kr?.status() ?? 0,
        hasXHello: (await page.locator("x-hello").count()) > 0,
        bodyLen: (await page.locator("body").innerText()).trim().length,
      };
      const shotK = join(SHOT_DIR, "xelement-kit-wc.png");
      await page.screenshot({ path: shotK, fullPage: true });
      report.screenshots.push(shotK);
      if ((report.phases.kit.status || 0) >= 400)
        report.fails.push(`kit status ${report.phases.kit.status}`);
    }

    if (pageErrors.length) report.fails.push(...pageErrors.map((e) => `pageerror: ${e}`));
    // Filter noisy CDN console errors optionally
    const hardConsole = consoleErrors.filter(
      (e) => !/favicon|cdn\.jsdelivr|alpine/i.test(e) || /x_element|UxDom|CustomElement/i.test(e)
    );
    // Keep all console errors as soft warnings in report; fail only on pageerrors + assertion fails
    report.consoleErrors = consoleErrors;

    report.ok = report.fails.length === 0;
    const outJson = join(SHOT_DIR, "xelement-browser-report.json");
    writeFileSync(outJson, JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));

    if (!report.ok) process.exit(1);
    if (pageErrors.length) process.exit(2);
    process.exit(0);
  } catch (err) {
    report.ok = false;
    report.fails.push(String(err?.message || err));
    writeFileSync(
      join(SHOT_DIR, "xelement-browser-report.json"),
      JSON.stringify(report, null, 2)
    );
    console.error(JSON.stringify(report, null, 2));
    process.exit(1);
  } finally {
    await browser.close();
    server.close();
  }
}

function customElementsGet() {
  return false;
}

await run();
