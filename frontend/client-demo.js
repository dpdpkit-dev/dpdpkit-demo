// Drives @dpdpkit/client against the dpdpkit-fastapi backend on this site (see app/fastapi_demo.py) and prints
// each request and response. The client takes a custom `fetch`, so the wrapper below sees every call it makes.
import { createDpdpClient, DpdpError } from "@dpdpkit/client";

const root = document.getElementById("client-demo");
const userSelect = document.getElementById("client-user");
const log = document.getElementById("client-log");
const buttons = document.getElementById("client-calls");

async function loggingFetch(url, init = {}) {
  const entry = document.createElement("details");
  entry.open = true;
  const method = init.method || "GET";
  const requestText = [`${method} ${url}`, ...Object.entries(init.headers || {}).map(([k, v]) => `${k}: ${v}`)];
  if (init.body) requestText.push("", pretty(init.body));
  entry.append(summary(`${method} ${url}`), block("Request", requestText.join("\n")));
  log.prepend(entry);
  const response = await fetch(url, init);
  const body = await response.clone().text();
  entry.querySelector("summary").textContent += ` → ${response.status}`;
  entry.append(block("Response", `${response.status} ${response.statusText}\n\n${pretty(body)}`));
  return response;
}

function pretty(text) {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return String(text);
  }
}

function summary(text) {
  const s = document.createElement("summary");
  s.textContent = text;
  return s;
}

function block(title, text) {
  const wrap = document.createElement("div");
  const h = document.createElement("strong");
  h.textContent = title;
  const pre = document.createElement("pre");
  pre.textContent = text;
  wrap.append(h, pre);
  return wrap;
}

// Each button is the one line of client code it runs, shown on the button and executed.
const calls = {
  "client.getNotice('en')": (c) => c.getNotice("en"),
  "client.myConsents()": (c) => c.myConsents(),
  "client.recordConsents([{ purpose: 'marketing', granted: true }])": (c) =>
    c.recordConsents([{ purpose: "marketing", granted: true }]),
  "client.withdraw('marketing')": (c) => c.withdraw("marketing"),
  "client.receipt()": (c) => c.receipt(),
  "client.openRequest('access')": (c) => c.openRequest("access"),
  "client.myRequests()": (c) => c.myRequests(),
  "client.exportMyData()": (c) => c.exportMyData(),
};

for (const [label, run] of Object.entries(calls)) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.onclick = async () => {
    // Built per click so the chosen person goes out in X-User, standing in for a login.
    const client = createDpdpClient({
      baseUrl: root.dataset.baseUrl,
      headers: { "X-User": userSelect.value },
      fetch: loggingFetch,
    });
    try {
      await run(client);
    } catch (error) {
      const text = error instanceof DpdpError ? `DpdpError ${error.status} ${error.code}: ${error.message}` : String(error);
      log.firstElementChild?.append(block("Thrown by the client", text));
    }
  };
  buttons.append(button, " ");
}

document.getElementById("client-clear").onclick = () => log.replaceChildren();
