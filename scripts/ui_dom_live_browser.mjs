/**
 * Live browser QA for UxDom standalone showcase.
 * Usage: node scripts/ux_dom_live_browser.mjs [baseUrl]
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const BASE = process.argv[2] || "http://127.0.0.1:8080";
const OUT = path.resolve("screenshots");
fs.mkdirSync(OUT, { recursive: true });

const results = [];
function log(ok, name, detail = "") {
  results.push({ ok, name, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(`console: ${msg.text()}`);
  });

  // 1) Home (follow redirect)
  let res = await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 30000 });
  log(!!res && res.ok(), "home status", `status=${res?.status()} url=${page.url()}`);
  const title = await page.title();
  log(title.includes("UxDom") || title.length > 0, "home title", title);
  const bodyText = await page.locator("body").innerText();
  log(bodyText.includes("Showcase") || bodyText.includes("UxDom"), "home has content", bodyText.slice(0, 80));
  await page.screenshot({ path: path.join(OUT, "ux_dom-home.png"), fullPage: true });

  // Visible structure
  const h1 = await page.locator("h1").first().textContent().catch(() => null);
  log(!!h1 && h1.length > 0, "home h1", h1 || "missing");

  // Nav links present
  for (const label of ["Home", "Shop", "Cart", "Live SSE", "Stream"]) {
    const n = await page.getByRole("link", { name: label }).count();
    log(n >= 1, `nav link: ${label}`, `count=${n}`);
  }

  // 2) Shop
  res = await page.goto(BASE + "/shop/Shop", { waitUntil: "networkidle", timeout: 30000 });
  log(!!res && res.ok(), "shop status", `status=${res?.status()}`);
  const shopText = await page.locator("body").innerText();
  log(shopText.length > 20, "shop has body text", shopText.slice(0, 100));
  await page.screenshot({ path: path.join(OUT, "ux_dom-shop.png"), fullPage: true });

  // Try HTMX / interactive buttons if any
  const buttons = page.locator("button, [hx-get], [hx-post], a.btn, [data-ux-action]");
  const btnCount = await buttons.count();
  log(true, "interactive elements", `count=${btnCount}`);
  if (btnCount > 0) {
    try {
      await buttons.first().click({ timeout: 3000 });
      await page.waitForTimeout(500);
      log(true, "first interactive click");
    } catch (e) {
      log(false, "first interactive click", String(e).slice(0, 120));
    }
  }

  // 3) Cart
  res = await page.goto(BASE + "/cart/Cart", { waitUntil: "networkidle", timeout: 30000 });
  log(!!res && res.ok(), "cart status", `status=${res?.status()}`);
  await page.screenshot({ path: path.join(OUT, "ux_dom-cart.png"), fullPage: true });

  // 4) SSE demo
  res = await page.goto(BASE + "/sse/SseDemo", { waitUntil: "domcontentloaded", timeout: 30000 });
  log(!!res && res.ok(), "sse status", `status=${res?.status()}`);
  await page.waitForTimeout(1500);
  const sseText = await page.locator("body").innerText();
  log(sseText.length > 10, "sse has content", sseText.slice(0, 120));
  await page.screenshot({ path: path.join(OUT, "ux_dom-sse.png"), fullPage: true });

  // 5) Stream
  res = await page.goto(BASE + "/stream/StreamDemo", { waitUntil: "networkidle", timeout: 30000 });
  log(!!res && res.ok(), "stream status", `status=${res?.status()}`);
  await page.screenshot({ path: path.join(OUT, "ux_dom-stream.png"), fullPage: true });

  // 6) Health
  res = await page.goto(BASE + "/health", { waitUntil: "networkidle", timeout: 15000 });
  log(!!res && res.ok(), "health status", `status=${res?.status()}`);
  const healthBody = await page.locator("body").innerText().catch(() => "");
  log(true, "health body", healthBody.slice(0, 80));

  // 7) Mobile viewport
  await page.setViewportSize({ width: 390, height: 844 });
  res = await page.goto(BASE + "/index/Index", { waitUntil: "networkidle", timeout: 30000 });
  log(!!res && res.ok(), "mobile home status", `status=${res?.status()}`);
  const overflow = await page.evaluate(() => {
    return {
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      bodyTextLen: (document.body && document.body.innerText || "").length,
    };
  });
  log(
    overflow.scrollWidth <= overflow.clientWidth + 8,
    "mobile no horizontal overflow",
    JSON.stringify(overflow)
  );
  log(overflow.bodyTextLen > 20, "mobile visible content", `len=${overflow.bodyTextLen}`);
  await page.screenshot({ path: path.join(OUT, "ux_dom-mobile.png"), fullPage: true });

  // 8) Console errors (filter network 404 noise optionally)
  const hard = errors.filter((e) => !e.includes("favicon"));
  log(hard.length === 0, "no console/page errors", hard.slice(0, 5).join(" | ") || "clean");

  await browser.close();

  const failed = results.filter((r) => !r.ok);
  console.log("\n==== SUMMARY ====");
  console.log(`total=${results.length} pass=${results.length - failed.length} fail=${failed.length}`);
  if (failed.length) {
    for (const f of failed) console.log(" -", f.name, f.detail);
    process.exit(1);
  }
  process.exit(0);
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
