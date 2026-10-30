import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url)) + "\\..";
const url = "http://127.0.0.1:8767/";
const outputDir = path.join(root, "tmp", "qa");
fs.mkdirSync(outputDir, { recursive: true });

const chromePath = [
  process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].find((candidate) => candidate && fs.existsSync(candidate));
if (!chromePath) throw new Error("Chrome or Edge was not found.");

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function get(target) {
  return new Promise((resolve, reject) => {
    const request = http.get(target, (response) => {
      let data = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => {
        data += chunk;
      });
      response.on("end", () => resolve({ statusCode: response.statusCode, data }));
    });
    request.setTimeout(2_000, () => request.destroy(new Error("timeout")));
    request.on("error", reject);
  });
}

async function waitFor(target) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await get(target);
      if (response.statusCode >= 200 && response.statusCode < 300) return;
    } catch {
      // Wait for the server or browser to start.
    }
    await sleep(100);
  }
  throw new Error(`Timed out waiting for ${target}`);
}

class Cdp {
  constructor(socket) {
    this.socket = socket;
    this.id = 0;
    this.pending = new Map();
    this.events = new Map();
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const pending = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(message.error.message));
        else pending.resolve(message.result);
        return;
      }
      (this.events.get(message.method) || []).forEach((handler) => handler(message.params));
    });
  }

  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  on(event, handler) {
    const handlers = this.events.get(event) || [];
    handlers.push(handler);
    this.events.set(event, handlers);
  }
}

const server = spawn("python", ["-m", "http.server", "8767", "--bind", "127.0.0.1"], {
  cwd: root,
  stdio: "ignore",
  windowsHide: true,
});
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "l1-portfolio-qa-"));
const chrome = spawn(
  chromePath,
  [
    "--headless=new",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--no-first-run",
    "--remote-debugging-port=9225",
    `--user-data-dir=${profile}`,
    url,
  ],
  { stdio: "ignore", windowsHide: true },
);

let socket;
try {
  await waitFor(url);
  await waitFor("http://127.0.0.1:9225/json/version");
  const targets = JSON.parse((await get("http://127.0.0.1:9225/json/list")).data);
  const page = targets.find((target) => target.type === "page");
  socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });

  const cdp = new Cdp(socket);
  const errors = [];
  cdp.on("Runtime.exceptionThrown", (event) => errors.push(event.exceptionDetails.text));
  cdp.on("Log.entryAdded", (event) => {
    if (event.entry.level === "error") errors.push(event.entry.text);
  });
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Log.enable");

  const reports = [];
  for (const viewport of [
    { name: "desktop", width: 1440, height: 1000, mobile: false },
    { name: "laptop", width: 1024, height: 900, mobile: false },
    { name: "tablet", width: 768, height: 900, mobile: true },
    { name: "mobile", width: 390, height: 844, mobile: true },
  ]) {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: 1,
      mobile: viewport.mobile,
    });
    await cdp.send("Page.navigate", { url });
    await sleep(850);
    const result = await cdp.send("Runtime.evaluate", {
      returnByValue: true,
      expression: `(() => {
        const ids = new Set([...document.querySelectorAll("[id]")].map((node) => node.id));
        return {
          title: document.title,
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          brokenImages: [...document.images]
            .filter((image) => !image.complete || image.naturalWidth === 0)
            .map((image) => image.getAttribute("src")),
          missingAnchors: [...document.querySelectorAll('a[href^="#"]')]
            .filter((anchor) => anchor.hash && !ids.has(anchor.hash.slice(1)))
            .map((anchor) => anchor.getAttribute("href")),
          missingResults: [...document.querySelectorAll("[data-result], [data-weight], [data-risk], [data-contribution]")]
            .filter((node) => node.textContent.trim() === "—")
            .map((node) => node.dataset.result || node.dataset.weight || node.dataset.risk || node.dataset.contribution),
          h1Count: document.querySelectorAll("h1").length,
          sectionCount: document.querySelectorAll("main section[id]").length,
        };
      })()`,
    });
    const metrics = result.result.value;
    if (metrics.scrollWidth > metrics.clientWidth + 1) throw new Error(`${viewport.name}: horizontal overflow`);
    if (metrics.brokenImages.length) throw new Error(`${viewport.name}: broken images`);
    if (metrics.missingAnchors.length) throw new Error(`${viewport.name}: missing anchors`);
    if (metrics.missingResults.length) {
      throw new Error(`${viewport.name}: unresolved results: ${metrics.missingResults.join(", ")}`);
    }
    if (metrics.h1Count !== 1 || metrics.sectionCount !== 10) throw new Error(`${viewport.name}: bad heading or section count`);

    if (viewport.name === "mobile") {
      const menu = await cdp.send("Runtime.evaluate", {
        returnByValue: true,
        awaitPromise: true,
        expression: `(async () => {
          const button = document.querySelector("#menu-button");
          button.click();
          await new Promise((resolve) => setTimeout(resolve, 280));
          const open = document.body.classList.contains("nav-open");
          button.click();
          await new Promise((resolve) => setTimeout(resolve, 280));
          return { open, closed: !document.body.classList.contains("nav-open") };
        })()`,
      });
      if (!menu.result.value.open || !menu.result.value.closed) throw new Error("mobile navigation failed");
    }

    const screenshot = await cdp.send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: false,
    });
    const screenshotPath = path.join(outputDir, `${viewport.name}.png`);
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    reports.push({ viewport, metrics, screenshotPath });
  }

  if (errors.length) throw new Error(`Browser errors: ${errors.join(" | ")}`);
  console.log(JSON.stringify(reports, null, 2));
} finally {
  socket?.close();
  chrome.kill();
  server.kill();
}
