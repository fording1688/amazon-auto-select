'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiGet } from '@/lib/api';
import ContextBar from './context-bar';

type SkuHealth = {
  sku: string;
  asin: string;
  sales: number;
  ad_spend: number;
  acos: number | null;
  estimated_profit: number;
  inventory_days: number | null;
  health_score: number;
  problem_tags: string[];
  recommended_actions: string[];
};

type DailyReport = {
  today_main_issues: string[];
  today_potential_skus: string[];
  today_recommended_actions: string[];
  priority_order: string[];
};

function contextQuery(searchParams: URLSearchParams) {
  const params = new URLSearchParams();
  const storeId = searchParams.get('store_id');
  const businessDate = searchParams.get('business_date');
  if (storeId) params.set('store_id', storeId);
  if (businessDate) params.set('business_date', businessDate);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export default function Home() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-7xl px-6 py-8 text-slate-600">加载中...</main>}>
      <HomeContent />
    </Suspense>
  );
}

function HomeContent() {
  const searchParams = useSearchParams();
  const [health, setHealth] = useState<SkuHealth[]>([]);
  const [report, setReport] = useState<DailyReport>({
    today_main_issues: [],
    today_potential_skus: [],
    today_recommended_actions: [],
    priority_order: [],
  });

  useEffect(() => {
    const query = contextQuery(searchParams);
    Promise.all([
      apiGet<{ items: SkuHealth[] }>(`/api/copilot/sku-health${query}`).catch(() => ({ items: [] })),
      apiGet<DailyReport>(`/api/copilot/daily-report${query}`).catch(() => ({
        today_main_issues: [],
        today_potential_skus: [],
        today_recommended_actions: [],
        priority_order: [],
      })),
    ]).then(([healthData, reportData]) => {
      setHealth(healthData.items || []);
      setReport(reportData);
    });
  }, [searchParams]);

  const topRisks = health.slice(0, 8);
  const totalSales = health.reduce((sum, item) => sum + (item.sales || 0), 0);
  const totalAdSpend = health.reduce((sum, item) => sum + (item.ad_spend || 0), 0);
  const totalProfit = health.reduce((sum, item) => sum + (item.estimated_profit || 0), 0);
  const storeId = searchParams.get('store_id') || undefined;
  const businessDate = searchParams.get('business_date') || undefined;

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-8 flex flex-col gap-3 border-b border-slate-200 pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-medium text-blue-700">Amazon Seller Growth Copilot</p>
          <h1 className="text-3xl font-bold tracking-tight">亚马逊店铺增长驾驶舱</h1>
          <p className="mt-2 text-slate-600">上传业务、广告、库存和成本报表后，系统自动生成 SKU 健康、广告诊断、利润和每日建议。</p>
        </div>
        <a className="rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white" href="/uploads">上传报表</a>
      </header>

      <ContextBar storeId={storeId} businessDate={businessDate} basePath="/" />

      <section className="mb-6 grid gap-4 md:grid-cols-4">
        <Metric label="SKU 数" value={health.length.toString()} />
        <Metric label="销售额" value={`$${totalSales.toFixed(2)}`} />
        <Metric label="广告花费" value={`$${totalAdSpend.toFixed(2)}`} />
        <Metric label="估算利润" value={`$${totalProfit.toFixed(2)}`} />
      </section>

      <section className="mb-6 grid gap-6 lg:grid-cols-2">
        <Panel title="今日主要问题"><List items={report.today_main_issues} empty="暂无明显问题，继续观察销售、广告和库存。" /></Panel>
        <Panel title="今日建议动作"><List items={report.today_recommended_actions} empty="暂无建议动作，请先上传报表。" /></Panel>
      </section>

      <section className="mb-6 grid gap-6 lg:grid-cols-2">
        <Panel title="潜力 SKU"><List items={report.today_potential_skus} empty="暂无明显潜力 SKU。" /></Panel>
        <Panel title="处理优先级"><List items={report.priority_order} empty="先上传完整报表后生成优先级。" /></Panel>
      </section>

      <Panel title="SKU Health Center">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-slate-500">
              <tr><th className="py-3">SKU / ASIN</th><th>销售</th><th>广告</th><th>利润</th><th>库存</th><th>健康分</th><th>标签</th><th>建议</th></tr>
            </thead>
            <tbody>
              {topRisks.map((item) => (
                <tr key={`${item.sku}-${item.asin}`} className="border-b align-top">
                  <td className="py-3 font-medium">{item.sku}<br /><span className="text-slate-500">{item.asin}</span></td>
                  <td>${item.sales?.toFixed(2)}</td>
                  <td>${item.ad_spend?.toFixed(2)}<br />ACOS {((item.acos || 0) * 100).toFixed(1)}%</td>
                  <td>${item.estimated_profit?.toFixed(2)}</td>
                  <td>{item.inventory_days ?? '-'} 天</td>
                  <td><span className="rounded bg-slate-100 px-2 py-1 font-semibold">{item.health_score}</span></td>
                  <td>{item.problem_tags.slice(0, 3).map((tag) => <span className="mr-1 inline-block rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-700" key={tag}>{tag}</span>)}</td>
                  <td className="max-w-sm">{item.recommended_actions[0] || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border bg-white p-4"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p></div>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-lg border bg-white p-5"><h2 className="mb-4 text-xl font-bold">{title}</h2>{children}</section>;
}

function List({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) return <p className="text-slate-500">{empty}</p>;
  return <ul className="space-y-2">{items.map((item, index) => <li className="rounded bg-slate-50 p-3" key={index}>{item}</li>)}</ul>;
}
