## 总体架构
```mermaid
flowchart TD
  A["浏览器 static 页面"] --> B["/api/chat"]
  B --> C["FastAPI app/main.py"]
  C --> D["ConversationEngine 状态机"]
  D --> E{"是否需要 RAG"}
  E -- 否 --> F["固定话术 / 留资钩子 / 手机校验"]
  E -- 是 --> G["RagService 检索知识库"]
  G --> H["返回答案 + top5 来源"]
  F --> I["前端渲染回复和状态"]
  H --> I
  F --> J{"手机号有效?"}
  J -- 是 --> K["InMemoryCrm 写入线索"]
```

## 主要流程
```mermaid
flowchart TD
  A["进入页面"] --> B["qualification: 问最高学历"]
  B --> C["收集 education"]
  C --> D["收集 goal"]
  D --> E["收集 purpose"]
  E --> F["intent_router: 意图识别"]
  F --> G{"用户问题类型"}
  G -- "你好/寒暄" --> H["直接回复主线引导，不走 RAG"]
  G -- "多少钱/能不能报/最快拿证" --> I["直接进入 钩子"]
  G -- "怎么报名" --> J["走 RAG，追加软钩子，不进入 钩子"]
  G -- "普通政策问题" --> K["走 RAG"]
  G -- "RAG 无依据" --> L["兜底话术，设置 pending_soft_lead"]
  L -- "用户说 好/可以/同意" --> M["手机号码验证"]
  I --> M
  M -- "有效手机号" --> N["success + 写入 CRM"]
  M -- "稍后再说" --> O["留资兜底"]
```
<img width="1180" height="2480" alt="image" src="https://github.com/user-attachments/assets/ccc8f99d-cec2-4a55-8f6f-955222b3b0ca" />

```mermaid
flowchart TD
    A["用户输入"] --> B["/api/chat"]
    B --> C["ConversationEngine"]

    C --> D{"当前是否在留资/手机校验?"}
    D -- "是" --> E["手机号校验 / 拒绝留资处理"]
    E --> F{"手机号有效或拒绝?"}
    F -- "有效" --> G["写入 CRM: full lead"]
    F -- "拒绝" --> H["写入 CRM: downgraded lead"]
    G --> Z["返回回复"]
    H --> Z

    D -- "否" --> I["Intent Router"]
    I --> J{"是否 lead / human_service?"}
    J -- "是" --> K["留资钩子"]
    K --> Z

    J -- "否" --> L{"是否处于画像采集阶段?"}
    L -- "是" --> M["Slot Filling"]
    M --> N{"education / goal / purpose 是否齐全?"}
    N -- "否" --> O["追问缺失槽位"]
    O --> Z
    N -- "是" --> P["进入咨询阶段"]
    P --> Z

    L -- "否" --> Q{"意图类型"}
    Q -- "small_talk" --> R["Small Talk 模板回复"]
    R --> Z

    Q -- "rag / faq" --> S["读取最近历史"]
    S --> T["Query Rewrite"]
    T --> U["RAG Retriever"]
    U --> V{"是否命中可靠依据?"}
    V -- "是" --> W["Answer Builder / LLM 生成或兜底摘要"]
    W --> X["返回答案 + 来源"]
    X --> Z

    V -- "否" --> Y["知识库无依据兜底 + pending_soft_lead"]
    Y --> Z
```





# 部署运行说明

## 1. 环境

- Python 3.10+
- 项目根目录执行命令

## 2. 安装

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 3. 配置

本地无 API Key 也能跑。将 `.env` 设置为：

```env
QWEN_API_KEY=
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.5-flash
LLM_ENABLED=false
RAG_EMBEDDING_ENABLED=false
```

如需启用 Qwen 和向量检索：

```env
QWEN_API_KEY=你的DashScope_API_Key
LLM_ENABLED=true
RAG_EMBEDDING_ENABLED=true
```

修改 `.env` 后需要重启服务。

## 4. 启动

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

访问：

- 页面：http://127.0.0.1:8000/
- 健康检查：http://127.0.0.1:8000/health
- API 文档：http://127.0.0.1:8000/docs

服务器部署可用：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 5. 验证

```bash
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{"status":"ok"}
```

运行测试：

```bash
python -m pytest
```

## 6. RAG 数据

服务默认读取：

```text
data/rag/chunks.jsonl
```

如需重新生成 RAG 数据：

```bash
python -m app.rag.build_curated_knowledge --source data/source_crgk_text_documents --output data/rag
```

如需重建向量索引，先设置 `QWEN_API_KEY` 和 `RAG_EMBEDDING_ENABLED=true`，启动服务后执行：

```bash
curl -X POST http://127.0.0.1:8000/api/rag/rebuild
```

## 7. 常见问题

- 端口被占用：把 `--port 8000` 改成其他端口。
- PowerShell 无法激活虚拟环境：先执行 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`。
- 无 API Key：设置 `LLM_ENABLED=false`、`RAG_EMBEDDING_ENABLED=false`。
- CRM 数据保存在内存中，服务重启后会清空。
