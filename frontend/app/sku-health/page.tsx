import { apiGet } from '@/lib/api';

const pageSize = 50;

export default async function SkuHealthPage({ searchParams }: { searchParams?: { page?: string } }) {
  const data = await apiGet<{ items: any[] }>('/api/copilot/sku-health').catch(() => ({ items: [] }));
  const currentPage = Math.max(1, Number(searchParams?.page || 1));
  const totalPages = Math.max(1, Math.ceil(data.items.length / pageSize));
  const items = data.items.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <h1 className="text-3xl font-bold">SKU Health Center</h1>
      <p className="mt-2 text-slate-600">按健康分排序，优先处理低分 SKU。</p>
      <div className="mt-6 overflow-x-auto rounded-lg border bg-white p-4">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b">
              <th className="min-w-80 py-3">产品</th>
              <th>SKU / ASIN</th>
              <th>销售</th>
              <th>利润</th>
              <th>库存天数</th>
              <th>健康分</th>
              <th>标签</th>
              <th>建议</th>
            </tr>
          </thead>
          <tbody>
          {items.map((item) => (
            <tr className="border-b align-top" key={`${item.sku}-${item.asin}`}>
              <td className="py-3">
                <div className="flex min-w-80 items-start gap-3">
                  {item.image_url ? (
                    <img className="h-16 w-16 rounded border object-contain" src={item.image_url} alt={item.title || item.asin || item.sku} />
                  ) : (
                    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded border bg-slate-50 text-xs text-slate-400">无图</div>
                  )}
                  <div>
                    <div className="line-clamp-2 max-w-md font-medium" title={item.title || ''}>{item.title || '暂无产品标题，请上传 Listing 表补充'}</div>
                    <div className="mt-1 text-xs text-slate-500">{item.asin || item.sku}</div>
                  </div>
                </div>
              </td>
              <td className="py-3 font-medium">{item.sku}<br/><span className="text-slate-500">{item.asin}</span></td>
              <td>${item.sales?.toFixed?.(2) ?? item.sales}</td>
              <td>${item.estimated_profit?.toFixed?.(2) ?? item.estimated_profit}</td>
              <td>{item.inventory_days ?? '-'}</td>
              <td>{item.health_score}</td>
              <td>{item.problem_tags?.join(', ')}</td>
              <td>{item.recommended_actions?.[0]}</td>
            </tr>
          ))}
        </tbody></table>
        <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
          <span>共 {data.items.length} 条，第 {currentPage} / {totalPages} 页</span>
          <div className="flex gap-2">
            <a className="rounded border px-3 py-1 aria-disabled:pointer-events-none aria-disabled:opacity-40" aria-disabled={currentPage <= 1} href={`/sku-health?page=${Math.max(1, currentPage - 1)}`}>上一页</a>
            <a className="rounded border px-3 py-1 aria-disabled:pointer-events-none aria-disabled:opacity-40" aria-disabled={currentPage >= totalPages} href={`/sku-health?page=${Math.min(totalPages, currentPage + 1)}`}>下一页</a>
          </div>
        </div>
      </div>
    </main>
  );
}
