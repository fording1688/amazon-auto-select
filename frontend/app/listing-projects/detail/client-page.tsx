'use client';

import { FormEvent, useEffect, useState } from 'react';
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

export default function ListingProjectDetailPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [projectMessage, setProjectMessage] = useState('');
  const [competitorMessage, setCompetitorMessage] = useState('');

  async function load() {
    const response = await authFetch(`/api/listing-projects/${params.id}`);
    setData(await response.json());
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, [params.id]);

  async function generate(path: string, label: string) {
    setLoading(true);
    setMessage('');
    try {
      const response = await authFetch(`/api/listing-projects/${params.id}/${path}`, { method: 'POST' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '生成失败');
      setMessage(`${label} 已生成并保存版本。`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '生成失败');
    } finally {
      setLoading(false);
    }
  }

  async function saveProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const inputs: Record<string, string> = {};
    inputFields.forEach(([key]) => {
      inputs[key] = String(form.get(key) || '');
    });
    const payload = {
      project_name: String(form.get('project_name') || ''),
      marketplace: String(form.get('marketplace') || ''),
      brand: String(form.get('brand') || ''),
      category: String(form.get('category') || ''),
      product_name: String(form.get('product_name') || ''),
      target_price: String(form.get('target_price') || ''),
      fulfillment_method: String(form.get('fulfillment_method') || ''),
      notes: String(form.get('notes') || ''),
      inputs,
    };
    setLoading(true);
    setProjectMessage('正在保存草稿...');
    try {
      const response = await authFetch(`/api/listing-projects/${params.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '保存失败');
      setData(result);
      setProjectMessage('草稿已保存。');
    } catch (err) {
      setProjectMessage(err instanceof Error ? err.message : '保存失败');
    } finally {
      setLoading(false);
    }
  }

  async function addCompetitor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const existingUrls = new Set((data?.competitors || []).map((item: any) => normalizeUrl(item.competitor_url)).filter(Boolean));
    const seenUrls = new Set<string>();
    const urls = String(form.get('competitor_urls') || '')
      .split(/\n+/)
      .map((url) => url.trim())
      .filter(Boolean)
      .filter((url) => {
        const key = normalizeUrl(url);
        if (!key || seenUrls.has(key) || existingUrls.has(key)) return false;
        seenUrls.add(key);
        return true;
      });
    if (!urls.length) {
      setCompetitorMessage('没有新的同行链接可保存，重复链接已自动跳过。');
      return;
    }
    const common = {
      what_to_reference: String(form.get('what_to_reference') || ''),
      what_to_avoid: String(form.get('what_to_avoid') || ''),
    };
    setLoading(true);
    setCompetitorMessage('正在保存同行链接...');
    try {
      for (const url of urls) {
        const response = await authFetch(`/api/listing-projects/${params.id}/competitors`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ competitor_url: url, ...common }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || '保存失败');
      }
      formElement.reset();
      await load();
      setCompetitorMessage(`已保存 ${urls.length} 个同行链接，下面的同行参考列表已更新。`);
    } catch (err) {
      setCompetitorMessage(err instanceof Error ? err.message : '保存失败');
    } finally {
      setLoading(false);
    }
  }

  async function deleteCompetitor(competitorId: number) {
    if (!window.confirm('确定删除这个同行参考吗？')) return;
    setLoading(true);
    setCompetitorMessage('正在删除同行参考...');
    try {
      const response = await authFetch(`/api/listing-projects/${params.id}/competitors/${competitorId}`, { method: 'DELETE' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '删除失败');
      await load();
      setCompetitorMessage('已删除同行参考。');
    } catch (err) {
      setCompetitorMessage(err instanceof Error ? err.message : '删除失败');
    } finally {
      setLoading(false);
    }
  }

  if (!data?.project) {
    return <main className="mx-auto max-w-7xl px-6 py-8"><p className="text-slate-500">加载中...</p></main>;
  }

  const project = data.project;
  const isDraft = project.status === 'draft';
  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-6 border-b border-slate-200 pb-5">
        <p className="text-sm font-medium text-blue-700">Listing 生成模块</p>
        <h1 className="text-3xl font-bold">{project.project_name}</h1>
        <p className="mt-2 text-slate-600">
          {project.product_name || '-'} · {project.marketplace} · <span className={isDraft ? 'font-semibold text-emerald-700' : 'font-semibold text-slate-700'}>{isDraft ? '草稿可编辑' : '已生成，基础信息已锁定'}</span>
        </p>
      </header>
      <ListingSubnav projectId={params.id} />

      <section className="mb-6 grid gap-4 md:grid-cols-4">
        <Metric label="Marketplace" value={project.marketplace} />
        <Metric label="Brand" value={project.brand || '-'} />
        <Metric label="Category" value={project.category || '-'} />
        <Metric label="Target Price" value={project.target_price ? `$${project.target_price}` : '-'} />
      </section>

      <section className="mb-6 rounded-lg border bg-white p-5" id="generate">
        <h2 className="text-xl font-bold">生成操作</h2>
        <p className="mt-2 text-sm text-slate-600">生成结果都会保存为新版本，不会覆盖旧内容。</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button className="rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50" disabled={loading} onClick={() => generate('generate-listing', 'Listing 文案')}>生成 Listing 文案</button>
          <button className="rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50" disabled={loading} onClick={() => generate('generate-image-prompts', '图片 Prompt')}>生成图片 Prompt</button>
          <button className="rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50" disabled={loading} onClick={() => generate('generate-aplus', 'A+ 页面方案')}>生成 A+ 页面</button>
        </div>
        {message && <div className="mt-4 rounded bg-slate-50 p-3 text-sm text-slate-700">{message}</div>}
      </section>

      <section className="mb-6 grid gap-6 lg:grid-cols-2" id="competitors">
        <Panel title="产品输入信息">
          {isDraft ? (
            <ProjectDraftForm data={data} loading={loading} message={projectMessage} onSubmit={saveProject} />
          ) : (
            <>
              <p className="mb-3 rounded bg-amber-50 p-3 text-sm text-amber-800">
                这个项目已经生成过内容，基础信息已锁定。需要改产品资料时，请在项目列表点击“复制基本信息”，新建一个草稿再修改。
              </p>
              <InfoBlock data={data.inputs || {}} />
            </>
          )}
        </Panel>
        <Panel title="同行参考资料录入">
          <form className="space-y-3" onSubmit={addCompetitor}>
            <Textarea name="competitor_urls" label="Competitor URLs，一行一个，可一次粘贴多个" />
            <Textarea name="what_to_reference" label="想参考什么，可选" />
            <Textarea name="what_to_avoid" label="不想参考什么，可选" />
            <p className="text-sm text-slate-500">
              第一版只需要粘贴同行链接。标题、五点、图片和 A+ 信息后续会接 Amazon 数据 API 自动抓取，不让你手工填。
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <button className="rounded-md border border-blue-700 px-4 py-2 font-semibold text-blue-700 disabled:opacity-50" disabled={loading}>
                {loading ? '保存中...' : '保存同行参考'}
              </button>
              {competitorMessage && (
                <span className={`text-sm font-medium ${competitorMessage.includes('失败') || competitorMessage.includes('请至少') ? 'text-red-700' : 'text-emerald-700'}`}>
                  {competitorMessage}
                </span>
              )}
            </div>
          </form>
        </Panel>
      </section>

      <Panel title={`同行参考资料 (${data.competitors?.length || 0})`}>
        <div className="grid gap-3 md:grid-cols-2">
          {(data.competitors || []).map((item: any) => (
            <div className="rounded border bg-slate-50 p-3" key={item.id}>
              <div className="flex items-start justify-between gap-3">
                <div className="font-semibold text-slate-900">{item.competitor_title || compactUrl(item.competitor_url) || `Reference #${item.id}`}</div>
                <button
                  className="shrink-0 rounded border border-red-200 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                  disabled={loading}
                  onClick={() => deleteCompetitor(item.id)}
                  type="button"
                >
                  删除
                </button>
              </div>
              {item.competitor_url && (
                <a className="mt-1 block break-all text-xs text-blue-700 hover:underline" href={item.competitor_url} target="_blank" rel="noreferrer">
                  {item.competitor_url}
                </a>
              )}
              <p className="mt-2 text-sm text-slate-600">{item.what_to_reference || '仅作为关键词、结构和卖点参考，不复制文案。'}</p>
              <p className="mt-1 text-xs text-slate-500">{item.what_to_avoid || '避免复制图片、Logo、品牌和版权元素。'}</p>
            </div>
          ))}
        </div>
      </Panel>

      <div id="versions">
      <Panel title="Listing 版本管理">
        <div className="space-y-4">
          {(data.listing_versions || []).map((item: any) => <ListingCard item={item} key={item.id} />)}
          {!data.listing_versions?.length && <p className="text-slate-500">还没有 Listing 版本，点击“生成 Listing 文案”。</p>}
        </div>
      </Panel>
      </div>

      <div id="image-prompts">
      <Panel title="图片 Prompt 版本">
        <div className="space-y-4">
          {(data.image_prompt_versions || []).map((item: any) => <PromptCard item={item} key={item.id} />)}
          {!data.image_prompt_versions?.length && <p className="text-slate-500">还没有图片 Prompt，点击“生成图片 Prompt”。</p>}
        </div>
      </Panel>
      </div>

      <div id="aplus">
      <Panel title="A+ 页面版本">
        <div className="space-y-4">
          {(data.aplus_versions || []).map((item: any) => <AplusCard item={item} key={item.id} />)}
          {!data.aplus_versions?.length && <p className="text-slate-500">还没有 A+ 版本，点击“生成 A+ 页面”。</p>}
        </div>
      </Panel>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border bg-white p-4"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 font-bold">{value}</p></div>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mb-6 rounded-lg border bg-white p-5"><h2 className="mb-4 text-xl font-bold">{title}</h2>{children}</section>;
}

function ProjectDraftForm({ data, loading, message, onSubmit }: { data: any; loading: boolean; message: string; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  const project = data.project || {};
  const inputs = data.inputs || {};
  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <div className="grid gap-3 md:grid-cols-2">
        <Input name="project_name" label="项目名称" defaultValue={project.project_name || ''} required />
        <Input name="product_name" label="产品名称" defaultValue={project.product_name || ''} required />
        <Input name="marketplace" label="站点" defaultValue={project.marketplace || 'US'} />
        <Input name="brand" label="品牌，可选" defaultValue={project.brand || ''} />
        <Input name="category" label="类目，可选" defaultValue={project.category || ''} />
        <Input name="target_price" label="目标售价，可选" type="number" defaultValue={project.target_price || ''} />
        <Input name="fulfillment_method" label="发货方式，可选" defaultValue={project.fulfillment_method || ''} placeholder="FBM / FBA / Both" />
      </div>
      <Textarea name="notes" label="补充备注，可选" defaultValue={project.notes || ''} />
      <div className="grid gap-3 md:grid-cols-2">
        {inputFields.map(([name, label]) => (
          <Textarea key={name} name={name} label={label} defaultValue={inputs?.[name] || ''} />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button className="rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50" disabled={loading}>
          {loading ? '保存中...' : '保存草稿'}
        </button>
        {message && <span className={`text-sm font-medium ${message.includes('失败') || message.includes('锁定') ? 'text-red-700' : 'text-emerald-700'}`}>{message}</span>}
      </div>
    </form>
  );
}

function Input({ name, label, type = 'text', defaultValue = '', placeholder = '', required = false }: { name: string; label: string; type?: string; defaultValue?: string | number; placeholder?: string; required?: boolean }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {label}
      <input className="mt-1 w-full rounded border px-3 py-2" name={name} type={type} defaultValue={defaultValue} placeholder={placeholder} required={required} />
    </label>
  );
}

function Textarea({ name, label, defaultValue = '' }: { name: string; label: string; defaultValue?: string }) {
  return <label className="block text-sm font-semibold text-slate-700">{label}<textarea className="mt-1 min-h-20 w-full rounded border px-3 py-2" name={name} defaultValue={defaultValue} /></label>;
}

function compactUrl(url?: string) {
  if (!url) return '';
  try {
    const parsed = new URL(url);
    const asin = parsed.pathname.match(/\/dp\/([A-Z0-9]{10})/i)?.[1];
    return asin ? `Amazon ASIN ${asin}` : parsed.hostname + parsed.pathname.slice(0, 45);
  } catch {
    return url.length > 70 ? `${url.slice(0, 70)}...` : url;
  }
}

function normalizeUrl(url?: string) {
  return String(url || '').trim().replace(/\/+$/, '').toLowerCase();
}

function InfoBlock({ data }: { data: Record<string, any> }) {
  const entries = Object.entries(data).filter(([key, value]) => !['id', 'project_id', 'created_at', 'updated_at'].includes(key) && value);
  if (!entries.length) return <p className="text-slate-500">暂无输入信息。</p>;
  return <dl className="grid gap-2 text-sm">{entries.map(([key, value]) => <div className="rounded bg-slate-50 p-2" key={key}><dt className="text-slate-500">{key}</dt><dd className="mt-1 whitespace-pre-wrap font-medium">{String(value)}</dd></div>)}</dl>;
}

function ListingCard({ item }: { item: any }) {
  return (
    <article className="rounded border bg-slate-50 p-4">
      <h3 className="font-bold">{item.version_name}</h3>
      <p className="mt-2 font-semibold">{item.title}</p>
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm">
        {[item.bullet_1, item.bullet_2, item.bullet_3, item.bullet_4, item.bullet_5].map((bullet, index) => <li key={index}>{bullet}</li>)}
      </ol>
      <p className="mt-3 whitespace-pre-wrap text-sm">{item.description}</p>
      <div className="mt-3 rounded bg-white p-3 text-sm"><strong>Backend Search Terms:</strong> {item.backend_search_terms || '-'}</div>
      <p className="mt-2 text-xs text-slate-500">SEO {item.seo_score || '-'} · Conversion {item.conversion_score || '-'} · {item.compliance_risk_notes}</p>
    </article>
  );
}

function PromptCard({ item }: { item: any }) {
  return (
    <article className="rounded border bg-slate-50 p-4">
      <h3 className="font-bold">{item.version_name}</h3>
      <p className="mt-1 text-sm text-slate-600">{item.image_goal}</p>
      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <CopyBlock title="英文 Prompt" text={item.prompt_en} />
        <CopyBlock title="中文 Prompt" text={item.prompt_cn} />
      </div>
      <CopyBlock title="Negative Prompt" text={item.negative_prompt} />
      <p className="mt-2 text-sm text-slate-500">图片中文字：{item.image_text || '-'} · 尺寸建议：{item.size_recommendation || '-'}</p>
    </article>
  );
}

function AplusCard({ item }: { item: any }) {
  return (
    <article className="rounded border bg-slate-50 p-4">
      <h3 className="font-bold">{item.version_name}</h3>
      <CopyBlock title="Banner Copy" text={item.banner_copy} />
      <CopyBlock title="Brand Story" text={item.brand_story_copy} />
      <CopyBlock title="Feature Modules" text={item.feature_modules} />
      <CopyBlock title="Specification Module" text={item.specification_module} />
      <CopyBlock title="Application Module" text={item.application_module} />
      <CopyBlock title="Comparison Chart" text={item.comparison_chart} />
      <CopyBlock title="Image Prompt Notes" text={item.image_prompt_notes} />
    </article>
  );
}

function CopyBlock({ title, text }: { title: string; text?: string }) {
  return <div className="mt-3 rounded bg-white p-3 text-sm"><div className="mb-1 font-semibold text-slate-700">{title}</div><pre className="whitespace-pre-wrap font-sans text-slate-700">{text || '-'}</pre></div>;
}
