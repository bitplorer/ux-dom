/**
 * Headless Chromium: the text a browser displays for HTML snippets.
 *
 * Reads a JSON list of HTML strings on stdin, puts each in its own <div>
 * and prints the list of their ``innerText`` as JSON.
 *
 *   echo '["a&#39;b"]' | node tests/browser/inner_text_harness.mjs
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
  const texts = await page.evaluate((list) => {
    return list.map((html) => {
      const box = document.createElement("div");
      box.innerHTML = html;
      document.body.append(box);
      return box.innerText;
    });
  }, snippets);
  process.stdout.write(JSON.stringify(texts));
} finally {
  await browser.close();
}
