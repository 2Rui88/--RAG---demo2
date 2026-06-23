const sessionId = crypto.randomUUID();
const messagesEl = document.querySelector("#messages");
const quickRepliesEl = document.querySelector("#quickReplies");
const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const resetButton = document.querySelector("#resetButton");
const rebuildRagButton = document.querySelector("#rebuildRagButton");
const stateText = document.querySelector("#stateText");
const leadText = document.querySelector("#leadText");
const ragStatus = document.querySelector("#ragStatus");

const slotEls = {
  education: document.querySelector("#slotEducation"),
  goal: document.querySelector("#slotGoal"),
  purpose: document.querySelector("#slotPurpose"),
  phone: document.querySelector("#slotPhone"),
  crmLead: document.querySelector("#slotCrmLead"),
};
let sending = false;

const stateLabels = {
  welcome: "欢迎",
  qualification: "资质诊断",
  intent_router: "意图识别",
  lead_hook: "留资钩子",
  phone_verify: "手机号校验",
  success: "留资成功",
};

function addMessage(role, text, sources = []) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  const body = document.createElement("div");
  body.textContent = text;
  node.appendChild(body);
  if (sources.length > 0) {
    node.appendChild(renderRagSources(sources));
  }
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderRagSources(sources) {
  const panel = document.createElement("details");
  panel.className = "rag-sources";
  const summary = document.createElement("summary");
  summary.textContent = `命中资料 top ${sources.length}`;
  panel.appendChild(summary);

  const list = document.createElement("ol");
  for (const source of sources) {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = source.source_title || "未命名文件";
    const meta = document.createElement("span");
    const score = Number(source.score ?? 0).toFixed(4);
    meta.textContent = `得分 ${score}`;
    item.append(title, meta);
    list.appendChild(item);
  }
  panel.appendChild(list);
  return panel;
}

function renderQuickReplies(items) {
  quickRepliesEl.innerHTML = "";
  for (const item of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item;
    button.addEventListener("click", () => sendMessage(item));
    quickRepliesEl.appendChild(button);
  }
}

function renderMeta(payload) {
  stateText.textContent = stateLabels[payload.state] ?? payload.state;
  leadText.textContent = payload.lead_saved ? "已留资" : payload.lead_required ? "待留资" : "未触发";
  slotEls.education.textContent = payload.slots.education ?? "未填写";
  slotEls.goal.textContent = payload.slots.goal ?? "未填写";
  slotEls.purpose.textContent = payload.slots.purpose ?? "未填写";
  slotEls.phone.textContent = payload.slots.phone ?? "未留资";
  slotEls.crmLead.textContent = payload.slots.crm_lead_id ?? "未写入";
  renderQuickReplies(payload.quick_replies ?? []);
}

async function sendMessage(text) {
  if (sending) return;
  const message = text.trim();
  if (!message) return;

  sending = true;
  input.disabled = true;
  addMessage("user", message);
  input.value = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    if (!response.ok) {
      addMessage("bot", "服务暂时不可用，请稍后再试。");
      return;
    }

    const payload = await response.json();
    addMessage("bot", payload.reply, payload.used_rag ? payload.rag_sources ?? [] : []);
    renderMeta(payload);
  } finally {
    sending = false;
    input.disabled = false;
    input.focus();
  }
}

async function resetSession() {
  const response = await fetch(`/api/sessions/${sessionId}/reset`, { method: "POST" });
  const payload = await response.json();
  messagesEl.innerHTML = "";
  addMessage("bot", payload.reply);
  renderMeta(payload);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(input.value);
});

resetButton.addEventListener("click", resetSession);

async function refreshRagStatus() {
  const response = await fetch("/api/rag/status");
  if (!response.ok) {
    ragStatus.textContent = "索引状态读取失败";
    return;
  }
  const payload = await response.json();
  const vectorText = payload.vector_cache_exists ? "向量缓存已存在" : "未生成向量缓存";
  const enabledText = payload.embedding_enabled ? "可重建" : "未启用重建";
  ragStatus.textContent = `${vectorText}，${enabledText}`;
}

async function rebuildRagIndex() {
  rebuildRagButton.disabled = true;
  rebuildRagButton.textContent = "重建中";
  ragStatus.textContent = "正在重建向量索引";
  try {
    const response = await fetch("/api/rag/rebuild", { method: "POST" });
    const payload = await response.json();
    ragStatus.textContent = payload.message;
  } catch (error) {
    ragStatus.textContent = "重建失败，请检查服务日志";
  } finally {
    rebuildRagButton.disabled = false;
    rebuildRagButton.textContent = "重建向量索引";
  }
}

rebuildRagButton.addEventListener("click", rebuildRagIndex);

resetSession();
refreshRagStatus();
