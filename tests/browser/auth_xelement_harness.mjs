/**
 * Live Chromium: complex CustomElement / AlpineComponent auth flows.
 *
 * Serves a page built by Python (AUTH_HTML_PATH) with x_element.js + Alpine,
 * then exercises login/signup upgrade, validation, success, multi-instance,
 * and shadow shell slots.
 *
 *   AUTH_HTML_PATH=/tmp/auth.html AUTH_JS_PATH=... node tests/browser/auth_xelement_harness.mjs
 */
import { createServer } from "node:http";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "/workspace/node_modules/playwright/index.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "../..");
const SHOT = join(ROOT, "screenshots/auth-xelements");
mkdirSync(SHOT, { recursive: true });

const HTML_PATH = process.env.AUTH_HTML_PATH;
const JS_PATH =
  process.env.AUTH_JS_PATH || join(ROOT, "src/ux_dom/scripts/x_element.js");
if (!HTML_PATH) {
  console.error(JSON.stringify({ ok: false, error: "AUTH_HTML_PATH required" }));
  process.exit(1);
}

const fails = [];
const phases = {};
function fail(m) {
  fails.push(m);
}

/** Playwright fill + input/change so Alpine x-model always sees values. */
async function fillAlpine(locator, value) {
  await locator.fill(value);
  await locator.dispatchEvent("input");
  await locator.dispatchEvent("change");
}

async function run() {
  const html = readFileSync(HTML_PATH, "utf8");
  const js = readFileSync(JS_PATH, "utf8");

  const server = createServer((req, res) => {
    const url = req.url.split("?")[0];
    if (url === "/x_element.js") {
      res.writeHead(200, { "Content-Type": "application/javascript; charset=utf-8" });
      res.end(js);
      return;
    }
    if (url === "/" || url === "/index.html") {
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end(html);
      return;
    }
    res.writeHead(404);
    res.end("no");
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const { port } = server.address();
  const BASE = `http://127.0.0.1:${port}`;

  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e?.message || e)));

  try {
    await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 45000 });
    // Alpine from CDN may need a beat; x_element upgrades custom elements
    await page.waitForTimeout(800);

    // ── Upgrade: custom elements defined + template cloned ──────────
    const upgrade = await page.evaluate(() => {
      const tags = [
        "x-login-form",
        "x-signup-form",
        "x-auth-shell",
        "x-profile-badge",
        "x-session-banner",
      ];
      const out = { defined: {}, hosts: {} };
      for (const t of tags) {
        out.defined[t] = !!customElements.get(t);
        const els = [...document.querySelectorAll(t)];
        out.hosts[t] = els.map((el) => ({
          children: el.childElementCount,
          shadow: !!el.shadowRoot,
          text: (el.innerText || el.shadowRoot?.innerText || "").trim().slice(0, 100),
        }));
      }
      out.ux_dom = !!(window.UxDom && window.UxDom.XElement);
      out.alpine = typeof window.Alpine !== "undefined";
      return out;
    });
    phases.upgrade = upgrade;
    if (!upgrade.ux_dom) fail("UxDom.XElement missing");
    for (const t of Object.keys(upgrade.defined)) {
      if (!upgrade.defined[t]) fail(`${t} not defined`);
      if (!upgrade.hosts[t]?.length) fail(`${t} host missing`);
    }
    // light login/signup must have cloned children
    for (const t of ["x-login-form", "x-signup-form", "x-profile-badge"]) {
      if (!(upgrade.hosts[t][0]?.children > 0)) fail(`${t} not upgraded (no children)`);
    }
    // shadow shell
    if (!upgrade.hosts["x-auth-shell"][0]?.shadow) fail("auth-shell missing shadowRoot");

    await page.screenshot({ path: join(SHOT, "01-auth-page.png"), fullPage: true });

    // ── Login validation via Alpine component API (authoritative state) ──
    const login = page.locator("x-login-form").first();

    async function loginCall(email, password) {
      return page.evaluate(
        async ({ email, password }) => {
          const root = document.querySelector("x-login-form [x-data]");
          if (!root || !window.Alpine) return { err: "no-alpine" };
          const data = window.Alpine.$data(root);
          data.email = email;
          data.password = password;
          data.login();
          if (window.Alpine.nextTick) await window.Alpine.nextTick();
          return { error: data.error, ok: data.ok, attempts: data.attempts };
        },
        { email, password }
      );
    }

    let st = await loginCall("", "");
    phases.loginEmpty = st;
    if (!/required/i.test(st.error || "")) fail(`login empty: ${JSON.stringify(st)}`);

    st = await loginCall("not-an-email", "password1");
    phases.loginBadEmail = st;
    if (!/invalid email/i.test(st.error || "")) fail(`login bad email: ${JSON.stringify(st)}`);

    st = await loginCall("a@b.co", "ab");
    phases.loginShortPw = st;
    if (!/short/i.test(st.error || "")) fail(`login short pw: ${JSON.stringify(st)}`);

    st = await loginCall("a@b.co", "secret");
    phases.loginOk = st;
    if (!st.ok) fail(`login success failed: ${JSON.stringify(st)}`);
    // DOM should reflect Alpine state
    await page.waitForTimeout(100);
    const loginOkDom = await login.locator('[data-testid="login-ok"]').evaluate((el) => ({
      text: (el.textContent || "").trim(),
      display: getComputedStyle(el).display,
      hidden: el.hasAttribute("hidden"),
    }));
    phases.loginOkDom = loginOkDom;
    if (!/signed in/i.test(loginOkDom.text)) fail(`login ok DOM text: ${JSON.stringify(loginOkDom)}`);
    if (loginOkDom.display === "none") fail(`login ok still display:none: ${JSON.stringify(loginOkDom)}`);
    await page.screenshot({ path: join(SHOT, "02-login-ok.png"), fullPage: true });

    // ── Signup validation via Alpine API ────────────────────────────
    const signup = page.locator("x-signup-form").first();
    async function signupCall(fields) {
      return page.evaluate(async (fields) => {
        const root = document.querySelector("x-signup-form [x-data]");
        const data = window.Alpine.$data(root);
        Object.assign(data, fields);
        data.signup();
        if (window.Alpine.nextTick) await window.Alpine.nextTick();
        return { error: data.error, ok: data.ok };
      }, fields);
    }
    let su = await signupCall({
      name: "Ada",
      email: "ada@lovelace.dev",
      password: "hunter2x",
      confirm: "hunter2y",
    });
    phases.signupMismatch = su;
    if (!/match/i.test(su.error || "")) fail(`signup mismatch: ${JSON.stringify(su)}`);

    su = await signupCall({
      name: "Ada",
      email: "ada@lovelace.dev",
      password: "hunter2x",
      confirm: "hunter2x",
    });
    phases.signupOk = su;
    if (!su.ok) fail(`signup success failed: ${JSON.stringify(su)}`);
    await page.waitForTimeout(100);
    const signupOkDom = await signup.locator('[data-testid="signup-ok"]').evaluate((el) => ({
      text: (el.textContent || "").trim(),
      display: getComputedStyle(el).display,
    }));
    phases.signupOkDom = signupOkDom;
    if (!/account created/i.test(signupOkDom.text)) fail(`signup ok DOM: ${JSON.stringify(signupOkDom)}`);
    if (signupOkDom.display === "none") fail(`signup ok still display:none`);
    await page.screenshot({ path: join(SHOT, "03-signup-ok.png"), fullPage: true });

    // ── Multi-instance: second login form independent state ─────────
    const login2 = page.locator("x-login-form").nth(1);
    if ((await login2.count()) > 0) {
      await login2.locator("#login-submit").click();
      await page.waitForTimeout(100);
      const e2 = await login2.locator('[data-testid="login-error"]').innerText();
      // first login still ok
      const stillOk = await login.locator('[data-testid="login-ok"]').isVisible();
      phases.multiLogin = { secondError: e2, firstStillOk: stillOk };
      if (!/required/i.test(e2)) fail(`second login empty: ${e2}`);
      if (!stillOk) fail("first login state leaked/cleared by second instance");
    } else {
      phases.multiLogin = { skipped: true };
    }

    // ── Profile badges multi-upgrade ────────────────────────────────
    const badges = await page.evaluate(() => {
      const els = [...document.querySelectorAll("x-profile-badge")];
      return {
        count: els.length,
        upgraded: els.filter((e) => e.childElementCount > 0).length,
        texts: els.slice(0, 3).map((e) => e.innerText.trim()),
      };
    });
    phases.badges = badges;
    if (badges.count < 3) fail(`expected multiple badges, got ${badges.count}`);
    if (badges.upgraded !== badges.count) fail("not all badges upgraded");

    // ── Shadow slot projection ──────────────────────────────────────
    const shell = await page.evaluate(() => {
      const el = document.querySelector("x-auth-shell");
      if (!el || !el.shadowRoot) return { ok: false, reason: !el ? "no-el" : "no-shadow" };
      const slots = [...el.shadowRoot.querySelectorAll("slot")].map((s) => ({
        name: s.name || "",
        assigned: s.assignedNodes().length,
      }));
      const shadowText = (el.shadowRoot.textContent || "").trim().slice(0, 80);
      return { ok: true, slots, shadowText };
    });
    phases.shell = shell;
    if (!shell.ok) fail("auth-shell shadow inspect failed");

    // ── Rescan after dynamic inject ─────────────────────────────────
    await page.evaluate(() => {
      const host = document.createElement("x-profile-badge");
      host.id = "dyn-badge";
      document.body.appendChild(host);
      if (window.UxDom?.XElement) UxDom.XElement.scan(document.body);
    });
    await page.waitForTimeout(200);
    const dyn = await page.evaluate(() => {
      const el = document.querySelector("#dyn-badge");
      return { exists: !!el, children: el?.childElementCount || 0 };
    });
    phases.dynamic = dyn;
    if (!(dyn.children > 0)) fail("dynamic x-profile-badge not upgraded after scan");

    for (const e of pageErrors) {
      // Alpine CDN noise filter
      if (!/favicon|cdn\.jsdelivr|alpinejs/i.test(e)) fail(`pageerror: ${e}`);
    }

    const report = {
      ok: fails.length === 0,
      fails,
      phases,
      pageErrors,
      screenshots: ["01-auth-page.png", "02-login-ok.png", "03-signup-ok.png"],
    };
    writeFileSync(join(SHOT, "auth-browser-report.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
    process.exit(report.ok ? 0 : 1);
  } catch (err) {
    fails.push(String(err?.message || err));
    const report = { ok: false, fails, phases, pageErrors };
    writeFileSync(join(SHOT, "auth-browser-report.json"), JSON.stringify(report, null, 2));
    console.error(JSON.stringify(report, null, 2));
    process.exit(1);
  } finally {
    await browser.close();
    server.close();
  }
}

await run();
