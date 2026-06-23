const fs = require("fs");
const path = require("path");

const outPath = path.join(__dirname, "rag_lead_flow.svg");
const width = 2600;
const height = 1900;
const nodes = {};
const lines = [];

function esc(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function wrapText(text, maxChars) {
  const explicit = String(text).split("\n");
  const lines = [];
  for (const part of explicit) {
    if (part.length <= maxChars) {
      lines.push(part);
      continue;
    }
    for (let i = 0; i < part.length; i += maxChars) {
      lines.push(part.slice(i, i + maxChars));
    }
  }
  return lines;
}

function textBlock(text, x, y, w, h, size = 26, weight = 400, color = "#1f2933", maxChars = 14) {
  const parts = wrapText(text, maxChars);
  const lineHeight = size * 1.32;
  const startY = y + h / 2 - ((parts.length - 1) * lineHeight) / 2;
  return parts
    .map((part, index) => {
      return `<text x="${x + w / 2}" y="${startY + index * lineHeight}" text-anchor="middle" dominant-baseline="middle" font-size="${size}" font-weight="${weight}" fill="${color}">${esc(part)}</text>`;
    })
    .join("\n");
}

function lane(title, x, y, w, h, fill, stroke) {
  lines.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="22" fill="${fill}" stroke="${stroke}" stroke-width="2"/>`);
  lines.push(`<text x="${x + 28}" y="${y + 42}" font-size="28" font-weight="700" fill="#203040">${esc(title)}</text>`);
}

function node(id, x, y, w, h, text, fill, stroke, kind = "rect") {
  nodes[id] = { x, y, w, h };
  if (kind === "diamond") {
    const pts = `${x + w / 2},${y} ${x + w},${y + h / 2} ${x + w / 2},${y + h} ${x},${y + h / 2}`;
    lines.push(`<polygon points="${pts}" fill="${fill}" stroke="${stroke}" stroke-width="3"/>`);
    lines.push(textBlock(text, x + 24, y + 12, w - 48, h - 24, 22, 700, "#1f2933", 13));
  } else {
    lines.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="16" fill="${fill}" stroke="${stroke}" stroke-width="3"/>`);
    lines.push(textBlock(text, x + 16, y + 10, w - 32, h - 20, 25, 400, "#1f2933", 15));
  }
}

function point(id, side) {
  const n = nodes[id];
  if (side === "right") return [n.x + n.w, n.y + n.h / 2];
  if (side === "left") return [n.x, n.y + n.h / 2];
  if (side === "top") return [n.x + n.w / 2, n.y];
  return [n.x + n.w / 2, n.y + n.h];
}

function edge(from, to, label = "", fromSide = "bottom", toSide = "top") {
  const [x1, y1] = point(from, fromSide);
  const [x2, y2] = point(to, toSide);
  lines.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#444" stroke-width="4" marker-end="url(#arrow)"/>`);
  if (label) {
    const mx = (x1 + x2) / 2;
    const my = (y1 + y2) / 2;
    const tw = Math.max(58, label.length * 18 + 24);
    lines.push(`<rect x="${mx - tw / 2}" y="${my - 19}" width="${tw}" height="38" rx="8" fill="#fff" stroke="#ddd"/>`);
    lines.push(`<text x="${mx}" y="${my + 1}" text-anchor="middle" dominant-baseline="middle" font-size="20" fill="#52616b">${esc(label)}</text>`);
  }
}

lines.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`);
lines.push(`<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M2,2 L10,6 L2,10 Z" fill="#444"/></marker></defs>`);
lines.push(`<rect width="100%" height="100%" fill="#ffffff"/>`);
lines.push(`<text x="${width / 2}" y="58" text-anchor="middle" font-family="Microsoft YaHei, SimHei, Arial" font-size="44" font-weight="700" fill="#1f2933">基于 RAG 的留资 Demo 全流程图</text>`);
lines.push(`<text x="${width / 2}" y="105" text-anchor="middle" font-family="Microsoft YaHei, SimHei, Arial" font-size="22" fill="#52616b">前端会话 → 后端状态机 → RAG 检索生成 → 留资入 CRM → 索引管理</text>`);
lines.push(`<g font-family="Microsoft YaHei, SimHei, Arial">`);

lane("前端交互", 70, 140, 520, 1580, "#EAF5FF", "#5B9EE6");
lane("后端会话状态机", 650, 140, 690, 1580, "#F5EEFF", "#9B72D0");
lane("RAG 检索与生成", 1400, 140, 720, 1200, "#ECF8F1", "#4EA66A");
lane("CRM / 索引管理", 2180, 140, 350, 1580, "#FFF7E6", "#D9A441");

node("user", 160, 220, 340, 78, "用户打开首页", "#FFFFFF", "#5B9EE6");
node("ui", 150, 340, 360, 96, "前端页面\nstatic/index.html + app.js", "#FFFFFF", "#5B9EE6");
node("reset", 150, 480, 360, 96, "初始化/重置会话\nPOST /api/sessions/{id}/reset", "#FFFFFF", "#5B9EE6");
node("render", 150, 1500, 360, 112, "渲染回复、状态、slots\n快捷回复、RAG 来源", "#FFFFFF", "#5B9EE6");
node("next", 170, 1660, 320, 60, "等待下一轮输入", "#FFFFFF", "#5B9EE6");

node("welcome", 790, 220, 400, 90, "welcome_response\n进入资格诊断", "#FFFFFF", "#9B72D0");
node("qualify", 790, 350, 400, 106, "资格诊断\neducation → goal → purpose", "#FFFFFF", "#9B72D0");
node("chat", 790, 500, 400, 88, "POST /api/chat\nsession_id + message", "#FFFFFF", "#9B72D0");
node("router", 790, 630, 400, 98, "handle_message\n状态机与意图路由", "#FFFFFF", "#9B72D0");
node("inPhone", 790, 780, 400, 118, "当前在\nlead_hook / phone_verify?", "#FFF5CC", "#B98518", "diamond");
node("direct", 770, 940, 440, 122, "强留资意图?\n费用/资格/最快拿证/老师联系", "#FFF5CC", "#B98518", "diamond");
node("needQual", 780, 1105, 420, 118, "资格诊断完成?", "#FFF5CC", "#B98518", "diamond");
node("free", 790, 1260, 400, 96, "自由问答处理\n问候/无关/业务问题", "#FFFFFF", "#9B72D0");
node("turns", 790, 1400, 400, 100, "业务问题\nqa_turns + 1", "#FFFFFF", "#9B72D0");
node("limit", 780, 1540, 420, 112, "问答轮次 ≥ 10?", "#FFF5CC", "#B98518", "diamond");
node("response", 975, 1690, 230, 72, "ChatResponse", "#FFFFFF", "#9B72D0");

node("phone", 2220, 235, 270, 96, "手机号步骤\n拒绝/校验/保存", "#FFFFFF", "#D9A441");
node("downgrade", 2220, 370, 270, 96, "拒绝手机号\n写 downgraded 线索", "#FFFFFF", "#D9A441");
node("full", 2220, 500, 270, 96, "手机号有效\n写 full 线索", "#FFFFFF", "#D9A441");
node("crm", 2220, 630, 270, 82, "InMemoryCrm.leads", "#FFFFFF", "#D9A441");
node("crmApi", 2220, 745, 270, 78, "GET /api/crm/leads\n查看线索", "#FFFFFF", "#D9A441");
node("hook", 2220, 895, 270, 108, "lead_hook\n解释需老师规划\n请求手机号", "#FFFFFF", "#D9A441");
node("collect", 2220, 1045, 270, 100, "补齐诊断 slots\n继续快捷提问", "#FFFFFF", "#D9A441");

node("ragEntry", 1575, 1280, 360, 86, "调用 RAG 回答\n_answer_user_need", "#FFFFFF", "#4EA66A");
node("keyword", 1485, 420, 250, 92, "BM25\n关键词检索", "#FFFFFF", "#4EA66A");
node("vector", 1785, 420, 250, 92, "可选向量检索\nVectorIndex.search", "#FFFFFF", "#4EA66A");
node("fuse", 1575, 560, 360, 82, "RRF 融合结果", "#FFFFFF", "#4EA66A");
node("rerank", 1575, 685, 360, 82, "轻量重排\nTop 5", "#FFFFFF", "#4EA66A");
node("conf", 1575, 810, 360, 112, "置信度与实体覆盖\n是否通过?", "#FFF5CC", "#B98518", "diamond");
node("gen", 1575, 965, 360, 112, "Top 3 来源\nQwen 生成或抽取式 fallback", "#FFFFFF", "#4EA66A");
node("compress", 1575, 1120, 360, 90, "必要时压缩/截断\n拼接来源与软引导", "#FFFFFF", "#4EA66A");
node("fallback", 1575, 1465, 360, 96, "未命中/置信不足\n软性引导留资", "#FFECEC", "#D64545");

node("status", 2220, 1195, 270, 78, "GET /api/rag/status", "#FFFFFF", "#D9A441");
node("rebuild", 2220, 1310, 270, 92, "POST /api/rag/rebuild\n重建向量索引", "#FFFFFF", "#D9A441");
node("enabled", 2220, 1440, 270, 108, "RAG_EMBEDDING_ENABLED\n=true?", "#FFF5CC", "#B98518", "diamond");
node("cache", 2220, 1595, 270, 96, "读取 chunks.jsonl\n写 vector_index.json", "#FFFFFF", "#D9A441");

edge("user", "ui");
edge("ui", "reset");
edge("reset", "welcome", "", "right", "left");
edge("welcome", "qualify");
edge("qualify", "chat");
edge("chat", "router");
edge("router", "inPhone");
edge("inPhone", "phone", "是", "right", "left");
edge("phone", "downgrade", "拒绝");
edge("phone", "full", "有效");
edge("downgrade", "crm");
edge("full", "crm");
edge("crm", "crmApi");
edge("downgrade", "response", "", "left", "right");
edge("full", "response", "", "left", "right");
edge("inPhone", "direct", "否");
edge("direct", "hook", "是", "right", "left");
edge("hook", "response", "", "left", "right");
edge("direct", "needQual", "否");
edge("needQual", "collect", "否", "right", "left");
edge("collect", "response", "", "left", "right");
edge("needQual", "free", "是");
edge("free", "turns");
edge("turns", "limit");
edge("limit", "hook", "是", "right", "left");
edge("limit", "ragEntry", "否", "right", "left");
edge("ragEntry", "keyword", "", "top", "bottom");
edge("ragEntry", "vector", "可选", "top", "bottom");
edge("keyword", "fuse");
edge("vector", "fuse");
edge("fuse", "rerank");
edge("rerank", "conf");
edge("conf", "fallback", "否");
edge("conf", "gen", "是");
edge("gen", "compress");
edge("compress", "response", "", "left", "right");
edge("fallback", "response", "", "left", "right");
edge("response", "render", "", "left", "right");
edge("render", "next");
edge("next", "chat", "", "right", "left");
edge("ui", "status", "状态查询", "right", "left");
edge("ui", "rebuild", "点击重建", "right", "left");
edge("rebuild", "enabled");
edge("enabled", "cache", "是");
edge("cache", "ragEntry", "刷新服务", "left", "right");

lines.push(`<text x="90" y="1785" font-size="22" fill="#52616b">图例：蓝色=前端交互，紫色=后端状态机，绿色=RAG，黄色=CRM/索引管理，红色=未命中或需用户修正。</text>`);
lines.push(`<text x="90" y="1830" font-size="22" fill="#52616b">核心转化逻辑：普通政策问题先用 RAG 建立信任；费用、资格、最快拿证、人工老师等高意向问题转入 lead_hook；手机号有效写 full 线索，拒绝则写 downgraded 线索。</text>`);
lines.push(`</g></svg>`);

fs.writeFileSync(outPath, lines.join("\n"), "utf8");
console.log(outPath);
