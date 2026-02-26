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
