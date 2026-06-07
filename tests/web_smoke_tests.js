const assert = require("assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const root = path.resolve(__dirname, "..");
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const appSource = fs.readFileSync(path.join(root, "docs/public/webserver/app.js"), "utf8");

if (!fs.existsSync(chromePath)) {
  throw new Error("Google Chrome is required for browser smoke tests");
}

function browserScriptForScenario(scenario) {
  return `
    window.__smoke = { posts: [], errors: [], downloads: 0, inputClicks: 0 };
    window.addEventListener("error", function (event) {
      window.__smoke.errors.push(event.message || "browser error");
    });
    window.addEventListener("unhandledrejection", function (event) {
      window.__smoke.errors.push(String(event.reason || "unhandled rejection"));
    });

    HTMLAnchorElement.prototype.click = function () {
      if (this.download) window.__smoke.downloads += 1;
    };
    HTMLInputElement.prototype.click = function () {
      if (this.type === "file") window.__smoke.inputClicks += 1;
    };

    class SmokeEventSource {
      constructor(url) {
        this.url = url;
        this.listeners = {};
        setTimeout(() => {
          if (this.onopen) this.onopen({ type: "open" });
          this.dispatch("log", { msg: "Smoke log line", lvl: 3 });
        }, 25);
      }
      addEventListener(type, listener) {
        if (!this.listeners[type]) this.listeners[type] = [];
        this.listeners[type].push(listener);
      }
      dispatch(type, data) {
        (this.listeners[type] || []).forEach((listener) => {
          listener({ data: JSON.stringify(data) });
        });
      }
      close() {}
    }
    window.EventSource = SmokeEventSource;

    const configured = ${JSON.stringify(scenario === "settings")};
    const endpointValues = {
      "Connection: Server URL": configured ? "https://photos.example.com" : "",
      "Connection: API Key": configured ? "fixture-api-key" : "",
      "Photos: Source": "Album",
      "Photos: Album IDs": "11111111-1111-4111-8111-111111111111",
      "Photos: Album Labels": "Family",
      "Photos: Person IDs": "",
      "Photos: Person Labels": "",
      "Photos: Display Mode": "Fill",
      "Photos: Slideshow Interval": "15 seconds",
      "Screen: Connection Timeout": "10 minutes",
      "Clock: Format": "24 Hour",
      "Clock: Timezone": "Europe/London (GMT+0)",
      "Firmware: Manifest URL": "",
      "Firmware: Beta Manifest URL": ""
    };

    window.fetch = function (url, options) {
      const method = options && options.method ? options.method : "GET";
      if (method === "POST") window.__smoke.posts.push(String(url));
      const decoded = decodeURIComponent(String(url));
      let value = "";
      Object.keys(endpointValues).forEach((name) => {
        if (decoded.indexOf(name) !== -1) value = endpointValues[name];
      });
      const state = value === true ? "ON" : value === false ? "OFF" : String(value);
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ value, state, option: [] })
      });
    };
  `;
}

function smokeAssertionsForScenario(scenario) {
  return `
    (async function () {
      function waitFor(check, timeoutMs) {
        const started = Date.now();
        return new Promise((resolve, reject) => {
          function poll() {
            try {
              if (check()) return resolve();
            } catch (error) {
              return reject(error);
            }
            if (Date.now() - started > timeoutMs) return reject(new Error("Timed out waiting for " + ${JSON.stringify(scenario)}));
            setTimeout(poll, 50);
          }
          poll();
        });
      }
      function pageText() {
        return document.body.innerText || "";
      }
      function requireText(text) {
        if (pageText().indexOf(text) === -1) throw new Error("Missing text: " + text);
      }
      function buttonByText(text) {
        return Array.from(document.querySelectorAll("button")).find((button) => button.textContent.trim() === text);
      }

      try {
        if (${JSON.stringify(scenario)} === "wizard") {
          await waitFor(() => pageText().indexOf("connect your photo frame") !== -1, 8000);
          requireText("Immich Server URL");
          requireText("API Key");
          requireText("Import Settings");
        } else {
          await waitFor(() => pageText().indexOf("Photo Source") !== -1, 8000);
          requireText("Immich Server URL");
          requireText("Photo Source");
          requireText("Add an album");
          requireText("Add a person");
          requireText("Export");
          requireText("Import");
          const exportButton = buttonByText("Export");
          const importButton = buttonByText("Import");
          if (!exportButton) throw new Error("Export button not found");
          if (!importButton) throw new Error("Import button not found");
          exportButton.click();
          importButton.click();
          if (window.__smoke.downloads !== 1) throw new Error("Export did not trigger a download");
          if (window.__smoke.inputClicks !== 1) throw new Error("Import did not open the file picker");
          const logsTab = Array.from(document.querySelectorAll(".sp-tab")).find((tab) => tab.textContent.trim() === "Logs");
          if (logsTab) logsTab.click();
          requireText("Clear");
        }
        if (window.__smoke.errors.length) throw new Error(window.__smoke.errors.join("; "));
        document.documentElement.setAttribute("data-smoke-${scenario}", "pass");
        document.body.appendChild(document.createTextNode(" ESPFRAME_BROWSER_SMOKE_${scenario.toUpperCase()}_PASS "));
      } catch (error) {
        document.documentElement.setAttribute("data-smoke-${scenario}", "fail");
        const pre = document.createElement("pre");
        pre.id = "smoke-error-${scenario}";
        pre.textContent = error && error.stack ? error.stack : String(error);
        document.body.appendChild(pre);
      }
    })();
  `;
}

function htmlForScenario(scenario) {
  const escapedAppSource = appSource.replace(/<\/script/gi, "<\\/script");
  return `<!doctype html>
<html>
<head><meta charset="utf-8"><title>Espframe web smoke ${scenario}</title></head>
<body><esp-app></esp-app>
<script>${browserScriptForScenario(scenario)}</script>
<script>${escapedAppSource}</script>
<script>${smokeAssertionsForScenario(scenario)}</script>
</body>
</html>`;
}

function runScenario(scenario) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "espframe-web-smoke-"));
  const htmlPath = path.join(tempDir, `${scenario}.html`);
  const userDataDir = path.join(tempDir, "chrome-profile");
  fs.writeFileSync(htmlPath, htmlForScenario(scenario));
  const result = spawnSync(
    chromePath,
    [
      "--headless=new",
      "--disable-gpu",
      "--no-first-run",
      "--no-default-browser-check",
      `--user-data-dir=${userDataDir}`,
      "--virtual-time-budget=10000",
      "--dump-dom",
      `file://${htmlPath}`,
    ],
    { encoding: "utf8", timeout: 20000 }
  );

  const output = `${result.stdout || ""}\n${result.stderr || ""}`;
  assert.equal(result.status, 0, `Chrome failed for ${scenario}:\n${output}`);
  assert.ok(
    output.includes(`ESPFRAME_BROWSER_SMOKE_${scenario.toUpperCase()}_PASS`),
    `Browser smoke scenario ${scenario} failed:\n${output}`
  );
}

runScenario("wizard");
runScenario("settings");

console.log("web browser smoke tests passed");
