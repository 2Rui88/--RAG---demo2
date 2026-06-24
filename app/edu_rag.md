# 学历提升智能客服系统优化方案（Phase 1）

## 项目目标

当前系统已具备：

* 用户画像采集
* RAG知识库问答
* 留资流程
* CRM线索管理

当前架构：

```text
用户
 ↓
状态机
 ↓
关键词判断
 ↓
RAG
 ↓
留资
 ↓
CRM
```

Phase 1 优化目标：

* 提升知识库召回准确率
* 提升多轮对话理解能力
* 提升意图识别能力
* 提升用户交互体验

优化后架构：

```text
用户
 ↓
Intent Router
 ↓
FAQ / RAG / Small Talk
 ↓
Answer Builder
 ↓
留资流程
 ↓
CRM
```

---

# P0：RAG能力增强

## TASK-001：实现 Query Rewrite

### 目标

提升知识库召回率。

### 问题描述

用户提问：

```text
专科升本科
```

知识库：

```text
专升本
```

Embedding 可能无法准确召回。

### 解决方案

增加 Query Rewrite。

示例：

```text
专科升本科
↓
专升本
```

```text
成人高考
↓
成考
```

### 技术方案

新增模块：

```python
rewrite_query(query)
```

流程：

```text
用户问题
 ↓
Query Rewrite
 ↓
Retriever
```

### 推荐模型

```text
Qwen3-4B-Instruct
```

### 推荐 Prompt

```text
你是学历提升领域查询改写助手。

请将用户问题改写为更适合知识库检索的标准问题。

要求：

1. 保留原始语义
2. 展开简称
3. 补充领域术语
4. 输出一句话

用户问题：

{query}
```

### 验收标准

* Rewrite 后召回率提升
* 能处理简称与同义词
* 不改变用户原始语义

### 待办事项

* [ ] 接入 Qwen3-4B-Instruct
* [ ] 实现 rewrite_query()
* [ ] Prompt设计
* [ ] Rewrite日志记录
* [ ] Rewrite开关配置
* [ ] 单元测试

---

## TASK-002：实现多轮上下文改写

### 目标

解决上下文丢失问题。

### 问题描述

用户：

```text
成人高考和国开有什么区别？
```

下一轮：

```text
报名时间呢？
```

系统无法知道：

```text
报名时间
```

对应：

```text
成人高考
```

### 解决方案

新增会话历史。

```python
session.history
```

例如：

```python
[
    {
        "role": "user",
        "content": "成人高考和国开有什么区别"
    }
]
```

### Query Rewrite结合历史

改写前：

```text
报名时间呢？
```

改写后：

```text
成人高考报名时间是什么时候？
```

### 技术方案

流程：

```text
用户问题
 ↓
读取History
 ↓
Rewrite Query
 ↓
Retriever
```

### Session结构调整

```python
@dataclass
class ConversationSession:
    session_id: str
    state: State
    slots: dict
    qa_turns: int
    history: list[dict]
```

### 验收标准

* 支持最近N轮上下文
* 能正确补全代词与省略问题
* Rewrite结果符合用户意图

### 待办事项

* [ ] 增加 session.history
* [ ] 保存最近10轮会话
* [ ] 历史截断策略
* [ ] Rewrite支持History
* [ ] 集成测试

---

# P1：对话层智能化

## TASK-003：实现 Intent Router

### 目标

替代关键词判断。

### 当前问题

```python
if "多少钱" in text:
```

容易误判。

### 解决方案

引入 Intent Classifier。

输出：

```json
{
  "intent": "rag",
  "confidence": 0.98
}
```

### 推荐意图分类

```text
faq
rag
small_talk
lead
human_service
```

### 推荐模型

```text
Qwen3-4B-Instruct
```

### 路由流程

```text
用户问题
 ↓
Intent Classifier
 ↓

 ┌────────┬────────┬────────┬────────┐
 ▼        ▼        ▼        ▼

FAQ      RAG     闲聊     留资
```

### 推荐输出格式

```json
{
  "intent": "rag",
  "confidence": 0.98,
  "reason": "用户正在咨询学历相关知识"
}
```

### 验收标准

* 意图识别准确率 ≥ 90%
* 支持低置信度降级
* 支持扩展新意图

### 待办事项

* [ ] Intent Prompt设计
* [ ] Intent模型接入
* [ ] Intent Enum定义
* [ ] Router模块实现
* [ ] 置信度阈值设计
* [ ] 降级策略设计

---

## TASK-004：实现 Slot Filling

### 目标

自动抽取用户画像。

### 当前问题

用户必须逐步回答：

```text
学历
↓
目标
↓
用途
```

体验较差。

### 解决方案

一次提取多个槽位。

用户：

```text
我是大专，想专升本。
```

抽取：

```json
{
  "education": "大专",
  "goal": "专升本"
}
```

### 推荐槽位

```text
education
goal
purpose
city
budget
urgency
```

### 推荐输出格式

```json
{
  "education": "大专",
  "goal": "专升本",
  "purpose": null,
  "city": null,
  "budget": null,
  "urgency": null
}
```

### 流程

```text
用户输入
 ↓
Slot Extractor
 ↓
更新Session
 ↓
检查缺失槽位
 ↓
继续追问
```

### Session结构

```python
session.slots = {
    "education": "",
    "goal": "",
    "purpose": "",
    "city": "",
    "budget": "",
    "urgency": ""
}
```

### 验收标准

* 支持一次抽取多个槽位
* 支持增量更新槽位
* 缺失槽位自动追问

### 待办事项

* [ ] Slot Prompt设计
* [ ] Slot Extractor实现
* [ ] Session同步更新
* [ ] 缺失槽位追问
* [ ] 槽位校验机制

---

## TASK-005：实现 Small Talk 模块

### 目标

处理轻量闲聊。

### 负责内容

```text
你好
在吗
谢谢
辛苦了
再见
```

### 路由流程

```text
Intent = small_talk
 ↓
Small Talk
 ↓
回复用户
```

### 验收标准

* 常见闲聊正常回复
* 不影响业务咨询流程
* 支持转回RAG流程

### 待办事项

* [ ] Small Talk Prompt
* [ ] 闲聊回复模板
* [ ] 闲聊历史管理
* [ ] 降级到RAG策略
* [ ] 测试用例编写

---

# Sprint规划

## Sprint 1（优先级最高）

```text
TASK-001 Query Rewrite
TASK-002 多轮上下文改写
```

## Sprint 2

```text
TASK-003 Intent Router
```

## Sprint 3

```text
TASK-004 Slot Filling
```

## Sprint 4

```text
TASK-005 Small Talk
```

---

# Phase 1 完成后目标架构

```text
用户
 ↓
Intent Router
 ↓
FAQ / RAG / Small Talk
 ↓
Query Rewrite
 ↓
History Context
 ↓
Retriever
 ↓
LLM
 ↓
回复用户
```

实现从：

```text
规则状态机 + 简单RAG
```

升级为：

```text
具备企业级雏形的学历提升智能咨询助手
```
