'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiGet, authFetch, readApiJson } from '@/lib/api';
import ListingSubnav from './listing-subnav';

type Project = {
  id: number;
  project_name: string;
  project_type?: string;
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
  const [deletingId, setDeletingId] = useState<number | null>(null);
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
      if (!response.ok && response.status !== 404) throw new Error(data.detail || '复制失败');
      if (!response.ok && response.status === 404) {
        const detailResponse = await authFetch(`/api/listing-projects/${projectId}`, { cache: 'no-store' });
        const detail = await readApiJson(detailResponse);
        if (!detailResponse.ok) throw new Error(detail.detail || '读取项目失败，无法复制');
        const project = detail.project || {};
        const createResponse = await authFetch('/api/listing-projects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_name: `${project.project_name || project.product_name || 'Listing 项目'} - 副本`,
            project_type: project.project_type || 'manual_input',
            marketplace: project.marketplace || 'US',
            brand: project.brand || '',
            category: project.category || '',
            product_name: project.product_name || '',
            target_price: project.target_price || '',
            fulfillment_method: project.fulfillment_method || '',
            notes: project.notes || '',
            inputs: detail.inputs || {},
          }),
        });
        const created = await readApiJson(createResponse);
        if (!createResponse.ok) throw new Error(created.detail || '复制失败');
        router.push(`/listing-projects/detail?id=${created.id}`);
        return;
      }
      router.push(`/listing-projects/detail?id=${data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '复制失败');
      setCopyingId(null);
    }
  }

  async function deleteProject(project: Project) {
    const ok = window.confirm(
      `确定删除这个 Listing 项目吗？\n\n${project.project_name}\n\n删除后会同时删除：产品输入信息、同行参考资料、Listing 文案版本、图片 Prompt 版本、A+ 页面版本。这个操作不能恢复。`
    );
    if (!ok) return;
    setDeletingId(project.id);
    setError('');
    try {
      const response = await authFetch(`/api/listing-projects/${project.id}`, { method: 'DELETE' });
      const data = await readApiJson(response);
      if (!response.ok) throw new Error(data.detail || '删除失败');
      setItems((current) => current.filter((item) => item.id !== project.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeletingId(null);
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
        {error && <p className="mb-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {!loading && (
          <>
            <table className="w-full text-left text-sm">
              <thead className="border-b text-slate-500">
                <tr>
                  <th className="py-3">项目</th>
                  <th>类型</th>
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
                    <td>
                      <span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.project_type === 'competitor_parse' ? 'bg-purple-50 text-purple-700' : 'bg-blue-50 text-blue-700'}`}>
                        {projectTypeLabel(item.project_type)}
                      </span>
                      <div className="mt-1 max-w-32 text-xs text-slate-500">{projectTypeHelp(item.project_type)}</div>
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
                        <button
                          className="font-semibold text-red-700 disabled:opacity-50"
                          disabled={deletingId === item.id}
                          onClick={() => deleteProject(item)}
                          type="button"
                        >
                          {deletingId === item.id ? '删除中...' : '删除'}
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

function projectTypeLabel(value?: string) {
  if (value === 'competitor_parse') return '竞品解析型';
  return '资料录入型';
}

function projectTypeHelp(value?: string) {
  if (value === 'competitor_parse') return '竞品链接解析后生成';
  return '自有资料加同行参考';
}
