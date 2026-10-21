/**
 * Headless Chromium: does a page run script when its links are clicked?
 *
 * Reads a JSON list of ``{html, probe}`` on stdin. Each ``html`` body loads as
 * its own page at http://t.test/ with a ``hit()`` function that counts calls.
 * After SMIL animations finish, the harness evaluates ``probe`` (a JS
 * expression, or null), then clicks every ``a`` and ``svg rect`` and prints
 * ``{hits, probe}`` per page. A click that navigates away ends that page.
 *
 *   echo '[{"html": "<a href=\"javascript:hit()\">x</a>", "probe": null}]' \
 *     | node tests/browser/url_click_harness.mjs
 */
import { chromium } from "playwright";

let input = "";
for await (const chunk of process.stdin) input += chunk;
const pages = JSON.parse(input);

const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
try {
  const results = [];
  for (const { html, probe } of pages) {
    const context = await browser.newContext();
    const page = await context.newPage();
    let hits = 0;
    await page.exposeFunction("hit", () => {
      hits++;
    });
    await page.route("http://t.test/**", (route) =>
      route.fulfill({
        contentType: "text/html",
        body: `<!DOCTYPE html><html><body>${html}</body></html>`,
      }),
    );
    await page.goto("http://t.test/", { waitUntil: "load" });
    await page.waitForTimeout(300); // animations use dur=0.05s fill=freeze
    const value = probe ? await page.evaluate(probe) : null;
    const targets = page.locator("a, svg rect");
    const count = await targets.count();
    for (let i = 0; i < count; i++) {
      try {
        await targets.nth(i).click({ force: true, timeout: 800 });
      } catch {}
      await page.waitForTimeout(150);
      if (!page.url().startsWith("http://t.test/")) break;
    }
    await page.waitForTimeout(150);
    results.push({ hits, probe: value });
    await context.close();
  }
  process.stdout.write(JSON.stringify(results));
} finally {
  await browser.close();
}
