'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiGet, authFetch, readApiJson } from '@/lib/api';
import ListingSubnav from './listing-subnav';

type Project = {
  id: number;
  project_name: string;
  marketplace: string;
  brand?: string;
  category?: string;
  product_name?: string;
  target_price?: number;
  fulfillment_method?: string;
  status: string;
  updated_at: string;
};

export default function ListingProjectsPage() {
  const router = useRouter();
  const [items, setItems] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [copyingId, setCopyingId] = useState<number | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiGet<{ items: Project[] }>('/api/listing-projects')
      .then((data) => setItems(data.items || []))
      .catch((err) => setError(err instanceof Error ? err.message : '加载失败'))
      .finally(() => setLoading(false));
  }, []);

  async function copyProject(projectId: number) {
    setCopyingId(projectId);
    setError('');
    try {
      const response = await authFetch(`/api/listing-projects/${projectId}/copy`, { method: 'POST' });
      const data = await readApiJson(response);
      if (!response.ok) throw new Error(data.detail || '复制失败');
      router.push(`/listing-projects/detail?id=${data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '复制失败');
      setCopyingId(null);
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-6 flex flex-col gap-3 border-b border-slate-200 pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-medium text-blue-700">Listing 生成模块</p>
          <h1 className="text-3xl font-bold">Listing 项目列表</h1>
          <p className="mt-2 text-slate-600">这里只显示当前登录用户自己的 Listing 项目。</p>
        </div>
        <Link className="rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white" href="/listing-projects/new">新建 Listing 项目</Link>
      </header>
      <ListingSubnav />

      <section className="overflow-x-auto rounded-lg border bg-white p-4">
        {loading && <p className="py-8 text-center text-slate-500">加载中...</p>}
        {error && <p className="py-8 text-center text-red-600">{error}</p>}
        {!loading && !error && (
          <>
            <table className="w-full text-left text-sm">
              <thead className="border-b text-slate-500">
                <tr>
                  <th className="py-3">项目</th>
                  <th>产品</th>
                  <th>类目</th>
                  <th>价格</th>
                  <th>状态</th>
                  <th>更新时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr className="border-b align-top" key={item.id}>
                    <td className="py-3 font-semibold">
                      {item.project_name}
                      <div className="mt-1 text-xs text-slate-500">{item.marketplace} · {item.brand || 'No Brand'}</div>
                    </td>
                    <td>{item.product_name || '-'}</td>
                    <td>{item.category || '-'}</td>
                    <td>{item.target_price ? `$${item.target_price}` : '-'}</td>
                    <td><span className="rounded bg-slate-100 px-2 py-1 text-xs">{item.status}</span></td>
                    <td>{item.updated_at ? item.updated_at.slice(0, 10) : '-'}</td>
                    <td>
                      <div className="flex flex-wrap gap-2">
                        <Link className="font-semibold text-blue-700" href={`/listing-projects/detail?id=${item.id}`}>打开</Link>
                        <button
                          className="font-semibold text-slate-700 disabled:opacity-50"
                          disabled={copyingId === item.id}
                          onClick={() => copyProject(item.id)}
                          type="button"
                        >
                          {copyingId === item.id ? '复制中...' : '复制基本信息'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!items.length && <p className="py-8 text-center text-slate-500">暂无 Listing 项目，先新建一个产品内容项目。</p>}
          </>
        )}
      </section>
    </main>
  );
}
