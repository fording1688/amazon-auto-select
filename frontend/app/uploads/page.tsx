'use client';

import { FormEvent, useEffect, useState } from 'react';
import { authFetch } from '@/lib/api';

const reportTypes = [
  ['business_report', 'Business Report'],
  ['search_term_report', 'Advertising Search Term Report'],
  ['campaign_report', 'Campaign Report'],
  ['inventory_report', 'Inventory Report'],
  ['product_cost', 'Product Cost Excel'],
] as const;

export default function UploadsPage() {
  const [reportType, setReportType] = useState<(typeof reportTypes)[number][0]>('business_report');
  const [duplicateStrategy, setDuplicateStrategy] = useState('prompt');
  const [uploadedBy, setUploadedBy] = useState('');
  const [marketplace, setMarketplace] = useState('US');
  const [stores, setStores] = useState<Array<{ id: number; name: string; marketplace: string }>>([]);
  const [storeName, setStoreName] = useState('');
  const [newStoreName, setNewStoreName] = useState('');
  const [creatingStore, setCreatingStore] = useState(false);
  const [businessDate, setBusinessDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    authFetch('/api/copilot/stores')
      .then((response) => response.json())
      .then((data) => {
        const items = data.items || [];
        setStores(items);
        if (items[0]?.name) {
          setStoreName(items[0].name);
          setMarketplace(items[0].marketplace || 'US');
        }
      })
      .catch(() => undefined);
  }, []);

  async function createStore() {
    const cleanName = newStoreName.trim();
    if (!cleanName) {
      setError('请先填写店铺名称。');
      return;
    }
    setCreatingStore(true);
    setError('');
    try {
      const response = await authFetch('/api/copilot/stores', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: cleanName, marketplace }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || '创建店铺失败');
      const nextStores = [...stores.filter((store) => store.id !== data.id), data];
      setStores(nextStores);
      setStoreName(data.name);
      setNewStoreName('');
      setMarketplace(data.marketplace || marketplace || 'US');
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建店铺失败');
    } finally {
      setCreatingStore(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!storeName.trim()) {
      setError('请先创建并选择店铺名称。');
      return;
    }
    if (!file) {
      setError('请先选择 CSV 或 Excel 文件。');
      return;
    }
    const form = new FormData();
    form.append('file', file);
    form.append('duplicate_strategy', duplicateStrategy);
    form.append('uploaded_by', uploadedBy);
    form.append('marketplace', marketplace);
    form.append('store_name', storeName);
    form.append('business_date', businessDate);
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await authFetch(`/api/copilot/uploads/${reportType}`, {
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
      <p className="mt-2 text-slate-600">先定店铺和真实业务日期，再上传 Amazon 业务、广告、库存和成本报表。系统会把数据挂到对应项目批次下。</p>

      <section className="mt-6 rounded-lg border bg-white p-5">
        <h2 className="text-xl font-bold">店铺设置</h2>
        <p className="mt-1 text-sm text-slate-600">新账号先创建店铺。后续上传、看板和分析都会按账号 + 店铺隔离。</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_120px_auto]">
          <input
            className="rounded-md border border-slate-300 px-3 py-2"
            value={newStoreName}
            onChange={(event) => setNewStoreName(event.target.value)}
            placeholder="例如：Apple US Store"
          />
          <input
            className="rounded-md border border-slate-300 px-3 py-2"
            value={marketplace}
            onChange={(event) => setMarketplace(event.target.value)}
            placeholder="US"
          />
          <button
            className="rounded-md border border-blue-700 px-4 py-2 font-semibold text-blue-700 disabled:opacity-50"
            disabled={creatingStore}
            onClick={createStore}
            type="button"
          >
            {creatingStore ? '创建中...' : '创建店铺'}
          </button>
        </div>
      </section>

      <form className="mt-6 rounded-lg border bg-white p-5" onSubmit={submit}>
        <label className="block text-sm font-semibold text-slate-700">报表类型</label>
        <select
          className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
          value={reportType}
          onChange={(event) => setReportType(event.target.value as (typeof reportTypes)[number][0])}
        >
          {reportTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-semibold text-slate-700">店铺名称</label>
            <select
              className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
              value={storeName}
              onChange={(event) => setStoreName(event.target.value)}
            >
              <option value="">请选择店铺</option>
              {stores.map((store) => <option key={store.id} value={store.name}>{store.name} ({store.marketplace || 'US'})</option>)}
            </select>
            <p className="mt-1 text-xs text-slate-500">没有店铺时，先在上方创建。系统不再自动使用默认店铺。</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700">数据日期</label>
            <input
              className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
              type="date"
              value={businessDate}
              onChange={(event) => setBusinessDate(event.target.value)}
            />
            <p className="mt-1 text-xs text-slate-500">这是报表对应的业务日期，不是上传时间。</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700">站点</label>
            <input
              className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
              value={marketplace}
              onChange={(event) => setMarketplace(event.target.value)}
              placeholder="US"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700">上传人</label>
            <input
              className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
              value={uploadedBy}
              onChange={(event) => setUploadedBy(event.target.value)}
              placeholder="可选"
            />
          </div>
        </div>

        <label className="mt-4 block text-sm font-semibold text-slate-700">重复数据处理</label>
        <select
          className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
          value={duplicateStrategy}
          onChange={(event) => setDuplicateStrategy(event.target.value)}
        >
          <option value="prompt">发现重复时先提示，不导入业务行</option>
          <option value="overwrite">覆盖旧数据：旧行设为 inactive，新行参与分析</option>
          <option value="skip">跳过重复数据：只导入非重复行</option>
          <option value="preserve_inactive">保留为新批次但不参与默认分析</option>
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
            <Info label="项目名" value={result.project_name} />
            <Info label="店铺" value={result.store_name} />
            <Info label="数据日期" value={result.business_date ? String(result.business_date).slice(0, 10) : '-'} />
            <Info label="报表类型" value={result.report_type} />
            <Info label="行数" value={result.row_count} />
            <Info label="同步新表行数" value={result.synced_rows} />
            <Info label="状态" value={result.status} />
            <Info label="重复数据" value={result.duplicate_count} />
            <Info label="数据开始日期" value={result.period_start || '-'} />
            <Info label="数据结束日期" value={result.period_end || '-'} />
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
