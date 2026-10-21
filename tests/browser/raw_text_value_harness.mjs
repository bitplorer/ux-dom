/**
 * Headless Chromium: the values a page computes from raw text bodies.
 *
 * Reads a JSON list of HTML body strings on stdin, loads each as its own page
 * and prints, per page, what its scripts stored in ``window.__out``, the
 * ``value`` of each ``<textarea>``, the ``textContent`` of each
 * pre / listing / xmp / plaintext / title / iframe / noscript, and the ``::before``
 * ``content`` of each ``.probe`` element, and the ``namespaceURI`` of each
 * element with an ``id``.
 *
 *   echo '["<script>__out = {a: `x`}</script>"]' | node tests/browser/raw_text_value_harness.mjs
 */
import { chromium } from "playwright";

let input = "";
for await (const chunk of process.stdin) input += chunk;
const bodies = JSON.parse(input);

const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
try {
  const results = [];
  for (const body of bodies) {
    // A fresh page each time: setContent keeps the Document (and its
    // adoptedStyleSheets) of the page it writes into.
    const page = await browser.newPage();
    await page.setContent(
      `<!DOCTYPE html><html><head><script>window.__out = {}</script></head><body>${body}</body></html>`,
    );
    results.push(
      await page.evaluate(() => {
        const all = (sel) => [...document.querySelectorAll(sel)];
        return {
          out: window.__out,
          values: all("textarea").map((e) => e.value),
          texts: all("pre, listing, xmp, plaintext, title, iframe, noscript").map(
            (e) => e.textContent,
          ),
          before: all(".probe").map(
            (e) => getComputedStyle(e, "::before").content,
          ),
          ns: Object.fromEntries(all("[id]").map((e) => [e.id, e.namespaceURI])),
        };
      }),
    );
    await page.close();
  }
  process.stdout.write(JSON.stringify(results));
} finally {
  await browser.close();
}
