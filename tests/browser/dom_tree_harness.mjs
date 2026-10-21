/**
 * Headless Chromium: the element tree the HTML parser builds from fragments.
 *
 * Reads a JSON list of HTML strings on stdin, sets each as the ``innerHTML``
 * of its own <div> and prints, per string, the div's element children as
 * ``[localName, namespaceURI, [children...]]``. Text and comments are left out.
 *
 *   echo '["<svg><rect/></svg>"]' | node tests/browser/dom_tree_harness.mjs
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
    const tree = (el) => [...el.children].map((c) => [c.localName, c.namespaceURI, tree(c)]);
    return list.map((html) => {
      const box = document.createElement("div");
      box.innerHTML = html;
      document.body.append(box);
      const out = tree(box);
      box.remove();
      return out;
    });
  }, snippets);
  process.stdout.write(JSON.stringify(results));
} finally {
  await browser.close();
}
