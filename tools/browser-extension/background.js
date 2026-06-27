/**
 * Engine GCU Chrome extension — WebSocket bridge to Python BeelineBridge.
 *
 * Protocol: Python sends {id, type, ...params}; extension replies {id, result} or {id, error}.
 * Unsolicited: {type: "hello"} on connect; {type: "cdp_event", tabId, method, params} for CDP events.
 */

const BRIDGE_URL = "ws://127.0.0.1:9229";
const EXT_VERSION = "1.0.0";

const FORWARDED_CDP_EVENTS = new Set([
  "Runtime.consoleAPICalled",
  "Page.frameNavigated",
  "Page.frameResized",
  "Page.lifecycleEvent",
  "Target.targetInfoChanged",
]);

let ws = null;
let reconnectTimer = null;
const attachedTabs = new Set();
const tabGroups = new Map(); // agentId -> groupId

function send(msg) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }
  ws = new WebSocket(BRIDGE_URL);
  ws.onopen = () => {
    send({ type: "hello", version: EXT_VERSION });
  };
  ws.onclose = () => {
    ws = null;
    reconnectTimer = setTimeout(connect, 2000);
  };
  ws.onerror = () => {
    ws?.close();
  };
  ws.onmessage = (ev) => {
    let msg;
    try {
      msg = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (msg.id) {
      handleCommand(msg).catch((err) => {
        send({ id: msg.id, error: String(err) });
      });
    }
  };
}

async function handleCommand(msg) {
  const { id, type } = msg;
  try {
    let result = {};
    switch (type) {
      case "context.create":
        result = await createContext(msg.agentId || "default");
        break;
      case "context.destroy":
        result = await destroyContext(msg.groupId);
        break;
      case "tab.create":
        result = await createTab(msg.url || "about:blank", msg.groupId);
        break;
      case "tab.close":
        result = await closeTab(msg.tabId);
        break;
      case "tab.list":
        result = await listTabs(msg.groupId);
        break;
      case "tab.activate":
        result = await activateTab(msg.tabId);
        break;
      case "cdp.attach":
        result = await cdpAttach(msg.tabId);
        break;
      case "cdp.detach":
        result = await cdpDetach(msg.tabId);
        break;
      case "cdp":
        result = await cdpSend(msg.tabId, msg.method, msg.params || {});
        break;
      default:
        throw new Error(`Unknown command type: ${type}`);
    }
    send({ id, result });
  } catch (err) {
    send({ id, error: String(err) });
  }
}

async function createContext(agentId) {
  const tab = await chrome.tabs.create({ url: "about:blank", active: true });
  const groupId = await chrome.tabs.group({ tabIds: [tab.id] });
  await chrome.tabGroups.update(groupId, { title: `Engine: ${agentId}`, collapsed: false });
  tabGroups.set(agentId, groupId);
  return { groupId, tabId: tab.id };
}

async function destroyContext(groupId) {
  const tabs = await chrome.tabs.query({ groupId });
  let closedTabs = 0;
  for (const tab of tabs) {
    if (tab.id != null) {
      await cdpDetach(tab.id).catch(() => {});
      await chrome.tabs.remove(tab.id);
      closedTabs += 1;
    }
  }
  try {
    await chrome.tabGroups.update(groupId, { collapsed: true });
  } catch {
    /* group may already be gone */
  }
  return { ok: true, closedTabs };
}

async function createTab(url, groupId) {
  const tab = await chrome.tabs.create({ url, active: true });
  if (groupId != null) {
    await chrome.tabs.group({ tabIds: [tab.id], groupId });
  }
  return { tabId: tab.id };
}

async function closeTab(tabId) {
  await cdpDetach(tabId).catch(() => {});
  await chrome.tabs.remove(tabId);
  return { ok: true };
}

async function listTabs(groupId) {
  const query = groupId != null ? { groupId } : {};
  const tabs = await chrome.tabs.query(query);
  return {
    tabs: tabs.map((t) => ({
      id: t.id,
      url: t.url,
      title: t.title,
      groupId: t.groupId,
    })),
  };
}

async function activateTab(tabId) {
  await chrome.tabs.update(tabId, { active: true });
  const tab = await chrome.tabs.get(tabId);
  if (tab.windowId != null) {
    await chrome.windows.update(tab.windowId, { focused: true });
  }
  return { ok: true };
}

async function cdpAttach(tabId) {
  if (attachedTabs.has(tabId)) {
    return { ok: true, attached: false, message: "Already attached" };
  }
  await chrome.debugger.attach({ tabId }, "1.3");
  attachedTabs.add(tabId);
  chrome.debugger.onEvent.addListener(onCdpEvent);
  await chrome.debugger.sendCommand({ tabId }, "Runtime.enable", {});
  await chrome.debugger.sendCommand({ tabId }, "Page.enable", {});
  try {
    await chrome.debugger.sendCommand({ tabId }, "Page.setLifecycleEventsEnabled", {
      enabled: true,
    });
  } catch {
    /* optional */
  }
  return { ok: true, attached: true };
}

async function cdpDetach(tabId) {
  if (!attachedTabs.has(tabId)) {
    return { ok: true };
  }
  try {
    await chrome.debugger.detach({ tabId });
  } catch {
    /* already detached */
  }
  attachedTabs.delete(tabId);
  return { ok: true };
}

async function cdpSend(tabId, method, params) {
  if (!attachedTabs.has(tabId)) {
    await cdpAttach(tabId);
  }
  const result = await chrome.debugger.sendCommand({ tabId }, method, params);
  return { result };
}

function onCdpEvent(source, method, params) {
  if (!FORWARDED_CDP_EVENTS.has(method)) {
    return;
  }
  send({
    type: "cdp_event",
    tabId: source.tabId,
    method,
    params: params || {},
  });
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "status") {
    sendResponse({ connected: ws != null && ws.readyState === WebSocket.OPEN });
    return true;
  }
  return false;
});

connect();
