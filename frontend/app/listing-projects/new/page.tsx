'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authFetch } from '@/lib/api';
import ListingSubnav from '../listing-subnav';

const inputFields = [
  ['size', '尺寸 / 规格'],
  ['material', '材质'],
  ['color', '颜色'],
  ['quantity', '数量 / 几件装'],
  ['compatibility', '兼容型号 / 适配对象'],
  ['package_includes', '包装包含'],
  ['warning_limitation', '使用限制 / 注意事项'],
  ['use_cases', '使用场景'],
  ['main_keywords', '主关键词'],
  ['compliance_notes', '合规备注 / 不能写的宣传点'],
] as const;

export default function NewListingProjectPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const inputs: Record<string, string> = {};
    inputFields.forEach(([key]) => {
      inputs[key] = String(form.get(key) || '');
    });
    const productName = String(form.get('product_name') || '').trim();
    const payload = {
      project_name: `${productName || 'Listing 项目'} ${new Date().toISOString().slice(0, 10)}`,
      marketplace: String(form.get('marketplace') || 'US'),
      brand: String(form.get('brand') || ''),
      category: String(form.get('category') || ''),
      product_name: productName,
      target_price: String(form.get('target_price') || ''),
      fulfillment_method: String(form.get('fulfillment_method') || ''),
      notes: String(form.get('notes') || ''),
      inputs,
    };
    setLoading(true);
    setError('');
    try {
      const response = await authFetch('/api/listing-projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || '创建失败');
      router.push(`/listing-projects/detail?id=${data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <h1 className="text-3xl font-bold">新建 Listing 项目</h1>
      <p className="mt-2 text-slate-600">用于生成标题、五点、描述、Search Terms、图片 Prompt 和 A+ 方案。先填少量硬信息，同行链接到详情页再补。</p>
      <div className="mt-6">
        <ListingSubnav />
      </div>

      <form className="mt-6 space-y-5 rounded-lg border bg-white p-5" onSubmit={submit}>
        <section>
          <h2 className="text-xl font-bold">基础信息</h2>
          <div className="mt-3 grid gap-4 md:grid-cols-2">
            <Input name="product_name" label="产品名称" required />
            <Input name="marketplace" label="站点" defaultValue="US" />
            <Input name="brand" label="品牌，可选" />
            <Input name="category" label="类目，可选" />
            <Input name="target_price" label="目标售价，可选" type="number" />
            <Input name="fulfillment_method" label="发货方式，可选" placeholder="FBM / FBA / Both" />
            <Textarea name="notes" label="补充备注，可选" />
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold">产品资料 / 关键词 / 合规限制</h2>
          <p className="mt-2 text-sm text-slate-500">
            这里只填系统不能瞎猜的硬信息。目标客户、卖点方向、长尾词、兼容词、避开词和差异化方向，后续会根据同行参考资料自动分析。
          </p>
          <div className="mt-3 grid gap-4 md:grid-cols-2">
            {inputFields.map(([name, label]) => (
              <Textarea key={name} name={name} label={label} />
            ))}
          </div>
        </section>

        {error && <div className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}
        <button className="rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50" disabled={loading}>
          {loading ? '创建中...' : '创建项目'}
        </button>
      </form>
    </main>
  );
}

function Input({ name, label, type = 'text', defaultValue = '', placeholder = '', required = false }: { name: string; label: string; type?: string; defaultValue?: string; placeholder?: string; required?: boolean }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {label}
      <input className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2" name={name} type={type} defaultValue={defaultValue} placeholder={placeholder} required={required} />
    </label>
  );
}

function Textarea({ name, label }: { name: string; label: string }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {label}
      <textarea className="mt-2 min-h-24 w-full rounded-md border border-slate-300 px-3 py-2" name={name} />
    </label>
  );
}
