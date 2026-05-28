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
        {sections.map(([key, label]) => <section className="rounded-lg border bg-white p-5" key={key}><h2 className="mb-3 text-xl font-bold">{label}</h2><ul className="space-y-2">{(data[key] || []).slice(0, 10).map((item, index) => <li className="rounded bg-slate-50 p-3" key={index}><strong>{item.search_term}</strong><br/>点击 {item.clicks} · 花费 ${item.spend?.toFixed?.(2) ?? item.spend} · 订单 {item.orders} · ACOS {((item.acos || 0) * 100).toFixed(1)}%<br/><span className="text-slate-600">{item.reason || item.action}</span></li>)}</ul></section>)}
      </div>
    </main>
  );
}
