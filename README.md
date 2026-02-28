# LedgerFlow MVP

本项目是一个本地运行的复式记账 MVP，包含：

- 复式记账（借贷平衡校验）
- 购物清单与清单转交易草稿
- 月度/年度统计图表
- Google Gemini 消费建议（无 API Key 时自动降级为规则建议）

## 快速开始

```bash
python -m venv .venv
.venv/Scripts/pip.exe install -r requirements.txt
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py runserver
```

访问：

- 仪表盘: `http://127.0.0.1:8000/`
- 新增记账: `http://127.0.0.1:8000/journals/new`
- 交易明细: `http://127.0.0.1:8000/journals/`
- 购物清单: `http://127.0.0.1:8000/lists/`
- 分析报告: `http://127.0.0.1:8000/reports`

## 环境变量

复制 `.env.example` 并设置：

- `GOOGLE_API_KEY`: 你的 Gemini API Key
- `GEMINI_MODEL`: 默认 `gemini-1.5-flash`

不配置 `GOOGLE_API_KEY` 时，系统会返回规则建议。

## 测试

```bash
.venv/Scripts/python.exe manage.py test
```

## MCP Server（给 AI 客户端调用）

已内置一个基于 stdio 的 MCP 服务，支持记账、购物清单和报表查询。

启动命令：

```bash
.venv/Scripts/python.exe scripts/run_mcp_server.py
```

如果你希望“启动项目时自动带上 MCP 服务”：

```bash
.venv/Scripts/python.exe scripts/start_with_mcp.py
```

这个脚本会同时启动：

- Django 开发服务（`manage.py runserver`）
- MCP stdio 服务（`scripts/run_mcp_server.py`）

可用 tools（首批）：

- `ledger.get_accounts`
- `ledger.get_categories`
- `ledger.list_tags`
- `ledger.list_journals`
- `ledger.get_journal`
- `ledger.create_journal`
- `ledger.update_journal`
- `ledger.delete_journal`（需 `confirm=true`）
- `shopping.list_items`
- `shopping.add_item`
- `shopping.update_item`
- `shopping.update_status`
- `shopping.delete_item`（需 `confirm=true`）
- `shopping.pending_summary`
- `report.monthly_summary`
- `report.period_summary`
- `report.yearly_summary`

AI 客户端 MCP 配置示例（通用）：

```json
{
  "mcpServers": {
    "ledgerflow": {
      "command": "D:/project/memory/.venv/Scripts/python.exe",
      "args": ["D:/project/memory/scripts/run_mcp_server.py"]
    }
  }
}
```

## 远程 MCP（HTTP）

项目已支持远程 MCP HTTP 入口：

- `POST /mcp/http`

部署后可通过域名访问，例如：

- `https://book.524120.xyz/mcp/http`

建议配置环境变量 `MCP_API_TOKEN` 作为远程调用鉴权：

- 请求头可用 `Authorization: Bearer <token>`
- 或 `X-MCP-Token: <token>`

Cherry Studio 可选择 `streamablehttp` 类型并填入上述 URL 与 Token。
