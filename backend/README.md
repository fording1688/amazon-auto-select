# Backend

Seller Growth Copilot 后端复用现有 FastAPI 应用：`app.main:app`。

启动：

```bash
uvicorn app.main:app --reload --port 8005
```

核心 API：

- `POST /api/copilot/uploads/{report_type}`
- `GET /api/copilot/sku-health`
- `GET /api/copilot/ads-diagnosis`
- `POST /api/copilot/profit-calculator`
- `GET /api/copilot/daily-report`
