# OpenClaw 使用手册（LedgerFlow 远程 MCP）

> 目标读者：OpenClaw 配置者、Prompt 维护者、日常使用者。
>
> 目标：让 OpenClaw 稳定完成“记账、查账、购物清单管理、报表分析”等全流程操作。

---

## 1. 系统说明

LedgerFlow 已提供远程 MCP 接口，OpenClaw 通过该接口调用工具完成业务操作。

- 协议类型：`streamablehttp`
- MCP 端点：`https://book.524120.xyz/mcp/http`
- 鉴权方式：`Authorization: Bearer <MCP_API_TOKEN>`（推荐必填）

---

## 2. 部署前检查（服务器）

在服务器执行：

```bash
cd ~/server/ledgerflow-app
git pull
docker compose up -d --build
```

编辑 `.env`，确认有：

```env
MCP_API_TOKEN=replace-with-a-strong-random-token
```

重启服务：

```bash
docker compose restart
```

---

## 3. 接口联通验证

先不用 OpenClaw，直接验证 MCP 接口可用。

### 3.1 列出工具

```bash
curl -s -X POST "https://book.524120.xyz/mcp/http" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer replace-with-a-strong-random-token" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

预期：返回 `tools` 数组，工具名如 `ledger_get_accounts`（下划线命名）。

### 3.2 调用一个工具

```bash
curl -s -X POST "https://book.524120.xyz/mcp/http" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer replace-with-a-strong-random-token" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"ledger_get_accounts","arguments":{}}}'
```

预期：返回账户列表。

---

## 4. OpenClaw 配置方式

在 OpenClaw 新增 MCP 服务时使用：

- 类型：`streamablehttp`
- URL：`https://book.524120.xyz/mcp/http`
- Token：`MCP_API_TOKEN` 的值

> 不要用 `sse`，否则会报 405。

---

## 5. 工具清单（当前可用）

### 5.1 记账相关

- `ledger_get_accounts`
- `ledger_get_categories`
- `ledger_list_tags`
- `ledger_list_journals`
- `ledger_get_journal`
- `ledger_create_journal`
- `ledger_update_journal`
- `ledger_delete_journal`（必须 `confirm=true`）
- `ledger_create_rent_template`（房租押一付三模板）

### 5.2 购物清单相关

- `shopping_list_items`
- `shopping_add_item`
- `shopping_update_item`
- `shopping_update_status`
- `shopping_delete_item`（必须 `confirm=true`）
- `shopping_pending_summary`

### 5.3 报表相关

- `report_monthly_summary`
- `report_period_summary`（`day/week/month/year`）
- `report_yearly_summary`
- `report_budget_center_summary`

---

## 6. OpenClaw 运行规则（必须遵守）

这一节是“操作行为标准”，建议作为 OpenClaw 的项目级系统规则。

1. 任何写操作前先确认关键参数（日期、账户、金额、分类）。
2. 写操作必须尽量携带 `idempotency_key` 防重复提交。
3. 删除操作必须显式传 `confirm=true`。
4. 记账分录必须借贷平衡（借方总额 = 贷方总额）。
5. 查账缺省时间时：默认查询当月（`YYYY-MM`），但允许空月份查询全量。
6. 看报表缺省周期时：默认 `report_period_summary(period="month")`。

---

## 7. 幂等键（防重复记账）

支持幂等键的工具：

- `ledger_create_journal`
- `shopping_add_item`
- `ledger_create_rent_template`

规则：

- 同一个 `idempotency_key` + 同参数：返回首次结果（`idempotency_replay=true`）
- 同一个 `idempotency_key` + 不同参数：返回冲突错误

建议：OpenClaw 每次写操作都生成一个新 UUID 作为 `idempotency_key`。

---

## 8. 操作模板（OpenClaw 应该怎么做）

### 8.1 新增记账（标准流程）

用户输入：

> “帮我记一笔：微信午餐 32 元，分类餐饮，标签工作日”

OpenClaw 推荐执行顺序：

1. `ledger_get_accounts`（确认 `wechat`、`expense` 存在）
2. `ledger_get_categories`（找到“餐饮”对应分类）
3. `ledger_create_journal`（写入）

建议参数结构：

```json
{
  "date": "2026-03-01",
  "description": "午餐",
  "source": "mcp",
  "tags": "餐饮,工作日",
  "idempotency_key": "journal-20260301-001",
  "entries": [
    {"account_id": "expense", "category_id": "food", "debit": "32.00", "credit": "0.00", "currency": "CNY", "note": "午餐"},
    {"account_id": "wechat", "category_id": "food", "debit": "0.00", "credit": "32.00", "currency": "CNY", "note": "午餐"}
  ],
  "transfer_lines": []
}
```

### 8.2 查询当月交易

用户输入：

> “查一下这个月的账单”

OpenClaw 调用：

```json
{
  "name": "ledger_list_journals",
  "arguments": {
    "month": "2026-03"
  }
}
```

也支持组合过滤（账户/分类/标签）：

```json
{
  "name": "ledger_list_journals",
  "arguments": {
    "month": "2026-03",
    "account_id": "wechat",
    "category_id": "food",
    "tag": "餐饮"
  }
}
```

### 8.3 修改某笔记账

流程：

1. 先 `ledger_list_journals` 找到 `journal_id`
2. 再 `ledger_get_journal` 取原始结构
3. 修改需要变更字段后调用 `ledger_update_journal`

### 8.4 删除某笔记账

必须包含：`confirm=true`

```json
{
  "name": "ledger_delete_journal",
  "arguments": {
    "month": "2026-03",
    "journal_id": "xxx",
    "confirm": true
  }
}
```

### 8.5 新增购物项

```json
{
  "name": "shopping_add_item",
  "arguments": {
    "name": "洗衣液",
    "qty": 1,
    "est_price": 59,
    "actual_price": 49,
    "priority": "normal",
    "planned_date": "2026-03-02",
    "platform": "京东",
    "note": "日用品补货",
    "idempotency_key": "shopping-20260302-001"
  }
}
```

### 8.6 查询报表

默认月报：

```json
{
  "name": "report_period_summary",
  "arguments": {
    "period": "month"
  }
}
```

### 8.7 查询预算执行中心（含年预算趋势）

```json
{
  "name": "report_budget_center_summary",
  "arguments": {
    "scope": "year",
    "year": "2026"
  }
}
```

返回包含：预算总额、实际总额、预警分类、12个月预算/实际/差额趋势数据。

### 8.8 房租押一付三模板

```json
{
  "name": "ledger_create_rent_template",
  "arguments": {
    "pay_date": "2026-03-01",
    "start_month": "2026-03",
    "from_account_id": "wechat",
    "prepaid_account_id": "general",
    "deposit_account_id": "alipay",
    "category_id": "housing",
    "monthly_rent": 3000,
    "months_count": 3,
    "deposit_amount": 3000,
    "tags": "房租",
    "note": "XX小区",
    "idempotency_key": "rent-20260301-001"
  }
}
```

说明：会自动生成 1 笔付款凭证 + 3 笔月度分摊凭证。

---

## 9. 推荐用户问法（给 OpenClaw）

- “记一笔：支付宝买咖啡 18 元，分类餐饮，标签通勤。”
- “帮我查这个月所有餐饮相关支出。”
- “把今天那笔午餐从 32 改成 35。”
- “新增购物项：蓝牙耳机，预算 299，实际 259，平台京东。”
- “给我看本周和本月消费对比。”
- “帮我查微信账户 3 月餐饮交易。”
- “给我看 2026 年预算执行情况和预警分类。”
- “按押一付三生成房租模板，月租 3000 押金 3000。”

---

## 10. 常见错误与解决

### 10.1 `SSE error: 405`

- 原因：类型选成 `sse`
- 解决：改为 `streamablehttp`

### 10.2 `Invalid function.name pattern`

- 原因：客户端缓存旧工具
- 解决：删除 MCP 服务并重建；重启 OpenClaw

### 10.3 `JSON.parse unexpected end`

- 原因：客户端解析空 body
- 解决：更新到当前服务端版本（已做兼容）

### 10.4 `401 unauthorized`

- 原因：Token 错误/缺失
- 解决：核对 OpenClaw Token 与 `.env` 的 `MCP_API_TOKEN`

---

## 11. 安全与运维建议

- 生产环境务必设置强随机 `MCP_API_TOKEN`
- 建议定期轮换 token
- 外网访问建议配合 IP 白名单或 WAF
- 所有写操作保留幂等键与确认参数

常用命令：

```bash
docker compose ps
docker compose logs -f
docker compose restart
docker compose up -d --build
```
