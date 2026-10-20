/**
 * Headless Chromium: what the HTML parser builds from fragments.
 *
 * Reads a JSON list of HTML strings on stdin, sets each as the ``innerHTML``
 * of its own <div> and prints, per string, the div's ``innerHTML`` (the DOM it
 * built, serialized), its ``innerText`` and the ``value`` of each <textarea>.
 *
 *   echo '["<pre>\\n\\n a</pre>"]' | node tests/browser/parse_roundtrip_harness.mjs
 */
import { chromium } from "playwright";

let input = "";
for await (const chunk of process.stdin) input += chunk;
const snippets = JSON.parse(input);

const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
try {
  const page = await browser.newPage();
  await page.setContent("<!DOCTYPE html><html><body></body></html>");
  const results = await page.evaluate((list) => {
    return list.map((html) => {
      const box = document.createElement("div");
      box.innerHTML = html;
      document.body.append(box);
      const out = {
        html: box.innerHTML,
        text: box.innerText,
        values: [...box.querySelectorAll("textarea")].map((e) => e.value),
      };
      box.remove();
      return out;
    });
  }, snippets);
  process.stdout.write(JSON.stringify(results));
} finally {
  await browser.close();
}
