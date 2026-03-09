# OpenClaw 操作文档（LedgerFlow MCP）

本文档用于指导你在 OpenClaw 中接入并使用 LedgerFlow 的远程 MCP 服务，实现 AI 记账、购物清单管理、报表查询等操作。

## 1. 目标与架构

- 目标：在 OpenClaw 中通过自然语言调用 LedgerFlow 的业务能力。
- 协议：`streamablehttp`
- 端点：`https://book.524120.xyz/mcp/http`
- 鉴权：`MCP_API_TOKEN`（推荐必填）

## 2. 服务器端准备

### 2.1 更新代码并重建

```bash
cd ~/server/ledgerflow-app
git pull
docker compose up -d --build
```

### 2.2 设置 MCP 访问令牌

编辑 `.env`，增加或更新：

```env
MCP_API_TOKEN=replace-with-a-strong-random-token
```

重启容器：

```bash
docker compose restart
```

### 2.3 健康检查（推荐）

```bash
curl -X POST "https://book.524120.xyz/mcp/http" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer replace-with-a-strong-random-token" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

返回 `200` 且包含 `tools` 列表即表示 MCP 服务可用。

## 3. OpenClaw 连接配置

在 OpenClaw 新增 MCP 服务：

- 类型：`streamablehttp`
- URL：`https://book.524120.xyz/mcp/http`
- Token：`MCP_API_TOKEN` 对应值

> 注意：不要选 `sse`，否则会出现 `405` 错误。

## 4. 可用工具清单（首批）

### 4.1 记账

- `ledger_get_accounts`
- `ledger_get_categories`
- `ledger_list_tags`
- `ledger_list_journals`
- `ledger_get_journal`
- `ledger_create_journal`
- `ledger_update_journal`
- `ledger_delete_journal`（需要 `confirm=true`）

### 4.2 购物清单

- `shopping_list_items`
- `shopping_add_item`
- `shopping_update_item`
- `shopping_update_status`
- `shopping_delete_item`（需要 `confirm=true`）
- `shopping_pending_summary`

### 4.3 报表

- `report_monthly_summary`
- `report_period_summary`
- `report_yearly_summary`

## 5. 幂等键（防重复提交）

以下写工具支持 `idempotency_key`：

- `ledger_create_journal`
- `shopping_add_item`

建议在客户端每次写请求都携带一个唯一键（如 UUID）：

- 同一个 `idempotency_key` + 同参数：返回第一次结果（避免重复记账）
- 同一个 `idempotency_key` + 不同参数：返回冲突错误

## 6. OpenClaw 推荐测试话术

### 6.1 连通性

- “请调用 `ledger_get_accounts`，列出账户名称和余额。”

### 6.2 记账闭环

1) 新增一笔：

- “请调用 `ledger_create_journal` 新增记账：
  - date: `2026-03-01`
  - description: `午餐`
  - tags: `餐饮,工作日`
  - idempotency_key: `test-journal-001`
  - entries:
    - `{account_id: "expense", debit: "32", credit: "0", currency: "CNY"}`
    - `{account_id: "wechat", debit: "0", credit: "32", currency: "CNY"}`
  ”

2) 查询确认：

- “请调用 `ledger_list_journals`，month=`2026-03`，找出 `午餐` 这条记录并返回 journal_id。”

### 6.3 购物清单

- “请调用 `shopping_add_item`，新增：蓝牙耳机，qty=1，est_price=299，actual_price=259，priority=high，platform=京东，idempotency_key=`test-shopping-001`。”

### 6.4 报表

- “请调用 `report_period_summary`，period=`month`，用 5 条要点总结当前月消费情况。”

## 7. 常见问题排查

### 7.1 `SSE error: Non-200 status code (405)`

- 原因：MCP 类型选成了 `sse`
- 处理：改为 `streamablehttp`

### 7.2 `Invalid function.name pattern`

- 原因：客户端缓存了旧工具定义
- 处理：删除并重新添加 MCP 服务，重启 OpenClaw 后重试

### 7.3 `JSON.parse: unexpected end of data`

- 原因：客户端解析空响应体
- 处理：确保服务端已更新到最新版本（已对通知返回 JSON 兼容）

### 7.4 401 unauthorized

- 原因：Token 错误或缺失
- 处理：核对 OpenClaw Token 与服务器 `.env` 中 `MCP_API_TOKEN` 是否一致

## 8. 安全建议

- 生产环境务必设置 `MCP_API_TOKEN`
- 定期轮换 token
- 删除/导入类操作保留二次确认（`confirm=true`）
- 对外网访问建议配合 IP 白名单或 WAF

## 9. 运维命令

```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f

# 重建部署
docker compose up -d --build

# 仅重启服务
docker compose restart
```

## 10. 给 OpenClaw 的操作规范（重点）

这一节是给 OpenClaw 直接执行 LedgerFlow 的“行为规则”，建议你在 OpenClaw 的系统提示词/项目指令中粘贴使用。

### 10.1 总目标

- 通过 MCP 工具完成记账、查账、购物清单管理、报表分析。
- 优先使用已有数据（账户、分类、标签），避免凭空创建不存在的值。
- 所有写操作先校验参数，失败时返回可执行修复建议。

### 10.2 工具调用顺序规则

1. 记账前必须先调用：
   - `ledger_get_accounts`
   - `ledger_get_categories`
2. 若用户只说“查账”，默认调用：
   - `ledger_list_journals`（当月）
3. 若用户要“统计”，默认调用：
   - `report_period_summary`（`period=month`）
4. 写操作必须附带 `idempotency_key`，避免重复提交。

### 10.3 写操作安全规则

- 删除操作必须二次确认：`confirm=true`。
- 金额必须是字符串数字，且保留两位小数（如 `"32.00"`）。
- `ledger_create_journal` 的 `entries` 必须借贷平衡。
- 同一个 `idempotency_key` 不得复用到不同参数请求。

## 11. 给 OpenClaw 的可复制系统提示词

把下面这段直接粘贴到 OpenClaw 的项目系统提示词中：

```text
你是 LedgerFlow 财务助理，只能通过 MCP 工具操作记账系统。

规则：
1) 涉及新增/修改/删除数据时，优先确认关键参数：日期、账户、金额、分类、标签。
2) 每次写操作都生成并传递 idempotency_key（UUID 风格），防止重复提交。
3) 删除操作必须显式传 confirm=true。
4) 记账分录必须借贷平衡，不平衡时不要提交，先提示用户修正。
5) 若用户说“查账”但未给时间，默认查询当月（YYYY-MM）。
6) 若用户说“看报表”，默认调用 report_period_summary(period=month)。
7) 返回结果要中文简洁，包含关键金额、账户、分类与下一步建议。

常用工具：
- 账户/分类：ledger_get_accounts, ledger_get_categories
- 记账：ledger_create_journal, ledger_list_journals, ledger_update_journal, ledger_delete_journal
- 清单：shopping_add_item, shopping_list_items, shopping_update_status
- 报表：report_monthly_summary, report_period_summary, report_yearly_summary
```

## 12. 常见任务的标准执行模板

### 12.1 用户说“记一笔：微信花了32元吃午饭，分类餐饮”

OpenClaw 应执行：

1. 调 `ledger_get_accounts`，确认 `wechat`、`expense` 存在。
2. 调 `ledger_get_categories`，查到“餐饮”对应的分类 ID（如有）。
3. 调 `ledger_create_journal`：
   - `date`: 今日
   - `description`: `午饭`
   - `tags`: `餐饮`
   - `idempotency_key`: 新 UUID
   - `entries`:
     - 借：`expense` 32.00
     - 贷：`wechat` 32.00
4. 用自然语言返回“已记账成功 + 凭证摘要”。

### 12.2 用户说“看看我这个月花了多少”

OpenClaw 应执行：

1. 调 `report_period_summary`，参数 `period=month`
2. 返回：本月收入、支出、净额、储蓄率、前三消费分类。

### 12.3 用户说“把刚才那条删掉”

OpenClaw 应执行：

1. 先通过 `ledger_list_journals` 或上下文拿到 `journal_id`
2. 调 `ledger_delete_journal`，并设置 `confirm=true`
3. 返回删除结果与剩余记录提示。

## 13. 对话层推荐问法（你可直接对 OpenClaw 说）

- “帮我记一笔：支付宝买咖啡18元，分类餐饮，标签通勤。”
- “查询本月所有交易，按金额从高到低列出前10条。”
- “把今天那笔‘午餐’改成35元。”
- “新增购物项：洗衣液，预算59，实际49，平台京东。”
- “给我一个本周和本月的消费对比。”
