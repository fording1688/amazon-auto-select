# Amazon Seller Growth Copilot Architecture

## 目标

通过上传 Amazon 业务、广告、库存和成本报表，自动生成 SKU 健康、广告诊断、利润和每日运营建议。第一版只生成建议，不自动修改 Amazon 广告后台。

## 目录

- `/frontend`: Next.js + Tailwind CSS 前端。
- `/backend`: 后端说明，当前复用根目录 FastAPI app。
- `/database`: Supabase PostgreSQL schema。
- `/docs`: 架构和使用说明。

## 数据流

1. 上传 CSV / Excel 报表。
2. FastAPI 为每次上传创建 `import_batches` 记录，上传时间只代表文件进入系统的时间。
3. 解析报表里的 `Date / 日期` 作为 `report_date`，并保存 `period_start / period_end`。
4. 业务行写入 `import_batch_id`、`is_active`、`data_hash`，用于追踪批次和去重。
5. 重复数据按 marketplace + SKU/ASIN + report_date + campaign/search term 等维度识别。
6. 用户选择覆盖旧数据、跳过重复数据，或保留为不参与默认分析的新批次。
7. 规则引擎默认只读取 `is_active = true` 的数据，计算 SKU 健康、广告诊断、库存风险和利润。
8. 生成中文每日运营建议，用户人工确认执行，不自动改广告后台。
