# 亚马逊自动测款分析系统

第一版是最小可运行版本：默认使用 mock Amazon 数据，不需要真实 API Key。流程包括关键词管理、抓取 mock 产品、机会评分、OpenAI 分析或本地规则兜底、保存报告、后台查看、手动任务、定时任务和飞书 Webhook 推送。

## 安装

```bash
cd amazon-test-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 初始化数据库

```bash
python -m app.database
```

## 启动服务

```bash
uvicorn app.main:app --reload
```

访问后台：

```text
http://127.0.0.1:8000
```

## 配置

`.env` 支持：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENROUTER_HTTP_REFERER=
OPENROUTER_APP_NAME=amazon-auto-select
AMAZON_API_PROVIDER=mock
AMAZON_ADS_API_ENABLED=false
DEFAULT_AD_TEST_COST=15
SERPAPI_KEY=
RAINFOREST_API_KEY=
KEEPA_API_KEY=
FEISHU_WEBHOOK_URL=
DATABASE_URL=sqlite:///./amazon_test.db
DAILY_RUN_HOUR=8
OPENAI_MODEL=gpt-4o-mini
```

没有 `OPENAI_API_KEY` 时，系统会使用本地规则生成兜底 JSON 报告，保证流程能完整跑通。配置 `FEISHU_WEBHOOK_URL` 后，任务结束会推送 Top 5 产品。

如果使用 OpenRouter，把 `OPENAI_BASE_URL` 设置为 `https://openrouter.ai/api/v1`，`OPENAI_MODEL` 使用 OpenRouter 模型名，例如 `openai/gpt-4o-mini`。

如果要使用 SerpApi 真实 Amazon 搜索数据，把 `AMAZON_API_PROVIDER` 改为 `serpapi`，并设置 `SERPAPI_KEY` 或兼容旧脚本的 `SERPAPI_API_KEY`。

## 页面

- `/keywords`：关键词管理，支持新增、启用/停用、删除。
- `/products`：产品分析列表，支持按关键词和决策筛选。
- `/reports/product/{product_id}`：产品详情和 AI 分析报告。
- `/tasks`：手动运行任务和查看任务记录。
- `/imports`：上传运营和广告报表，支持 Search Term、Advertised Product、Campaign、Targeting、Bulk Operations 等。
- `/ad-recommendations`：广告优化建议安全模式。系统只生成建议，用户点击“确认执行”后只生成 `execution_plan_json`，第一版不会调用真实 Amazon Ads API。

## 广告建议安全模式

第一阶段默认不修改亚马逊广告后台。流程是：

1. 上传 Search Term Report、Advertised Product Report、Campaign Report、Targeting Report。
2. 系统根据订单、ACOS、点击、花费和预算状态生成 `pending` 建议。
3. 用户在 `/ad-recommendations` 点击“确认执行”。
4. 系统把建议改成 `approved`，并保存 `execution_plan_json`。
5. 第一版到此为止，不调用真实 Ads API。

后续接入真实 Amazon Ads API 时，仍然必须满足：

- `AMAZON_ADS_API_ENABLED=true`
- 建议状态为 `approved`
- 已经保存 `execution_plan_json`
- 单次批量执行不超过 20 条
- 预算和出价提高都不得超过 20%


## Amazon Seller Growth Copilot MVP

本仓库已新增前后端分离目录：

- `frontend/`：Next.js + Tailwind CSS 前端，面向 Cloudflare Pages。
- `backend/`：后端说明，当前复用现有 FastAPI 应用 `app.main:app`，面向 Render/VPS。
- `database/`：Supabase PostgreSQL schema。
- `docs/`：架构说明。

新增 API：

- `POST /api/copilot/uploads/{report_type}`：上传 Business、Search Term、Campaign、Inventory、Product Cost 报表。
- `GET /api/copilot/sku-health`：SKU 健康中心。
- `GET /api/copilot/ads-diagnosis`：广告诊断中心。
- `POST /api/copilot/profit-calculator`：利润计算器。
- `GET /api/copilot/daily-report`：每日中文运营报告。

前端本地启动：

```bash
cd frontend
npm install
npm run dev
```

默认调用 `http://127.0.0.1:8005` 的后端，可通过 `NEXT_PUBLIC_API_BASE_URL` 修改。

第一版只生成运营建议，不自动修改亚马逊广告后台。

### 报表批次和重复数据规则

- 每次上传都会创建 `import_batches` 记录，保存文件名、报表类型、上传时间、上传人、站点、数据周期、状态和重复数量。
- `uploaded_at` 只表示上传时间，不当作业务日期；系统优先读取报表里的 `Date / 日期` 作为 `report_date`。
- 业务数据表会记录 `import_batch_id`、`report_date`、`period_start`、`period_end`、`is_active`、`data_hash`。
- 默认分析只读取 `is_active = true` 的数据。
- 发现同站点、同 SKU/ASIN、同业务日期、同 campaign/search term 等维度重复时，可选择：
  - 覆盖旧数据：旧行设为 inactive，新行参与分析。
  - 跳过重复数据：只导入非重复行。
  - 保留为新批次但不参与默认分析：新行设为 inactive。
  - 重复时提示：创建批次并提示，不写入业务行。

## 后续接真实 Amazon API

统一入口在 `app/amazon_api_client.py`：

- `get_amazon_client()`
- `search_products(keyword: str, limit: int = 20) -> list[dict]`

后续接 SerpApi、Rainforest API、Keepa、DataForSEO 或 Oxylabs 时，只需要新增对应 Client，并把返回字段映射为系统内部统一字段：

```python
{
    "asin": "",
    "title": "",
    "price": 0,
    "rating": 0,
    "review_count": 0,
    "brand": "",
    "seller": "",
    "image_url": "",
    "product_url": "",
    "availability": "",
    "coupon": "",
    "variation_count": 0,
    "package_quantity": 1,
    "bsr": None,
}
```

## 评分逻辑

评分模块在 `app/scoring.py`，满分 100：

- 市场需求：25
- 竞争难度：20
- 利润空间：20
- 组合装机会：15
- 轻小件优势：10
- 差评改进机会：10

决策规则：

- 80-100：重点测款
- 65-79：小批量测试
- 50-64：观察
- 50 以下：放弃

## 注意

当前版本用于本地验证流程，不代表真实 Amazon 市场数据。上线前需要补充真实 API、账号鉴权、任务并发控制、日志系统和更严格的异常告警。
