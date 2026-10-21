/**
 * Headless Chromium: the IDL state a boolean attribute gives an element.
 *
 * Reads a JSON list of ``[html, selector, property]`` on stdin, sets each
 * html as the ``innerHTML`` of its own <div> and prints, per item, the value
 * of ``property`` on the element ``selector`` finds (``checked``,
 * ``disabled``, ``readOnly``, ...).
 *
 *   echo '[["<input checked>", "input", "checked"]]' | node tests/browser/boolean_state_harness.mjs
 */
import { chromium } from "playwright";

let input = "";
for await (const chunk of process.stdin) input += chunk;
const cases = JSON.parse(input);

const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
try {
  const page = await browser.newPage();
  await page.setContent("<!DOCTYPE html><html><body></body></html>");
  const results = await page.evaluate((list) => {
    return list.map(([html, selector, prop]) => {
      const box = document.createElement("div");
      box.innerHTML = html;
      document.body.append(box);
      const value = box.querySelector(selector)[prop];
      box.remove();
      return value;
    });
  }, cases);
  process.stdout.write(JSON.stringify(results));
} finally {
  await browser.close();
}
