'use client';

import { FormEvent, useState } from 'react';
import { API_BASE } from '@/lib/api';

const reportTypes = [
  ['business_report', 'Business Report'],
  ['search_term_report', 'Advertising Search Term Report'],
  ['campaign_report', 'Campaign Report'],
  ['inventory_report', 'Inventory Report'],
  ['product_cost', 'Product Cost Excel'],
] as const;

export default function UploadsPage() {
  const [reportType, setReportType] = useState<(typeof reportTypes)[number][0]>('business_report');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError('请先选择 CSV 或 Excel 文件。');
      return;
    }
    const form = new FormData();
    form.append('file', file);
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/copilot/uploads/${reportType}`, {
        method: 'POST',
        body: form,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.error_message || '上传失败');
      }
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="text-3xl font-bold">报表上传</h1>
      <p className="mt-2 text-slate-600">上传 Amazon 业务、广告、库存和成本报表，系统会解析入库并刷新 SKU 健康、广告诊断和每日建议。</p>

      <form className="mt-6 rounded-lg border bg-white p-5" onSubmit={submit}>
        <label className="block text-sm font-semibold text-slate-700">报表类型</label>
        <select
          className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
          value={reportType}
          onChange={(event) => setReportType(event.target.value as (typeof reportTypes)[number][0])}
        >
          {reportTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>

        <label className="mt-4 block text-sm font-semibold text-slate-700">文件</label>
        <input
          className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
        />

        <button className="mt-5 rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50" disabled={loading}>
          {loading ? '上传并分析中...' : '上传并分析'}
        </button>
      </form>

      {error && <div className="mt-5 rounded-md border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}
      {result && (
        <section className="mt-5 rounded-lg border bg-white p-5">
          <h2 className="text-xl font-bold">导入结果</h2>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            <Info label="批次 ID" value={result.batch_id} />
            <Info label="报表类型" value={result.report_type} />
            <Info label="行数" value={result.row_count} />
            <Info label="同步新表行数" value={result.synced_rows} />
            <Info label="状态" value={result.status} />
            <Info label="广告建议数" value={result.generated_ad_recommendations} />
            <Info label="错误" value={result.error_message || '-'} />
          </dl>
        </section>
      )}
    </main>
  );
}

function Info({ label, value }: { label: string; value: any }) {
  return <div className="rounded bg-slate-50 p-3"><dt className="text-sm text-slate-500">{label}</dt><dd className="mt-1 font-semibold">{String(value ?? '-')}</dd></div>;
}
