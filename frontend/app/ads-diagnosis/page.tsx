import { apiGet } from '@/lib/api';

const sections = [
  ['profitable_terms', '盈利词'],
  ['potential_terms', '潜力词'],
  ['waste_terms', '烧钱词'],
  ['negative_keywords', '建议否定词'],
  ['product_target_asins', 'ASIN 商品投放机会'],
  ['exact_keywords', '建议精准投放词'],
] as const;

type DiagnosisKey = (typeof sections)[number][0];
type DiagnosisData = Record<DiagnosisKey, any[]>;

const emptyDiagnosis: DiagnosisData = {
  profitable_terms: [],
  potential_terms: [],
  waste_terms: [],
  negative_keywords: [],
  product_target_asins: [],
  exact_keywords: [],
};

export default async function AdsDiagnosisPage() {
  const data = await apiGet<DiagnosisData>('/api/copilot/ads-diagnosis').catch(() => emptyDiagnosis);
  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <h1 className="text-3xl font-bold">Ads Diagnosis Center</h1>
      <p className="mt-2 text-slate-600">识别盈利词、ASIN 商品投放机会、烧钱词和否定词建议；ASIN 流量不会被当成 keyword exact。</p>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        {sections.map(([key, label]) => (
          <section className="rounded-lg border bg-white p-5" key={key}>
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-xl font-bold">{label}</h2>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">{(data[key] || []).length} 条</span>
            </div>
            <ul className="space-y-3">
              {(data[key] || []).slice(0, 10).map((item, index) => <AdDiagnosisItem item={item} key={index} />)}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}

function AdDiagnosisItem({ item }: { item: any }) {
  const trafficLabel = item.traffic_type === 'asin_product_target' ? 'ASIN Product Target' : 'Keyword Search Term';
  return (
    <li className="rounded border border-slate-100 bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <strong className="text-base">{item.search_term || '-'}</strong>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
            <span className="rounded bg-white px-2 py-1">{trafficLabel}</span>
            {item.targeting ? <span className="rounded bg-white px-2 py-1">原投放: {item.targeting}</span> : null}
          </div>
        </div>
        <span className="rounded bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">
          ACOS {((item.acos || 0) * 100).toFixed(1)}%
        </span>
      </div>

      <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <Info label="Campaign" value={item.campaign_name} strong />
        <Info label="Ad Group" value={item.ad_group_name} strong />
        <Info label="点击" value={item.clicks} />
        <Info label="花费" value={`$${item.spend?.toFixed?.(2) ?? item.spend ?? 0}`} />
        <Info label="销售" value={`$${item.sales?.toFixed?.(2) ?? item.sales ?? 0}`} />
        <Info label="订单" value={item.orders} />
      </div>

      <div className="mt-3 rounded bg-white p-2 text-sm">
        <div className="font-semibold text-slate-700">建议动作</div>
        <div className="mt-1 text-slate-700">{item.action || item.reason || '-'}</div>
      </div>
      <div className="mt-2 text-xs text-slate-500">去广告后台按 Campaign 和 Ad Group 搜索定位，再处理该搜索词或 ASIN。</div>
    </li>
  );
}

function Info({ label, value, strong = false }: { label: string; value: any; strong?: boolean }) {
  return (
    <div className="rounded bg-white px-2 py-1">
      <span className="text-slate-500">{label}: </span>
      <span className={strong ? 'font-semibold text-slate-900' : 'text-slate-800'}>{value || '-'}</span>
    </div>
  );
}
