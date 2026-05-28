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
2. FastAPI 解析字段并写入数据库。
3. 规则引擎计算 SKU 健康分、广告搜索词诊断、库存风险和利润。
4. 生成中文每日运营建议。
5. 用户人工确认执行，不自动改广告后台。
