"use client";

import { useState } from 'react';
import { API_BASE } from '@/lib/api';

const fields = [
  ['price', '售价'], ['purchase_cost', '采购成本'], ['logistics_cost', '物流成本'], ['fba_fee', 'FBA费用'], ['referral_fee_rate', '平台佣金比例'], ['ad_spend', '广告花费'],
] as const;

export default function ProfitCalculatorPage() {
  const [form, setForm] = useState<Record<string, number>>({ price: 29.99, referral_fee_rate: 0.15 });
  const [result, setResult] = useState<Record<string, number> | null>(null);
  async function calculate() {
    const response = await fetch(`${API_BASE}/api/copilot/profit-calculator`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) });
    setResult(await response.json());
  }
  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="text-3xl font-bold">Profit Calculator</h1>
      <div className="mt-6 grid gap-4 rounded-lg border bg-white p-5 md:grid-cols-2">
        {fields.map(([key, label]) => <label className="text-sm font-medium" key={key}>{label}<input className="mt-1 w-full rounded border px-3 py-2" type="number" step="0.01" value={form[key] ?? 0} onChange={(event) => setForm({ ...form, [key]: Number(event.target.value) })} /></label>)}
        <button className="rounded bg-blue-700 px-4 py-2 font-semibold text-white md:col-span-2" onClick={calculate}>计算利润</button>
      </div>
      {result && <div className="mt-6 rounded-lg border bg-white p-5"><h2 className="text-xl font-bold">计算结果</h2><div className="mt-4 grid gap-3 md:grid-cols-2">{Object.entries(result).map(([key, value]) => <div className="rounded bg-slate-50 p-3" key={key}><span className="text-slate-500">{key}</span><p className="text-2xl font-bold">{typeof value === 'number' ? value.toFixed(2) : value}</p></div>)}</div></div>}
    </main>
  );
}
