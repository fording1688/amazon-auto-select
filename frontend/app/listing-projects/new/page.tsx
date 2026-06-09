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
  const [amazonLoading, setAmazonLoading] = useState(false);
  const [error, setError] = useState('');
  const [projectType, setProjectType] = useState<'manual_input' | 'competitor_parse'>('manual_input');
  const [amazonInput, setAmazonInput] = useState('');
  const [amazonMessage, setAmazonMessage] = useState('');
  const [parsedProduct, setParsedProduct] = useState<any>(null);
  const [basic, setBasic] = useState<Record<string, string>>({
    product_name: '',
    marketplace: 'US',
    brand: '',
    category: '',
    target_price: '',
    fulfillment_method: '',
    notes: '',
  });
  const [inputs, setInputs] = useState<Record<string, string>>(
    Object.fromEntries(inputFields.map(([key]) => [key, '']))
  );

  function setBasicField(name: string, value: string) {
    setBasic((current) => ({ ...current, [name]: value }));
  }

  function setInputField(name: string, value: string) {
    setInputs((current) => ({ ...current, [name]: value }));
  }

  function fillFromProduct(product: any) {
    const facts = product?.normalizedFacts || {};
    const category = Array.isArray(product?.categories) ? product.categories.filter(Boolean).join(' > ') : '';
    const sizeParts = [
      facts.diameter ? `Diameter: ${facts.diameter}` : '',
      facts.thickness ? `Thickness: ${facts.thickness}` : '',
      facts.arborHole ? `Arbor/Hole: ${facts.arborHole}` : '',
      facts.grit ? `Grit: ${facts.grit}` : '',
    ].filter(Boolean);
    const about = Array.isArray(product?.aboutItem) ? product.aboutItem.filter(Boolean) : [];
    const sourceNote = [
      product?.asin ? `Amazon ASIN: ${product.asin}` : '',
      product?.productLink ? `Source: ${product.productLink}` : '',
      product?.rating ? `Rating: ${product.rating}` : '',
      product?.reviews ? `Reviews: ${product.reviews}` : '',
      product?.availability ? `Availability: ${product.availability}` : '',
    ].filter(Boolean).join('\n');
    setBasic((current) => ({
      ...current,
      product_name: product?.title || facts.productName || current.product_name,
      marketplace: domainToMarketplace(product?.amazonDomain) || current.marketplace || 'US',
      brand: product?.brand || facts.brand || current.brand,
      category: category || facts.productCategory || current.category,
      target_price: product?.extractedPrice ? String(product.extractedPrice) : current.target_price,
      notes: [current.notes, sourceNote].filter(Boolean).join(current.notes && sourceNote ? '\n\n' : ''),
    }));
    setInputs((current) => ({
      ...current,
      size: sizeParts.join('\n') || current.size,
      material: facts.material || current.material,
      color: facts.color || current.color,
      quantity: facts.quantity || current.quantity,
      compatibility: facts.compatibilityTarget || current.compatibility,
      package_includes: facts.packageIncludes || current.package_includes,
      use_cases: about.slice(0, 3).join('\n') || current.use_cases,
      main_keywords: deriveKeywords(product?.title || facts.productName || current.main_keywords),
      compliance_notes: current.compliance_notes || 'Do not claim official, original, authorized, universal fit, or guaranteed compatibility unless proven. Use competitor data only as reference; verify all specs before publishing.',
    }));
  }

  async function autofillFromAmazon() {
    const value = amazonInput.trim();
    if (!value) {
      setAmazonMessage('请输入 Amazon 链接或 ASIN。');
      return;
    }
    setAmazonLoading(true);
    setAmazonMessage('正在通过 SerpApi 获取商品详情...');
    try {
      const isUrl = /^https?:\/\//i.test(value) || value.includes('amazon.');
      const response = await authFetch(isUrl ? '/api/serpapi/amazon-product-by-url' : '/api/serpapi/amazon-product', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(isUrl ? { url: value } : { asin: value, amazonDomain: 'amazon.com' }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '获取商品详情失败');
      const product = result.product || result;
      setParsedProduct(product);
      fillFromProduct(product);
      setAmazonMessage(projectType === 'competitor_parse'
        ? '已解析竞品并补全表单。保存后系统会把这条竞品资料写入同行参考，生成内容时会带给模型。'
        : '已根据 SerpApi 商品详情补全表单。请检查尺寸、材质、包装和兼容信息，确认后再保存。');
    } catch (err) {
      setAmazonMessage(err instanceof Error ? err.message : '获取商品详情失败');
    } finally {
      setAmazonLoading(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const productName = String(basic.product_name || '').trim();
    if (projectType === 'competitor_parse' && !parsedProduct) {
      setError('竞品解析型请先输入竞品 Amazon 链接或 ASIN，并点击“解析竞品并补全”。');
      return;
    }
    const payload = {
      project_name: `${productName || 'Listing 项目'} ${new Date().toISOString().slice(0, 10)}`,
      project_type: projectType,
      marketplace: basic.marketplace || 'US',
      brand: basic.brand || '',
      category: basic.category || '',
      product_name: productName,
      target_price: basic.target_price || '',
      fulfillment_method: basic.fulfillment_method || '',
      notes: basic.notes || '',
      inputs,
      ...(projectType === 'competitor_parse' && parsedProduct
        ? { competitor_reference: productToCompetitorReference(parsedProduct) }
        : {}),
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

      <section className="mt-6 rounded-lg border bg-white p-5">
        <h2 className="text-xl font-bold">选择创建方式</h2>
        <p className="mt-2 text-sm text-slate-600">先确定这个 Listing 项目从哪里来，后面列表里也会按这个类型展示。</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <button
            className={`rounded-lg border p-4 text-left transition ${projectType === 'manual_input' ? 'border-blue-600 bg-blue-50 ring-2 ring-blue-100' : 'border-slate-200 bg-white hover:bg-slate-50'}`}
            onClick={() => setProjectType('manual_input')}
            type="button"
          >
            <div className="text-lg font-bold">资料录入型</div>
            <p className="mt-2 text-sm text-slate-600">你输入自己的产品规格、关键词和少量硬信息，再补充同行参考链接。适合已有供应链或准备上架的产品。</p>
          </button>
          <button
            className={`rounded-lg border p-4 text-left transition ${projectType === 'competitor_parse' ? 'border-purple-600 bg-purple-50 ring-2 ring-purple-100' : 'border-slate-200 bg-white hover:bg-slate-50'}`}
            onClick={() => setProjectType('competitor_parse')}
            type="button"
          >
            <div className="text-lg font-bold">竞品解析型</div>
            <p className="mt-2 text-sm text-slate-600">直接粘贴竞品 Amazon 链接或 ASIN，系统通过 SerpApi 解析商品 JSON，保存为同行参考后再交给模型生成内容。</p>
          </button>
        </div>
      </section>

      <section className="mt-6 rounded-lg border border-blue-100 bg-blue-50 p-5">
        <h2 className="text-xl font-bold text-slate-900">{projectType === 'competitor_parse' ? '竞品链接解析' : '用 Amazon 链接 / ASIN 自动补全'}</h2>
        <p className="mt-2 text-sm text-slate-600">
          {projectType === 'competitor_parse'
            ? '输入一个竞品 Amazon 链接或 ASIN。系统会抓取结构化信息，补全基础资料，并在创建项目时自动加入同行参考资料。'
            : '输入你自己的产品链接、供应商给的 Amazon 参考链接，或 ASIN。系统会通过后端 SerpApi 获取结构化商品数据，只补全下面表单，不会自动保存。'}
        </p>
        <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto]">
          <input
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            placeholder="https://www.amazon.com/dp/B0... 或 B0..."
            value={amazonInput}
            onChange={(event) => setAmazonInput(event.target.value)}
          />
          <button
            className="rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50"
            disabled={amazonLoading || loading}
            onClick={autofillFromAmazon}
            type="button"
          >
            {amazonLoading ? '获取中...' : projectType === 'competitor_parse' ? '解析竞品并补全' : '获取并补全'}
          </button>
        </div>
        {amazonMessage && (
          <p className={`mt-3 text-sm font-medium ${amazonMessage.includes('失败') || amazonMessage.includes('配置') || amazonMessage.includes('请输入') ? 'text-red-700' : 'text-emerald-700'}`}>
            {amazonMessage}
          </p>
        )}
      </section>

      <form className="mt-6 space-y-5 rounded-lg border bg-white p-5" onSubmit={submit}>
        <section>
          <h2 className="text-xl font-bold">基础信息</h2>
          <div className="mt-3 grid gap-4 md:grid-cols-2">
            <Input name="product_name" label="产品名称" required value={basic.product_name} onChange={setBasicField} />
            <Input name="marketplace" label="站点" value={basic.marketplace} onChange={setBasicField} />
            <Input name="brand" label="品牌，可选" value={basic.brand} onChange={setBasicField} />
            <Input name="category" label="类目，可选" value={basic.category} onChange={setBasicField} />
            <Input name="target_price" label="目标售价，可选" type="number" value={basic.target_price} onChange={setBasicField} />
            <Input name="fulfillment_method" label="发货方式，可选" placeholder="FBM / FBA / Both" value={basic.fulfillment_method} onChange={setBasicField} />
            <Textarea name="notes" label="补充备注，可选" value={basic.notes} onChange={setBasicField} />
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold">产品资料 / 关键词 / 合规限制</h2>
          <p className="mt-2 text-sm text-slate-500">
            这里只填系统不能瞎猜的硬信息。目标客户、卖点方向、长尾词、兼容词、避开词和差异化方向，后续会根据同行参考资料自动分析。
          </p>
          <div className="mt-3 grid gap-4 md:grid-cols-2">
            {inputFields.map(([name, label]) => (
              <Textarea key={name} name={name} label={label} value={inputs[name]} onChange={setInputField} />
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

function domainToMarketplace(domain?: string) {
  const map: Record<string, string> = {
    'amazon.com': 'US',
    'amazon.ca': 'CA',
    'amazon.co.uk': 'UK',
    'amazon.de': 'DE',
    'amazon.fr': 'FR',
    'amazon.it': 'IT',
    'amazon.es': 'ES',
    'amazon.co.jp': 'JP',
    'amazon.com.au': 'AU',
  };
  return map[String(domain || '').toLowerCase()] || '';
}

function deriveKeywords(title?: string) {
  const stop = new Set(['with', 'from', 'this', 'that', 'for', 'and', 'the', 'inch', 'pack']);
  const words = String(title || '')
    .toLowerCase()
    .match(/[a-z][a-z0-9+-]{2,}/g) || [];
  return Array.from(new Set(words.filter((word) => !stop.has(word)))).slice(0, 12).join(', ');
}

function productToCompetitorReference(product: any) {
  const bullets = Array.isArray(product?.aboutItem) ? product.aboutItem.filter(Boolean).join('\n') : '';
  const imageNotes = [
    product?.mainImage ? `Main image: ${product.mainImage}` : '',
    Array.isArray(product?.images) && product.images.length ? `Image count: ${product.images.length}` : '',
  ].filter(Boolean).join('\n');
  return {
    competitor_url: product?.productLink || '',
    competitor_title: product?.title || '',
    competitor_bullets: bullets,
    competitor_description: product?.description || '',
    competitor_price: product?.extractedPrice || '',
    competitor_rating: product?.rating || '',
    competitor_review_count: product?.reviews || '',
    competitor_image_notes: imageNotes,
    competitor_aplus_notes: Array.isArray(product?.aplus) ? product.aplus.join('\n') : '',
    what_to_reference: '参考公开商品信息中的关键词、规格表达、图片模块结构、卖点层级和买家关注点；不要复制原文、图片、Logo、品牌或版权元素。',
    what_to_avoid: '不要复制竞品标题、五点、图片构图、品牌词、Logo、授权/官方等高风险表达；所有尺寸、材质、兼容性以自己的产品事实为准。',
  };
}

function Input({ name, label, type = 'text', value = '', placeholder = '', required = false, onChange }: { name: string; label: string; type?: string; value?: string; placeholder?: string; required?: boolean; onChange: (name: string, value: string) => void }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {label}
      <input className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2" name={name} type={type} value={value} placeholder={placeholder} required={required} onChange={(event) => onChange(name, event.target.value)} />
    </label>
  );
}

function Textarea({ name, label, value = '', onChange }: { name: string; label: string; value?: string; onChange: (name: string, value: string) => void }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {label}
      <textarea className="mt-2 min-h-24 w-full rounded-md border border-slate-300 px-3 py-2" name={name} value={value} onChange={(event) => onChange(name, event.target.value)} />
    </label>
  );
}
