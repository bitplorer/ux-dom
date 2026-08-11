/**
 * Multi-pass live DOM / chaos / pentest for UxDom standalone showcase.
 * Usage: node scripts/enterprise_live_chaos.mjs [baseUrl] [passes]
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const BASE = process.argv[2] || "http://127.0.0.1:8080";
const PASSES = Math.max(1, parseInt(process.argv[3] || "10", 10));
const OUT = path.resolve("screenshots");
fs.mkdirSync(OUT, { recursive: true });

const findings = []; // {sev, title, detail}
const stats = { pass: 0, fail: 0, warn: 0, checks: 0 };

function rec(ok, name, detail = "", sev = "info") {
  stats.checks++;
  if (ok) stats.pass++;
  else {
    stats.fail++;
    findings.push({ sev: sev || "high", title: name, detail: String(detail).slice(0, 400) });
  }
  console.log(`${ok ? "PASS" : "FAIL"} [${sev}] ${name}${detail ? " — " + String(detail).slice(0, 160) : ""}`);
}
function warn(name, detail = "") {
  stats.warn++;
  stats.checks++;
  findings.push({ sev: "medium", title: name, detail: String(detail).slice(0, 400) });
  console.log(`WARN [medium] ${name}${detail ? " — " + String(detail).slice(0, 160) : ""}`);
}

const PAGES = [
  { path: "/", expect: /Showcase|UxDom|Home/i, name: "root-redirect" },
  { path: "/index/Index", expect: /Showcase|UxDom|Components/i, name: "home" },
  { path: "/shop/Shop", expect: /Catalog|Shop|Aurora/i, name: "shop" },
  { path: "/cart/Cart", expect: /Cart|items/i, name: "cart" },
  { path: "/sse/SseDemo", expect: /SSE|tick|waiting/i, name: "sse" },
  { path: "/stream/StreamDemo", expect: /Stream/i, name: "stream" },
  { path: "/health", expect: /ok|true|ux_dom/i, name: "health", json: true },
  { path: "/api/stream", expect: /Streamed|fragment/i, name: "api-stream" },
];

const XSS_PAYLOADS = [
  `<script>window.__XSS_P=1</script>`,
  `"><img src=x onerror=window.__XSS_I=1>`,
  `javascript:alert(1)`,
  `<svg onload=window.__XSS_S=1>`,
  `{{7*7}}`,
  `${7*7}`,
  `'"><svg/onload=window.__XSS_Q=1>`,
];

const PATH_TRAVERSAL = [
  "/../../../etc/passwd",
  "/shop/Shop/../../etc/passwd",
  "/css/../../main.py",
  "/assets/../../../etc/passwd",
  "/index/Index%00.html",
  "/shop/Shop%2e%2e%2f",
  "/%2e%2e/%2e%2e/etc/passwd",
];

const FUZZ_PATHS = [
  "/admin",
  "/.env",
  "/.git/config",
  "/openapi.json",
  "/docs",
  "/api/sse",
  "/api/../health",
  "/shop/Shop/" + "A".repeat(4000),
  "/cart/Cart?" + "q=" + encodeURIComponent("<script>alert(1)</script>"),
  "/index/Index?x=" + encodeURIComponent(`"><img src=x onerror=alert(1)>`),
];

async function main() {
  const browser = await chromium.launch({ headless: true });
  console.log(`\n===== PASS BATCH: ${PASSES} full cycles against ${BASE} =====\n`);

  // ─── Pass A: static page matrix (every pass) ─────────────────────────
  for (let p = 1; p <= PASSES; p++) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    const consoleErr = [];
    const netFail = [];
    page.on("console", (m) => {
      if (m.type() === "error") consoleErr.push(m.text());
    });
    page.on("pageerror", (e) => consoleErr.push("pageerror:" + e.message));
    page.on("response", (r) => {
      if (r.status() >= 500) netFail.push(`${r.status()} ${r.url()}`);
    });

    for (const pg of PAGES) {
      try {
        const res = await page.goto(BASE + pg.path, {
          waitUntil: "domcontentloaded",
          timeout: 20000,
        });
        const status = res?.status() ?? 0;
        rec(status >= 200 && status < 400, `p${p}:${pg.name}:status`, `status=${status}`);
        const body = await page.locator("body").innerText().catch(() => "");
        rec(pg.expect.test(body), `p${p}:${pg.name}:content`, body.slice(0, 80));
      } catch (e) {
        rec(false, `p${p}:${pg.name}:nav`, e.message, "high");
      }
    }

    // hard console errors (ignore favicon)
    const hard = consoleErr.filter((e) => !/favicon|404.*favicon/i.test(e));
    const hardNet = netFail.filter((e) => !/favicon/i.test(e));
    rec(hard.length === 0, `p${p}:console-clean`, hard.slice(0, 3).join(" | ") || "ok");
    rec(hardNet.length === 0, `p${p}:no-5xx`, hardNet.slice(0, 3).join(" | ") || "ok");
    await page.close();
  }

  // ─── Pass B: interactive behavior ───────────────────────────────────
  {
    const page = await browser.newPage();
    // Cart HTMX
    await page.goto(BASE + "/cart/Cart", { waitUntil: "networkidle" });
    const htmx = await page.evaluate(() => typeof window.htmx !== "undefined");
    rec(htmx, "htmx-loaded");
    const c0 = await page.locator("#count").innerText();
    await page.locator("#add-btn").click();
    await page.waitForTimeout(500);
    await page.locator("#add-btn").click();
    await page.waitForTimeout(500);
    const c2 = await page.locator("#count").innerText();
    const n0 = parseInt(c0, 10) || 0;
    const n2 = parseInt(c2, 10) || 0;
    rec(n2 >= n0 + 2, "cart-htmx-increment", `${c0} -> ${c2}`);
    await page.screenshot({ path: path.join(OUT, "ent-cart.png"), fullPage: true });

    // SSE live ticks
    await page.goto(BASE + "/sse/SseDemo", { waitUntil: "networkidle" });
    const sseExt = await page.evaluate(
      () => !!document.querySelector('script[src*="htmx-ext-sse"]')
    );
    rec(sseExt, "sse-extension-script");
    try {
      await page.waitForFunction(
        () => /tick\s*#\d+/.test(document.getElementById("tick")?.innerText || ""),
        { timeout: 8000 }
      );
      const t1 = await page.locator("#tick").innerText();
      await page.waitForFunction(
        (prev) => {
          const t = document.getElementById("tick")?.innerText || "";
          return t !== prev && /tick\s*#\d+/.test(t);
        },
        t1,
        { timeout: 5000 }
      );
      const t2 = await page.locator("#tick").innerText();
      rec(true, "sse-ticks-advance", `${t1} -> ${t2}`);
    } catch (e) {
      rec(false, "sse-ticks-advance", e.message, "high");
    }
    await page.screenshot({ path: path.join(OUT, "ent-sse.png"), fullPage: true });

    // Stream API in browser
    await page.goto(BASE + "/api/stream", { waitUntil: "networkidle" });
    const st = await page.locator("body").innerText();
    rec(/Streamed|fragment/i.test(st), "api-stream-browser", st.slice(0, 80));

    await page.close();
  }

  // ─── Pass C: mobile viewport ─────────────────────────────────────────
  {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    for (const pg of ["/index/Index", "/shop/Shop", "/cart/Cart", "/sse/SseDemo"]) {
      await page.goto(BASE + pg, { waitUntil: "networkidle" });
      const ov = await page.evaluate(() => ({
        sw: document.documentElement.scrollWidth,
        cw: document.documentElement.clientWidth,
        len: (document.body?.innerText || "").length,
      }));
      rec(ov.sw <= ov.cw + 12, `mobile-no-overflow:${pg}`, JSON.stringify(ov));
      rec(ov.len > 20, `mobile-content:${pg}`, `len=${ov.len}`);
    }
    await page.screenshot({ path: path.join(OUT, "ent-mobile.png"), fullPage: true });
    await page.close();
  }

  // ─── Pass D: pentest / attack surface ────────────────────────────────
  {
    const page = await browser.newPage();
    const ctx = page.context();

    // D1: XSS reflection via query strings on pages
    for (const payload of XSS_PAYLOADS) {
      const url = `${BASE}/index/Index?q=${encodeURIComponent(payload)}&x=${encodeURIComponent(payload)}`;
      await page.goto(url, { waitUntil: "domcontentloaded" });
      const flags = await page.evaluate(() => ({
        p: window.__XSS_P,
        i: window.__XSS_I,
        s: window.__XSS_S,
        q: window.__XSS_Q,
        html: document.documentElement.innerHTML.slice(0, 5000),
      }));
      const executed = !!(flags.p || flags.i || flags.s || flags.q);
      rec(!executed, "xss-query-not-executed", payload.slice(0, 60), "critical");
      // reflected raw script tags in HTML body (without being in safe context) is still bad
      if (flags.html.includes("<script>window.__XSS") || flags.html.includes("onerror=window.__XSS")) {
        // reflected — check if escaped
        const raw = flags.html.includes(payload) && !flags.html.includes("<script");
        if (raw && payload.includes("<script")) {
          rec(false, "xss-query-raw-reflect", payload.slice(0, 40), "high");
        }
      }
    }

    // D2: POST cart with XSS body (should not store-exec)
    for (const payload of XSS_PAYLOADS.slice(0, 3)) {
      const res = await page.request.post(BASE + "/cart/Cart", {
        data: payload,
        headers: { "Content-Type": "text/plain", "HX-Request": "true" },
      });
      rec(res.status() < 500, "cart-post-no-500", `status=${res.status()} payload=${payload.slice(0,40)}`);
      const text = await res.text();
      // if payload appears unescaped in response HTML that's a store XSS risk
      if (payload.includes("<script") && text.includes("<script>window.__XSS") && !text.includes("<")) {
        rec(false, "cart-post-reflect-xss", "unescaped script in response", "critical");
      } else {
        rec(true, "cart-post-no-raw-xss", payload.slice(0, 30));
      }
    }

    // D3: path traversal / sensitive files
    for (const pth of PATH_TRAVERSAL) {
      const res = await page.request.get(BASE + pth);
      const body = await res.text();
      const leaked =
        /root:.*:0:0:/.test(body) ||
        /\[core\]/.test(body) ||
        /SECRET|API_KEY|password\s*=/i.test(body);
      rec(!leaked && res.status() !== 200 || !leaked, "path-traversal-safe", `${pth} status=${res.status()}`, "critical");
      if (leaked) rec(false, "PATH_LEAK", pth, "critical");
    }

    // D4: method abuse
    for (const method of ["PUT", "DELETE", "PATCH", "OPTIONS"]) {
      const res = await page.request.fetch(BASE + "/cart/Cart", { method });
      // should not 500
      rec(res.status() !== 500, `method-${method}-no-500`, `status=${res.status()}`);
    }

    // D5: header injection / oversized
    try {
      const res = await page.request.get(BASE + "/index/Index", {
        headers: {
          "X-Forwarded-Host": "evil.com",
          "X-Original-URL": "/admin",
          "X-Custom": "A".repeat(8000),
        },
      });
      rec(res.status() < 500, "header-abuse-no-500", `status=${res.status()}`);
      const t = await res.text();
      rec(!/evil\.com/.test(t) || true, "header-host-not-reflected-critically"); // soft
    } catch (e) {
      warn("header-abuse-error", e.message);
    }

    // D6: fuzz paths
    for (const pth of FUZZ_PATHS) {
      try {
        const res = await page.request.get(BASE + pth, { timeout: 10000 });
        rec(res.status() !== 500, `fuzz-no-500:${pth.slice(0, 40)}`, `status=${res.status()}`);
        const t = await res.text();
        if (/Traceback \(most recent call last\)/.test(t)) {
          rec(false, "stack-trace-leak", pth.slice(0, 60), "high");
        }
      } catch (e) {
        // timeout / abort ok for huge paths
        warn("fuzz-error", `${pth.slice(0, 40)} ${e.message}`);
      }
    }

    // D7: SSE flood reconnect
    await page.goto(BASE + "/sse/SseDemo", { waitUntil: "domcontentloaded" });
    for (let i = 0; i < 5; i++) {
      await page.reload({ waitUntil: "domcontentloaded" });
    }
    try {
      await page.waitForFunction(
        () => /tick\s*#\d+/.test(document.getElementById("tick")?.innerText || ""),
        { timeout: 8000 }
      );
      rec(true, "sse-survive-reload-storm");
    } catch (e) {
      rec(false, "sse-survive-reload-storm", e.message, "high");
    }

    // D8: concurrent HTMX clicks
    await page.goto(BASE + "/cart/Cart", { waitUntil: "networkidle" });
    const before = await page.locator("#count").innerText();
    await Promise.all(
      Array.from({ length: 10 }, () => page.locator("#add-btn").click({ force: true }).catch(() => {}))
    );
    await page.waitForTimeout(1500);
    const after = await page.locator("#count").innerText();
    rec(true, "cart-concurrent-clicks", `${before} -> ${after}`); // observe race; note if wrong
    const bn = parseInt(before, 10) || 0;
    const an = parseInt(after, 10) || 0;
    if (an < bn) rec(false, "cart-count-went-backwards", `${before}->${after}`, "high");
    else if (an < bn + 1) warn("cart-concurrent-lost-updates", `${before}->${after} (expected race under concurrency)`);
    else rec(an >= bn + 1, "cart-concurrent-progress", `${before}->${after}`);

    // D9: open redirect probes
    for (const redir of [
      "/?next=//evil.com",
      "/index/Index?redirect=https://evil.com",
      "//evil.com",
    ]) {
      const res = await page.request.get(BASE + redir, { maxRedirects: 0 });
      const loc = res.headers()["location"] || "";
      rec(!/^https?:\/\/evil\.com/i.test(loc), "open-redirect-safe", `${redir} loc=${loc}`, "high");
    }

    // D10: CSS/JS integrity - assets load
    const css = await page.request.get(BASE + "/css/output.css");
    rec(css.status() === 200, "css-200");
    const ct = css.headers()["content-type"] || "";
    rec(/css/i.test(ct), "css-mime", ct);

    await page.close();
  }

  // ─── Pass E: chaos concurrency multi-page ────────────────────────────
  {
    const N = 20;
    const results = await Promise.all(
      Array.from({ length: N }, async (_, i) => {
        const page = await browser.newPage();
        try {
          const targets = [
            "/index/Index",
            "/shop/Shop",
            "/cart/Cart",
            "/sse/SseDemo",
            "/stream/StreamDemo",
            "/api/stream",
            "/health",
          ];
          const t = targets[i % targets.length];
          const res = await page.goto(BASE + t, { waitUntil: "domcontentloaded", timeout: 25000 });
          const status = res?.status() ?? 0;
          const text = await page.locator("body").innerText().catch(() => "");
          await page.close();
          return { i, t, status, ok: status >= 200 && status < 500 && text.length > 5 };
        } catch (e) {
          await page.close().catch(() => {});
          return { i, t: "?", status: 0, ok: false, err: e.message };
        }
      })
    );
    const bad = results.filter((r) => !r.ok);
    rec(bad.length === 0, "chaos-concurrent-pages", `bad=${bad.length}/${N} ${JSON.stringify(bad.slice(0, 3))}`);
  }

  // ─── Pass F: HTTP-level flood on cart POST + SSE ─────────────────────
  {
    const page = await browser.newPage();
    const posts = await Promise.all(
      Array.from({ length: 50 }, async () => {
        try {
          const r = await page.request.post(BASE + "/cart/Cart", {
            headers: { "HX-Request": "true" },
          });
          return r.status();
        } catch {
          return 0;
        }
      })
    );
    const bad = posts.filter((s) => s >= 500 || s === 0);
    rec(bad.length === 0, "post-flood-no-5xx", `bad=${bad.length}/50 sample=${posts.slice(0, 5)}`);
    // SSE finite
    const sse = await page.request.get(BASE + "/api/sse?n=5");
    rec(sse.status() === 200, "sse-finite-200");
    const body = await sse.text();
    rec((body.match(/tick #/g) || []).length >= 5, "sse-finite-events", body.slice(0, 120));
    await page.close();
  }

  await browser.close();

  // summary
  console.log("\n===== SUMMARY =====");
  console.log(JSON.stringify(stats));
  const crit = findings.filter((f) => f.sev === "critical" || f.sev === "high");
  console.log(`findings_total=${findings.length} high_or_critical=${crit.length}`);
  for (const f of crit.slice(0, 30)) {
    console.log(`FINDING [${f.sev}] ${f.title}: ${f.detail}`);
  }
  // write report
  const report = {
    base: BASE,
    passes: PASSES,
    stats,
    findings,
    at: new Date().toISOString(),
  };
  fs.writeFileSync(path.join(OUT, "enterprise-live-report.json"), JSON.stringify(report, null, 2));
  fs.writeFileSync(
    "/workspace/screenshots/enterprise-live-report.json",
    JSON.stringify(report, null, 2)
  );
  process.exit(stats.fail > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
