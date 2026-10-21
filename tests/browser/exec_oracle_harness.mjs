/**
 * Headless Chromium: does any of these HTML bodies run script?
 *
 * Reads a JSON list of HTML strings on stdin. Each one loads as the srcdoc of
 * its own iframe, behind a prelude that turns ``hit()``, ``alert``,
 * ``confirm``, ``prompt`` and ``print`` into a counter for that body. After
 * SMIL animations finish, every element gets mouse, pointer, focus, toggle,
 * load, error and animation events, so a surviving handler, ``javascript:``
 * link, form action or ``begin=click`` animation runs. Every request but the
 * host page gets HTTP 204, so a link or form that navigates leaves the frame
 * in place. Prints ``{hits, stray}``: per-body counts, and calls that came
 * from no body's prelude (the top page, or a document a ``javascript:`` URL
 * or ``data:`` frame made).
 *
 *   echo '["<img src=x onerror=alert(1)>"]' | node tests/browser/exec_oracle_harness.mjs
 */
import { chromium } from "playwright";

let input = "";
for await (const chunk of process.stdin) input += chunk;
const bodies = JSON.parse(input);

const TOP = "http://t.test/oracle";
const BATCH = 50;
const EVENTS = [
  "pointerover", "mouseover", "mouseenter", "pointerdown", "mousedown",
  "pointerup", "mouseup", "click", "focus", "focusin", "blur", "toggle",
  "load", "error", "animationstart", "animationend", "transitionend",
];

const hits = bodies.map(() => 0);
let stray = 0;

const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
try {
  const context = await browser.newContext();
  await context.exposeFunction("hit", (i) => {
    if (Number.isInteger(i) && i >= 0 && i < hits.length) hits[i]++;
    else stray++;
  });
  await context.route("**/*", (route) =>
    route.request().url() === TOP
      ? route.fulfill({
          contentType: "text/html",
          body:
            "<!DOCTYPE html><html><body><script>" +
            "alert = confirm = prompt = print = () => hit(-1);" +
            "</script></body></html>",
        })
      : route.fulfill({ status: 204, body: "" }),
  );
  for (let start = 0; start < bodies.length; start += BATCH) {
    const page = await context.newPage();
    page.on("dialog", (dialog) => {
      stray++;
      dialog.dismiss().catch(() => {});
    });
    await page.goto(TOP, { waitUntil: "load" });
    const batch = bodies.slice(start, start + BATCH);
    await page.evaluate(
      ([list, offset]) =>
        Promise.all(
          list.map(
            (html, k) =>
              new Promise((resolve) => {
                const frame = document.createElement("iframe");
                const prelude =
                  "<script>{const h = window.hit; window.hit = () => h(" +
                  (offset + k) +
                  "); alert = confirm = prompt = print = window.hit;}</scr" +
                  "ipt>";
                frame.onload = () => resolve();
                setTimeout(resolve, 3000);
                frame.srcdoc = prelude + html;
                document.body.append(frame);
              }),
          ),
        ),
      [batch, start],
    );
    await page.waitForTimeout(300); // animations use dur=0.05s fill=freeze
    await page.evaluate((events) => {
      for (const frame of document.querySelectorAll("iframe")) {
        const doc = frame.contentDocument;
        if (!doc) continue;
        const view = doc.defaultView;
        for (const el of doc.querySelectorAll("*")) {
          for (const type of events) {
            const Kind = type.startsWith("pointer")
              ? view.PointerEvent
              : type.startsWith("mouse") || type === "click"
                ? view.MouseEvent
                : view.Event;
            try {
              el.dispatchEvent(
                new Kind(type, { bubbles: true, cancelable: true, view }),
              );
            } catch {}
          }
        }
      }
    }, EVENTS);
    await page.waitForTimeout(400);
    await page.close();
  }
  process.stdout.write(JSON.stringify({ hits, stray }));
} finally {
  await browser.close();
}
