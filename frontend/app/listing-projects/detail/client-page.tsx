'use client';

import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import { authFetch } from '@/lib/api';
import type { ReferenceInsights, SerpApiAmazonSearchItem, SimilarProductReference } from '@/lib/amazon-reference-types';
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

const modelOptions = [
  { label: '使用后端默认模型', value: '' },
  { label: 'OpenAI GPT-4o mini - 便宜快', value: 'openai/gpt-4o-mini' },
  { label: 'OpenAI GPT-4o - 文案更稳', value: 'openai/gpt-4o' },
  { label: 'OpenAI GPT-4.1 mini - 性价比', value: 'openai/gpt-4.1-mini' },
  { label: 'Claude 3.5 Sonnet - 长文案强', value: 'anthropic/claude-3.5-sonnet' },
  { label: 'Gemini 2.5 Pro - 推理强', value: 'google/gemini-2.5-pro' },
  { label: 'DeepSeek Chat - 便宜中文好', value: 'deepseek/deepseek-chat' },
] as const;

const listingImageTypes = [
  { value: 'main_image', label: '主图', placeholder: '例如：主图 V1 / 白底主图' },
  { value: 'dimension', label: '尺寸图', placeholder: '例如：尺寸图英文版 / 规格标注图' },
  { value: 'feature', label: '卖点图', placeholder: '例如：核心卖点图 / 材质卖点图' },
  { value: 'compatibility', label: '适配图', placeholder: '例如：适配型号图 / compatible-with 图' },
  { value: 'application', label: '场景图', placeholder: '例如：使用场景图 / workshop 场景' },
  { value: 'package', label: '包装图', placeholder: '例如：包装内容图 / includes 图' },
  { value: 'aplus', label: 'A+ 图片', placeholder: '例如：A+ banner / A+ 模块图' },
  { value: 'other', label: '其他', placeholder: '例如：备用图 / 待审核图' },
] as const;

const amazonCategorySuggestions = [
  'Industrial & Scientific > Abrasive & Finishing Products > Abrasive Wheels & Discs',
  'Industrial & Scientific > Cutting Tools > Band Saw Blades',
  'Industrial & Scientific > Abrasive & Finishing Products > Abrasive Discs',
  'Tools & Home Improvement > Power Tool Parts & Accessories',
  'Arts, Crafts & Sewing > Craft Supplies > Stained Glass Making',
] as const;

type AssetDraft = {
  file: File | null;
  title: string;
  notes: string;
};

type VariantDraft = {
  id: string;
  sku: string;
  value: string;
  color: string;
  price: string;
  imageType: string;
};

export default function ListingProjectDetailPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [listingModel, setListingModel] = useState('');
  const [listingCount, setListingCount] = useState(1);
  const [imageModel, setImageModel] = useState('openai/gpt-4o');
  const [imageSetCount, setImageSetCount] = useState(1);
  const [aplusModel, setAplusModel] = useState('openai/gpt-4o');
  const [aplusCount, setAplusCount] = useState(1);
  const [referenceImage, setReferenceImage] = useState<{ file_name?: string; note?: string; preview?: string; data_url?: string }>({});
  const [assetDrafts, setAssetDrafts] = useState<Record<string, AssetDraft>>({});
  const [assetInputVersion, setAssetInputVersion] = useState<Record<string, number>>({});
  const [imageAssets, setImageAssets] = useState<any[]>([]);
  const [assetMessage, setAssetMessage] = useState('');
  const [projectMessage, setProjectMessage] = useState('');
  const [competitorMessage, setCompetitorMessage] = useState('');
  const [amazonDomain, setAmazonDomain] = useState('amazon.com');
  const [referenceKeyword, setReferenceKeyword] = useState('');
  const [referenceUrlOrAsin, setReferenceUrlOrAsin] = useState('');
  const [searchResults, setSearchResults] = useState<SerpApiAmazonSearchItem[]>([]);
  const [similarReferences, setSimilarReferences] = useState<SimilarProductReference[]>([]);
  const [referenceInsights, setReferenceInsights] = useState<ReferenceInsights | null>(null);
  const [referenceMessage, setReferenceMessage] = useState('');
  const [exportBrand, setExportBrand] = useState('');
  const [exportCategory, setExportCategory] = useState('');
  const [exportListingVersionId, setExportListingVersionId] = useState('');
  const [exportMessage, setExportMessage] = useState('');
  const [variationEnabled, setVariationEnabled] = useState(false);
  const [variationTheme, setVariationTheme] = useState('SizeName');
  const [parentSku, setParentSku] = useState('');
  const [parentSkuManual, setParentSkuManual] = useState(false);
  const [manualVariantSkuIds, setManualVariantSkuIds] = useState<Record<string, boolean>>({});
  const [variants, setVariants] = useState<VariantDraft[]>([
    { id: 'v1', sku: '', value: '', color: '', price: '', imageType: 'main_image' },
    { id: 'v2', sku: '', value: '', color: '', price: '', imageType: 'main_image' },
  ]);

  async function load() {
    const response = await authFetch(`/api/listing-projects/${params.id}`);
    setData(await response.json());
  }

  async function loadImages() {
    const response = await authFetch(`/api/listing-projects/${params.id}/images`, { cache: 'no-store' });
    if (!response.ok) return;
    const result = await response.json();
    setImageAssets(result.items || []);
  }

  useEffect(() => {
    load().catch(() => undefined);
    loadImages().catch(() => undefined);
  }, [params.id]);

  useEffect(() => {
    if (!data?.project) return;
    setExportBrand((current) => current || data.project.brand || '');
    setExportCategory((current) => current || data.project.category || '');
    const firstListingVersion = data.listing_versions?.[0]?.id;
    if (!exportListingVersionId && firstListingVersion) {
      setExportListingVersionId(String(firstListingVersion));
    }
  }, [data?.project?.id, data?.project?.brand, data?.project?.category, data?.listing_versions?.length, exportListingVersionId]);

  useEffect(() => {
    const competitors = Array.isArray(data?.competitors) ? data.competitors : [];
    const shouldAutoImport = data?.project?.project_type === 'competitor_parse' || competitors.some(hasImportedCompetitorData);
    if (!shouldAutoImport) return;
    if (!competitors.length) return;
    const importedReferences: SimilarProductReference[] = competitors.map((item: any, index: number) => competitorToStructuredReference(item, index));
    setSimilarReferences((current) => {
      const existing = new Set(current.map((item) => item.id));
      const merged = [...current];
      importedReferences.forEach((item: SimilarProductReference) => {
        if (!existing.has(item.id)) merged.push(item);
      });
      return merged;
    });
    setReferenceInsights((current) => current || buildLocalReferenceInsightsFromCompetitors(competitors));
    setReferenceMessage('已自动导入保存的竞品资料；生成 Listing / 图片 Prompt / A+ 时会直接带上这些结构化参考，不需要再次调用 SerpApi。');
  }, [data?.project?.id, data?.project?.project_type, data?.competitors?.length]);

  useEffect(() => {
    if (!variationEnabled || parentSkuManual || !data?.project) return;
    const listingVersions = data?.listing_versions || [];
    const selectedListing = listingVersions.find((item: any) => String(item.id) === String(exportListingVersionId)) || listingVersions[0] || {};
    const suggested = buildParentSku(data.project, selectedListing);
    if (suggested && parentSku !== suggested) setParentSku(suggested);
  }, [variationEnabled, parentSkuManual, data?.project?.id, data?.project?.product_name, data?.project?.project_name, data?.listing_versions?.length, exportListingVersionId, parentSku]);

  useEffect(() => {
    if (!variationEnabled || !parentSku) return;
    setVariants((current) => {
      let changed = false;
      const next = current.map((item, index) => {
        if (manualVariantSkuIds[item.id]) return item;
        const suggested = buildVariantSku(parentSku, item.value || item.color || `V${index + 1}`, index + 1);
        if (item.sku === suggested) return item;
        changed = true;
        return { ...item, sku: suggested };
      });
      return changed ? next : current;
    });
  }, [variationEnabled, parentSku, variants.map((item) => `${item.id}:${item.value}:${item.color}`).join('|'), manualVariantSkuIds]);

  function confirmedFacts() {
    const project = data?.project || {};
    const inputs = data?.inputs || {};
    return {
      productName: project.product_name || project.project_name || '',
      productCategory: project.category || '',
      brand: project.brand || '',
      material: inputs.material || '',
      color: inputs.color || '',
      diameter: inputs.size || '',
      thickness: inputs.size || '',
      arborHole: inputs.compatibility || '',
      grit: inputs.size || '',
      quantity: inputs.quantity || '',
      packageIncludes: inputs.package_includes || '',
      compatibilityTarget: inputs.compatibility || '',
    };
  }

  async function generate(path: string, label: string, options: { model: string; count: number; includeReference?: boolean }) {
    setLoading(true);
    setMessage('');
    try {
      const response = await authFetch(`/api/listing-projects/${params.id}/${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: options.model,
          version_count: options.count,
          similar_product_references: similarReferences,
          reference_insights: referenceInsights || {},
          confirmed_product_facts: confirmedFacts(),
          ...(options.includeReference
            ? {
                product_reference_image: {
                  file_name: referenceImage.file_name || '',
                  note: referenceImage.note || '',
                  data_url: referenceImage.data_url || '',
                },
              }
            : {}),
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '生成失败');
      const generatedCount = Array.isArray(result.items) ? result.items.length : 1;
      setMessage(`${label} 已生成并保存 ${generatedCount} 条版本。${options.model ? `本次使用模型：${options.model}` : '本次使用后端默认模型。'}`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '生成失败');
    } finally {
      setLoading(false);
    }
  }

  function searchItemToReference(item: SerpApiAmazonSearchItem): SimilarProductReference {
    return {
      id: `amazon-${item.asin || item.linkClean || item.title}`,
      url: item.linkClean || item.link,
      asin: item.asin,
      amazonDomain,
      platform: 'amazon',
      referenceType: 'similar_product',
      permissionStatus: 'public_analysis_only',
      allowedUsage: 'public_analysis_only',
      title: item.title,
      thumbnail: item.thumbnail,
      userNotes: 'Public Amazon reference. Use only for category, keyword, visual module, and layout analysis. Do not copy.',
    };
  }

  function addReference(ref: SimilarProductReference) {
    setSimilarReferences((current) => {
      const key = ref.asin || ref.url || ref.id;
      if (current.some((item) => (item.asin || item.url || item.id) === key)) return current;
      return [...current, ref];
    });
  }

  async function addSearchResultReference(item: SerpApiAmazonSearchItem) {
    if (!item.asin) {
      addReference(searchItemToReference(item));
      setReferenceMessage('这个搜索结果没有 ASIN，已按搜索摘要加入参考。');
      return;
    }
    setLoading(true);
    setReferenceMessage(`正在获取 ${item.asin} 的商品详情 JSON...`);
    try {
      const response = await authFetch('/api/serpapi/amazon-product', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asin: item.asin, amazonDomain }),
      });
      const product = await response.json();
      if (!response.ok) throw new Error(product.detail || '获取商品详情失败');
      addReference({
        ...searchItemToReference(item),
        id: `amazon-${product.asin || item.asin}`,
        url: product.productLink || item.linkClean || item.link,
        title: product.title || item.title,
        thumbnail: product.mainImage || item.thumbnail,
        productData: product,
      });
      setReferenceMessage(`已加入 ${item.asin} 的结构化详情参考。`);
    } catch (err) {
      addReference(searchItemToReference(item));
      setReferenceMessage(err instanceof Error ? `${err.message}；已先按搜索摘要加入参考。` : '详情获取失败，已先按搜索摘要加入参考。');
    } finally {
      setLoading(false);
    }
  }

  async function searchAmazonReferences() {
    if (!referenceKeyword.trim()) {
      setReferenceMessage('先输入关键词，例如 cbn grinding wheel。');
      return;
    }
    setLoading(true);
    setReferenceMessage('正在通过 SerpApi 搜索 Amazon 商品...');
    try {
      const response = await authFetch('/api/serpapi/amazon-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: referenceKeyword, amazonDomain, page: 1 }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'SerpApi 搜索失败');
      setSearchResults(result.organicResults || []);
      setReferenceMessage(`已获取 ${result.organicResults?.length || 0} 个搜索结果。勾选适合的竞品作为结构化参考。`);
    } catch (err) {
      setReferenceMessage(err instanceof Error ? err.message : 'SerpApi 搜索失败');
    } finally {
      setLoading(false);
    }
  }

  async function fetchAmazonProductByInput() {
    const input = referenceUrlOrAsin.trim();
    if (!input) {
      setReferenceMessage('请输入 Amazon 链接或 ASIN。');
      return;
    }
    setLoading(true);
    setReferenceMessage('正在获取商品详情 JSON...');
    try {
      const isUrl = /^https?:\/\//i.test(input) || input.includes('amazon.');
      const response = await authFetch(isUrl ? '/api/serpapi/amazon-product-by-url' : '/api/serpapi/amazon-product', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(isUrl ? { url: input, amazonDomain } : { asin: input, amazonDomain }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '获取商品详情失败');
      const product = result.product || result;
      addReference(result.reference || {
        id: `amazon-${product.asin}`,
        url: product.productLink,
        asin: product.asin,
        amazonDomain: product.amazonDomain || amazonDomain,
        platform: 'amazon',
        referenceType: 'similar_product',
        permissionStatus: 'public_analysis_only',
        allowedUsage: 'public_analysis_only',
        title: product.title,
        thumbnail: product.mainImage,
        productData: product,
      });
      setReferenceMessage('已添加 1 个结构化商品参考。');
    } catch (err) {
      setReferenceMessage(err instanceof Error ? err.message : '获取商品详情失败');
    } finally {
      setLoading(false);
    }
  }

  async function analyzeReferenceInsights() {
    if (!similarReferences.length) {
      setReferenceMessage('请先添加至少 1 个参考商品。');
      return;
    }
    setLoading(true);
    setReferenceMessage('正在分析参考商品结构化 JSON...');
    try {
      const response = await authFetch('/api/references/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ references: similarReferences, confirmedFacts: confirmedFacts(), model: imageModel }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '参考分析失败');
      setReferenceInsights(result);
      setReferenceMessage(`参考分析完成。${result.model ? `模型：${result.model}` : '使用本地规则。'}`);
    } catch (err) {
      setReferenceMessage(err instanceof Error ? err.message : '参考分析失败');
    } finally {
      setLoading(false);
    }
  }

  function handleReferenceImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 3 * 1024 * 1024) {
      setMessage('主图参考图片请控制在 3MB 以内，避免模型接口拒收。');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setReferenceImage((current) => ({
        ...current,
        file_name: file.name,
        preview: URL.createObjectURL(file),
        data_url: typeof reader.result === 'string' ? reader.result : '',
      }));
    };
    reader.onerror = () => setMessage('读取主图参考失败，请换一张图片重试。');
    reader.readAsDataURL(file);
  }

  function assetDraft(type: string): AssetDraft {
    return assetDrafts[type] || { file: null, title: '', notes: '' };
  }

  function updateAssetDraft(type: string, patch: Partial<AssetDraft>) {
    setAssetDrafts((current) => ({
      ...current,
      [type]: {
        ...(current[type] || { file: null, title: '', notes: '' }),
        ...patch,
      },
    }));
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

  async function uploadAsset(imageType: string) {
    const draft = assetDraft(imageType);
    if (!draft.file) {
      setAssetMessage('请先选择一张图片。');
      return;
    }
    const form = new FormData();
    form.append('file', draft.file);
    form.append('image_type', imageType);
    form.append('title', draft.title);
    form.append('notes', draft.notes);
    setLoading(true);
    setAssetMessage(`正在上传${imageTypeLabel(imageType)}到 Cloudflare R2...`);
    try {
      const response = await authFetch(`/api/listing-projects/${params.id}/images`, {
        method: 'POST',
        body: form,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '上传失败');
      setAssetDrafts((current) => ({
        ...current,
        [imageType]: { file: null, title: '', notes: '' },
      }));
      setAssetInputVersion((current) => ({ ...current, [imageType]: (current[imageType] || 0) + 1 }));
      await loadImages();
      setAssetMessage(`${imageTypeLabel(imageType)}已上传并保存到 R2。`);
    } catch (err) {
      setAssetMessage(err instanceof Error ? err.message : '上传失败');
    } finally {
      setLoading(false);
    }
  }

  async function deleteAsset(imageId: number) {
    if (!window.confirm('确定删除这张 Listing 图片吗？R2 上的文件也会尝试删除。')) return;
    setLoading(true);
    setAssetMessage('正在删除图片...');
    try {
      const response = await authFetch(`/api/listing-projects/${params.id}/images/${imageId}`, { method: 'DELETE' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '删除失败');
      await loadImages();
      setAssetMessage('图片已删除。');
    } catch (err) {
      setAssetMessage(err instanceof Error ? err.message : '删除失败');
    } finally {
      setLoading(false);
    }
  }

  async function generateAmazonUploadFile() {
    const listingVersions = data?.listing_versions || [];
    const selectedListing = listingVersions.find((item: any) => String(item.id) === String(exportListingVersionId)) || listingVersions[0];
    if (!selectedListing) {
      setExportMessage('请先生成至少 1 个 Listing 文案版本。');
      return;
    }
    if (!exportBrand.trim()) {
      setExportMessage('请先填写 Brand，生成上传文件时必填。');
      return;
    }
    if (!exportCategory.trim()) {
      setExportMessage('请先填写 Category，生成上传文件时必填。');
      return;
    }
    if (imageAssets.length < 5) {
      setExportMessage(`当前只有 ${imageAssets.length} 张图片，至少上传 5 张后再生成文件。`);
      return;
    }
    const cleanVariants = variants
      .map((item) => ({ ...item, value: item.value.trim(), color: item.color.trim(), sku: item.sku.trim(), price: item.price.trim() }))
      .filter((item) => item.value || item.color || item.sku || item.price);
    if (variationEnabled && !cleanVariants.length) {
      setExportMessage('已开启多变体，请至少填写 1 个子体规格。');
      return;
    }
    setLoading(true);
    try {
      const response = await authFetch(`/api/listing-projects/${params.id}/amazon-upload-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          listing_version_id: selectedListing.id,
          brand: exportBrand,
          category: exportCategory,
          images: imageAssets,
          variation: variationEnabled ? { enabled: true, theme: variationTheme, parentSku, variants: cleanVariants } : undefined,
        }),
      });
      if (!response.ok) {
        let detail = '生成失败';
        try {
          const result = await response.json();
          detail = result.detail || detail;
        } catch {
          detail = await response.text();
        }
        throw new Error(detail);
      }
      const blob = await response.blob();
      const fileName = filenameFromContentDisposition(response.headers.get('Content-Disposition')) || `${buildAmazonSku(data.project, selectedListing)}-SAW_BLADE-amazon-upload.xlsm`;
      downloadBlobFile(fileName, blob);
      setExportMessage(`已生成 ${fileName}。${variationEnabled ? `包含 ${cleanVariants.length} 个子体。` : '单品文件。'}图片列已写入当前上传图片链接，Listing 版本：${selectedListing.version_name || 'V1'}。`);
    } catch (err) {
      setExportMessage(err instanceof Error ? err.message : '生成失败');
    } finally {
      setLoading(false);
    }
  }

  if (!data?.project) {
    return <main className="mx-auto max-w-7xl px-6 py-8"><p className="text-slate-500">加载中...</p></main>;
  }

  const project = data.project;
  const isDraft = project.status === 'draft';
  const isCompetitorParse = project.project_type === 'competitor_parse';
  const hasImportedReferences = isCompetitorParse || (data.competitors || []).some(hasImportedCompetitorData);
  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-6 border-b border-slate-200 pb-5">
        <p className="text-sm font-medium text-blue-700">Listing 生成模块</p>
        <h1 className="text-3xl font-bold">{project.project_name}</h1>
        <p className="mt-2 text-slate-600">
          {project.product_name || '-'} · {project.marketplace} · <span className="rounded-full bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">{projectTypeLabel(project.project_type)}</span> · <span className={isDraft ? 'font-semibold text-emerald-700' : 'font-semibold text-slate-700'}>{isDraft ? '草稿可编辑' : '已生成，基础信息已锁定'}</span>
        </p>
      </header>
      <ListingSubnav projectId={params.id} />
      {message && <div className="mb-6 rounded bg-slate-50 p-3 text-sm text-slate-700">{message}</div>}

      <section className="mb-6 grid gap-4 md:grid-cols-4">
        <Metric label="Marketplace" value={project.marketplace} />
        <EditableMetric label="Brand" value={exportBrand} onChange={setExportBrand} placeholder="必填，例如：Your Brand" required />
        <EditableMetric label="Category" value={exportCategory} onChange={setExportCategory} placeholder="必填，可输入 Amazon 类目路径" required suggestions={amazonCategorySuggestions} />
        <Metric label="Target Price" value={project.target_price ? `$${project.target_price}` : '-'} />
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

      <Panel title={hasImportedReferences ? "竞品结构化参考" : "SerpApi 结构化参考分析"}>
        <div className="rounded border border-blue-100 bg-blue-50 p-3 text-sm text-blue-900">
          {hasImportedReferences
            ? '系统已自动导入保存的竞品结构化参考，不再重复调用 SerpApi。竞品只用于关键词、规格表达、卖点层级和图片模块参考，不能复制图片、Logo、包装或文案。'
            : '这里不会把 Amazon 链接直接丢给模型。系统先通过后端 SerpApi 获取结构化 JSON，再让模型只分析 JSON。竞品默认只用于公开分析和布局参考，不能复制图片、Logo、包装或文案。'}
        </div>
        {!hasImportedReferences && (
          <div className="mt-4 grid gap-3 lg:grid-cols-[160px_1fr_1fr_auto]">
            <label className="block text-sm font-semibold text-slate-700">
              Amazon 站点
              <select className="mt-1 w-full rounded border px-3 py-2" value={amazonDomain} onChange={(event) => setAmazonDomain(event.target.value)}>
                {['amazon.com', 'amazon.ca', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 'amazon.it', 'amazon.es', 'amazon.co.jp', 'amazon.com.au'].map((domain) => (
                  <option key={domain} value={domain}>{domain}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              关键词搜索类似产品
              <input className="mt-1 w-full rounded border px-3 py-2" value={referenceKeyword} onChange={(event) => setReferenceKeyword(event.target.value)} placeholder="例如：cbn grinding wheel" />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Amazon 链接 / ASIN 获取详情
              <input className="mt-1 w-full rounded border px-3 py-2" value={referenceUrlOrAsin} onChange={(event) => setReferenceUrlOrAsin(event.target.value)} placeholder="https://www.amazon.com/dp/B0... 或 B0..." />
            </label>
            <div className="flex items-end gap-2">
              <button className="rounded-md bg-blue-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={loading} onClick={searchAmazonReferences} type="button">搜索</button>
              <button className="rounded-md border border-blue-700 px-3 py-2 text-sm font-semibold text-blue-700 disabled:opacity-50" disabled={loading} onClick={fetchAmazonProductByInput} type="button">获取详情</button>
            </div>
          </div>
        )}
        {referenceMessage && <p className={`mt-3 text-sm font-medium ${referenceMessage.includes('失败') || referenceMessage.includes('配置') ? 'text-red-700' : 'text-emerald-700'}`}>{referenceMessage}</p>}
        {!!searchResults.length && (
          <div className="mt-4">
            <h3 className="mb-2 font-semibold">搜索结果</h3>
            <div className="grid gap-3 md:grid-cols-2">
              {searchResults.slice(0, 12).map((item) => (
                <div className="flex gap-3 rounded border bg-slate-50 p-3" key={item.asin || item.linkClean || item.title}>
                  {item.thumbnail ? <img alt="" className="h-16 w-16 rounded object-contain ring-1 ring-slate-200" src={item.thumbnail} /> : <div className="h-16 w-16 rounded bg-white ring-1 ring-slate-200" />}
                  <div className="min-w-0 flex-1">
                    <div className="line-clamp-2 text-sm font-semibold">{item.title || item.asin}</div>
                    <div className="mt-1 text-xs text-slate-500">{item.asin || '-'} · {item.price || '-'} · Rating {item.rating || '-'} · Reviews {item.reviews || '-'}</div>
                    <button className="mt-2 rounded border border-blue-700 px-2 py-1 text-xs font-semibold text-blue-700" onClick={() => addSearchResultReference(item)} type="button">加入参考</button>
                    {item.linkClean && <a className="ml-3 text-xs text-blue-700 hover:underline" href={item.linkClean} target="_blank" rel="noreferrer">打开</a>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">已选结构化参考 ({similarReferences.length})</h3>
              {!hasImportedReferences && (
                <button className="rounded-md border border-slate-300 px-3 py-1 text-sm font-semibold text-slate-700 disabled:opacity-50" disabled={!similarReferences.length || loading} onClick={analyzeReferenceInsights} type="button">分析参考 JSON</button>
              )}
            </div>
            <div className="mt-2 space-y-2">
              {similarReferences.map((ref) => (
                <div className="flex gap-3 rounded border bg-white p-3" key={ref.id}>
                  {ref.thumbnail ? <img alt="" className="h-14 w-14 rounded object-contain ring-1 ring-slate-200" src={ref.thumbnail} /> : null}
                  <div className="min-w-0 flex-1">
                    <div className="line-clamp-2 text-sm font-semibold">{ref.title || ref.asin || ref.url}</div>
                    <div className="mt-1 text-xs text-slate-500">{ref.asin || '-'} · {ref.allowedUsage}</div>
                  </div>
                  <button className="text-xs font-semibold text-red-700" onClick={() => setSimilarReferences((current) => current.filter((item) => item.id !== ref.id))} type="button">移除</button>
                </div>
              ))}
              {!similarReferences.length && <p className="rounded bg-slate-50 p-3 text-sm text-slate-500">{hasImportedReferences ? '还没有可导入的竞品资料；请回到同行参考资料里保存竞品链接。' : '还没有结构化参考。可以搜索关键词后选择，或直接输入 Amazon 链接 / ASIN。'}</p>}
            </div>
          </div>
          <div>
            <h3 className="font-semibold">参考分析结果</h3>
            {referenceInsights ? (
              <div className="mt-2 space-y-2 rounded border bg-slate-50 p-3 text-sm">
                <TagLine title="图片模块" items={referenceInsights.commonImageTypes || []} />
                <TagLine title="安全构图" items={referenceInsights.safeCompositionHints || []} />
                <TagLine title="买家关注" items={referenceInsights.buyerConcernHints || []} />
                <TagLine title="风险词" items={referenceInsights.riskyClaimsFound || []} />
                <p className="text-xs text-slate-500">分析来源：{referenceInsights.analysisMode || 'local'} {referenceInsights.model ? `· ${referenceInsights.model}` : ''}</p>
              </div>
            ) : (
              <p className="mt-2 rounded bg-slate-50 p-3 text-sm text-slate-500">{hasImportedReferences ? '系统会自动从已保存的竞品资料生成本地参考洞察。' : '点击“分析参考 JSON”后，生成 Listing / 图片 Prompt / A+ 时会带上这些结构化洞察。'}</p>
            )}
          </div>
        </div>
      </Panel>

      <div id="versions">
      <Panel title="Listing 版本管理">
        <GenerationControls
          buttonLabel="生成 Listing 文案"
          count={listingCount}
          countLabel="生成版本数"
          loading={loading}
          model={listingModel}
          onCountChange={setListingCount}
          onGenerate={() => generate('generate-listing', 'Listing 文案', { model: listingModel, count: listingCount })}
          onModelChange={setListingModel}
        />
        <div className="space-y-4">
          {(data.listing_versions || []).map((item: any) => <ListingCard item={item} key={item.id} />)}
          {!data.listing_versions?.length && <p className="text-slate-500">还没有 Listing 版本，点击“生成 Listing 文案”。</p>}
        </div>
      </Panel>
      </div>

      <div id="image-prompts">
      <Panel title="图片 Prompt 版本">
        <GenerationControls
          buttonLabel="生成一套图片 Prompt"
          count={imageSetCount}
          countHelp="1 套包含普通产品图：主图、尺寸图、卖点图、适配图、场景图、包装图。A+ 不在这里生成。"
          countLabel="生成套数"
          includeReference
          loading={loading}
          maxCount={5}
          model={imageModel}
          onCountChange={setImageSetCount}
          onGenerate={() => generate('generate-image-prompts', '图片 Prompt', { model: imageModel, count: imageSetCount, includeReference: true })}
          onModelChange={setImageModel}
          onReferenceImageChange={handleReferenceImage}
          onReferenceNoteChange={(note) => setReferenceImage((current) => ({ ...current, note }))}
          referenceImage={referenceImage}
        />
        <div className="space-y-4">
          {(data.image_prompt_versions || []).map((item: any) => <PromptCard item={item} key={item.id} />)}
          {!data.image_prompt_versions?.length && <p className="text-slate-500">还没有图片 Prompt，点击“生成图片 Prompt”。</p>}
        </div>
      </Panel>
      </div>

      <Panel title={`Listing 图片资产 (${imageAssets.length})`}>
        <div className="rounded border border-blue-100 bg-blue-50 p-3 text-sm text-blue-900">
          这里用于保存你从 ChatGPT、Midjourney 或其他模型生成好的 Listing 图片。图片文件会上传到 Cloudflare R2，系统只保存图片记录和 R2 路径。
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {listingImageTypes.map((type) => {
            const draft = assetDraft(type.value);
            const savedCount = imageAssets.filter((item) => item.image_type === type.value).length;
            return (
              <div className="rounded-lg border bg-slate-50 p-3" key={type.value}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold text-slate-900">{type.label}</h3>
                    <p className="mt-1 text-xs text-slate-500">已保存 {savedCount} 张</p>
                  </div>
                  <span className="rounded bg-white px-2 py-1 text-xs text-slate-500 ring-1 ring-slate-200">{type.value}</span>
                </div>
                <label className="mt-3 block text-xs font-semibold text-slate-600">
                  标题，可选
                  <input
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                    onChange={(event) => updateAssetDraft(type.value, { title: event.target.value })}
                    placeholder={type.placeholder}
                    value={draft.title}
                  />
                </label>
                <label className="mt-3 block text-xs font-semibold text-slate-600">
                  选择图片
                  <input
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                    key={`${type.value}-${assetInputVersion[type.value] || 0}`}
                    onChange={(event) => updateAssetDraft(type.value, { file: event.target.files?.[0] || null })}
                    type="file"
                  />
                </label>
                <label className="mt-3 block text-xs font-semibold text-slate-600">
                  备注，可选
                  <textarea
                    className="mt-1 min-h-20 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                    onChange={(event) => updateAssetDraft(type.value, { notes: event.target.value })}
                    placeholder="例如：来自 GPT-4o 生图；待检查文字拼写。"
                    value={draft.notes}
                  />
                </label>
                <button
                  className="mt-3 w-full rounded-md bg-blue-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  disabled={loading || !draft.file}
                  onClick={() => uploadAsset(type.value)}
                  type="button"
                >
                  {loading ? '处理中...' : `上传${type.label}`}
                </button>
              </div>
            );
          })}
        </div>
        {assetMessage && <p className={`mt-3 text-sm font-medium ${assetMessage.includes('失败') || assetMessage.includes('配置') || assetMessage.includes('请选择') ? 'text-red-700' : 'text-emerald-700'}`}>{assetMessage}</p>}
        <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {imageAssets.map((item) => (
            <div className="overflow-hidden rounded border bg-slate-50" key={item.id}>
              {item.url ? (
                <a href={item.url} target="_blank" rel="noreferrer">
                  <img alt={item.title || item.file_name} className="h-48 w-full bg-white object-contain" src={item.url} />
                </a>
              ) : (
                <div className="flex h-48 items-center justify-center bg-white text-sm text-slate-400">暂无可访问预览 URL</div>
              )}
              <div className="p-3 text-sm">
                <div className="font-semibold text-slate-900">{item.title || item.file_name}</div>
                <div className="mt-1 text-xs text-slate-500">{imageTypeLabel(item.image_type)} · {formatBytes(item.file_size)} · {item.content_type || '-'}</div>
                {item.notes && <p className="mt-2 whitespace-pre-wrap text-slate-600">{item.notes}</p>}
                <div className="mt-3 flex items-center gap-3">
                  {item.url && <a className="text-xs font-semibold text-blue-700 hover:underline" href={item.url} target="_blank" rel="noreferrer">打开原图</a>}
                  <button className="text-xs font-semibold text-red-700" disabled={loading} onClick={() => deleteAsset(item.id)} type="button">删除</button>
                </div>
              </div>
            </div>
          ))}
          {!imageAssets.length && <p className="rounded bg-slate-50 p-3 text-sm text-slate-500">还没有保存图片。生成图片后，上传到这里统一管理。</p>}
        </div>
        <AmazonUploadFilePanel
          brand={exportBrand}
          category={exportCategory}
          disabled={loading}
          imageCount={imageAssets.length}
          listingVersionId={exportListingVersionId}
          listingVersions={data.listing_versions || []}
          message={exportMessage}
          onGenerate={generateAmazonUploadFile}
          onListingVersionChange={setExportListingVersionId}
          onParentSkuChange={(value) => {
            setParentSkuManual(Boolean(value.trim()));
            setParentSku(value);
          }}
          onVariantAdd={() => setVariants((current) => [...current, createVariantDraft()])}
          onVariantChange={(id, patch) => {
            if (Object.prototype.hasOwnProperty.call(patch, 'sku')) {
              const sku = String(patch.sku || '').trim();
              setManualVariantSkuIds((current) => {
                const next = { ...current };
                if (sku) next[id] = true;
                else delete next[id];
                return next;
              });
            }
            setVariants((current) => current.map((item) => item.id === id ? { ...item, ...patch } : item));
          }}
          onVariantRemove={(id) => {
            setManualVariantSkuIds((current) => {
              const next = { ...current };
              delete next[id];
              return next;
            });
            setVariants((current) => current.filter((item) => item.id !== id));
          }}
          onVariationEnabledChange={setVariationEnabled}
          onVariationThemeChange={setVariationTheme}
          parentSku={parentSku}
          variationEnabled={variationEnabled}
          variationTheme={variationTheme}
          variants={variants}
        />
      </Panel>

      <div id="aplus">
      <Panel title="A+ 页面版本">
        <GenerationControls
          buttonLabel="生成 A+ 页面"
          count={aplusCount}
          countLabel="生成版本数"
          includeReference
          loading={loading}
          maxCount={5}
          model={aplusModel}
          onCountChange={setAplusCount}
          onGenerate={() => generate('generate-aplus', 'A+ 页面方案', { model: aplusModel, count: aplusCount, includeReference: true })}
          onModelChange={setAplusModel}
          onReferenceImageChange={handleReferenceImage}
          onReferenceNoteChange={(note) => setReferenceImage((current) => ({ ...current, note }))}
          referenceImage={referenceImage}
        />
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

function EditableMetric({
  label,
  onChange,
  placeholder,
  required = false,
  suggestions,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  suggestions?: readonly string[];
  value: string;
}) {
  const listId = suggestions?.length ? `${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-suggestions` : undefined;
  return (
    <label className="rounded-lg border bg-white p-4">
      <span className="text-sm text-slate-500">{label}{required ? ' *' : ''}</span>
      <input
        className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-bold focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        list={listId}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
      {listId && (
        <datalist id={listId}>
          {suggestions?.map((item) => <option key={item} value={item} />)}
        </datalist>
      )}
    </label>
  );
}

function AmazonUploadFilePanel({
  brand,
  category,
  disabled,
  imageCount,
  listingVersionId,
  listingVersions,
  message,
  onGenerate,
  onListingVersionChange,
  onParentSkuChange,
  onVariantAdd,
  onVariantChange,
  onVariantRemove,
  onVariationEnabledChange,
  onVariationThemeChange,
  parentSku,
  variationEnabled,
  variationTheme,
  variants,
}: {
  brand: string;
  category: string;
  disabled?: boolean;
  imageCount: number;
  listingVersionId: string;
  listingVersions: any[];
  message?: string;
  onGenerate: () => void;
  onListingVersionChange: (value: string) => void;
  onParentSkuChange: (value: string) => void;
  onVariantAdd: () => void;
  onVariantChange: (id: string, patch: Partial<VariantDraft>) => void;
  onVariantRemove: (id: string) => void;
  onVariationEnabledChange: (value: boolean) => void;
  onVariationThemeChange: (value: string) => void;
  parentSku: string;
  variationEnabled: boolean;
  variationTheme: string;
  variants: VariantDraft[];
}) {
  const ready = imageCount >= 5;
  const hasListing = listingVersions.length > 0;
  return (
    <div className="mt-6 rounded-lg border bg-white p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h3 className="text-lg font-bold">Amazon Listing 上传文件</h3>
          <p className="mt-1 text-sm text-slate-600">
            图片满 5 张后生成 Amazon 库存加载工具文件（.xlsm）。标题、五点、描述用选中的 Listing 版本；图片列直接写当前上传的 R2 图片链接。
          </p>
          {!ready && <p className="mt-2 text-sm font-semibold text-amber-700">当前 {imageCount}/5 张，继续上传图片后即可生成。</p>}
          {ready && (!brand.trim() || !category.trim()) && <p className="mt-2 text-sm font-semibold text-red-700">请先在顶部填写 Brand 和 Category。</p>}
        </div>
        <div className="flex flex-col gap-3 md:flex-row md:items-end">
          <label className="block text-sm font-semibold text-slate-700">
            Listing 版本
            <select
              className="mt-1 w-full min-w-64 rounded border px-3 py-2"
              disabled={!hasListing}
              onChange={(event) => onListingVersionChange(event.target.value)}
              value={listingVersionId || String(listingVersions[0]?.id || '')}
            >
              {listingVersions.map((item: any, index: number) => (
                <option key={item.id} value={String(item.id)}>
                  {item.version_name || `Listing Version ${index + 1}`}
                </option>
              ))}
            </select>
          </label>
          <button
            className="rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50"
            disabled={disabled || !ready || !hasListing || !brand.trim() || !category.trim()}
            onClick={onGenerate}
            type="button"
          >
            生成库存加载文件
          </button>
        </div>
      </div>
      <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <label className="flex items-center gap-2 text-sm font-bold text-slate-800">
          <input
            checked={variationEnabled}
            className="h-4 w-4"
            onChange={(event) => onVariationEnabledChange(event.target.checked)}
            type="checkbox"
          />
          多变体上传
        </label>
        <p className="mt-1 text-xs text-slate-500">
          不开启时按单品导出。开启后文件会生成 1 行父体 + 多行子体，适合尺寸、颜色、数量包装等变体。
        </p>
        {variationEnabled && (
          <div className="mt-4 space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              <label className="block text-sm font-semibold text-slate-700">
                父体 SKU，可选
                <input
                  className="mt-1 w-full rounded border bg-white px-3 py-2"
                  onChange={(event) => onParentSkuChange(event.target.value)}
                  placeholder="不填则自动生成"
                  value={parentSku}
                />
              </label>
              <label className="block text-sm font-semibold text-slate-700">
                变体主题
                <select className="mt-1 w-full rounded border bg-white px-3 py-2" onChange={(event) => onVariationThemeChange(event.target.value)} value={variationTheme}>
                  <option value="SizeName">SizeName / 尺寸规格</option>
                  <option value="ColorName">ColorName / 颜色</option>
                  <option value="SizeName-ColorName">SizeName-ColorName / 尺寸+颜色</option>
                  <option value="PackageQuantity">PackageQuantity / 包装数量</option>
                </select>
              </label>
              <div className="rounded bg-white p-3 text-xs text-slate-500 ring-1 ring-slate-200">
                子体价格不填时使用项目目标售价；SKU 不填时系统按父体 SKU + 规格自动生成。
              </div>
            </div>
            <div className="overflow-x-auto rounded border bg-white">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-100 text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">子 SKU</th>
                    <th className="px-3 py-2">规格/尺寸/数量</th>
                    <th className="px-3 py-2">颜色</th>
                    <th className="px-3 py-2">价格</th>
                    <th className="px-3 py-2">主图来源</th>
                    <th className="px-3 py-2">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {variants.map((variant) => (
                    <tr className="border-t" key={variant.id}>
                      <td className="px-3 py-2">
                        <input className="w-36 rounded border px-2 py-1" onChange={(event) => onVariantChange(variant.id, { sku: event.target.value })} placeholder="可选" value={variant.sku} />
                      </td>
                      <td className="px-3 py-2">
                        <input className="w-44 rounded border px-2 py-1" onChange={(event) => onVariantChange(variant.id, { value: event.target.value })} placeholder="例如：37.7 x 1/8 in / 3-pack" value={variant.value} />
                      </td>
                      <td className="px-3 py-2">
                        <input className="w-28 rounded border px-2 py-1" onChange={(event) => onVariantChange(variant.id, { color: event.target.value })} placeholder="可选" value={variant.color} />
                      </td>
                      <td className="px-3 py-2">
                        <input className="w-24 rounded border px-2 py-1" onChange={(event) => onVariantChange(variant.id, { price: event.target.value })} placeholder="$" type="number" value={variant.price} />
                      </td>
                      <td className="px-3 py-2">
                        <select className="w-32 rounded border px-2 py-1" onChange={(event) => onVariantChange(variant.id, { imageType: event.target.value })} value={variant.imageType}>
                          {listingImageTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
                        </select>
                      </td>
                      <td className="px-3 py-2">
                        <button className="text-xs font-semibold text-red-700 disabled:opacity-40" disabled={variants.length <= 1} onClick={() => onVariantRemove(variant.id)} type="button">删除</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button className="rounded-md border border-blue-700 px-3 py-2 text-sm font-semibold text-blue-700" onClick={onVariantAdd} type="button">
              添加子体
            </button>
          </div>
        )}
      </div>
      {message && <p className={`mt-3 text-sm font-semibold ${message.includes('请先') || message.includes('至少') || message.includes('当前只有') ? 'text-red-700' : 'text-emerald-700'}`}>{message}</p>}
      <p className="mt-3 text-xs text-slate-500">
        提醒：Amazon 不同类目的官方模板字段会有差异。这个文件先作为上传草稿/映射文件，后续可以按你的具体类目模板继续精修。
      </p>
    </div>
  );
}

function TagLine({ title, items }: { title: string; items: any[] }) {
  const clean = (items || []).filter(Boolean).slice(0, 8);
  return (
    <div>
      <div className="text-xs font-semibold text-slate-500">{title}</div>
      <div className="mt-1 flex flex-wrap gap-1">
        {clean.length ? clean.map((item) => <span className="rounded bg-white px-2 py-1 text-xs text-slate-700 ring-1 ring-slate-200" key={String(item)}>{String(item)}</span>) : <span className="text-xs text-slate-400">暂无</span>}
      </div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mb-6 rounded-lg border bg-white p-5"><h2 className="mb-4 text-xl font-bold">{title}</h2>{children}</section>;
}

function GenerationControls({
  buttonLabel,
  count,
  countHelp,
  countLabel,
  includeReference = false,
  loading,
  maxCount = 10,
  model,
  onCountChange,
  onGenerate,
  onModelChange,
  onReferenceImageChange,
  onReferenceNoteChange,
  referenceImage,
}: {
  buttonLabel: string;
  count: number;
  countHelp?: string;
  countLabel: string;
  includeReference?: boolean;
  loading: boolean;
  maxCount?: number;
  model: string;
  onCountChange: (count: number) => void;
  onGenerate: () => void;
  onModelChange: (model: string) => void;
  onReferenceImageChange?: (event: ChangeEvent<HTMLInputElement>) => void;
  onReferenceNoteChange?: (note: string) => void;
  referenceImage?: { file_name?: string; note?: string; preview?: string; data_url?: string };
}) {
  return (
    <div className="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-sm text-slate-600">生成结果会保存为新版本，不会覆盖旧内容。</p>
      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        <label className="block text-sm font-semibold text-slate-700">
          本次生成模型
          <select
            className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            value={model}
            onChange={(event) => onModelChange(event.target.value)}
          >
            {modelOptions.map((option) => (
              <option key={option.label} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-semibold text-slate-700">
          {countLabel}
          <input
            className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            min={1}
            max={maxCount}
            type="number"
            value={count}
            onChange={(event) => onCountChange(Math.max(1, Math.min(maxCount, Number(event.target.value) || 1)))}
          />
          {countHelp && <span className="mt-1 block text-xs font-normal text-slate-500">{countHelp}</span>}
        </label>
        {includeReference && (
          <label className="block text-sm font-semibold text-slate-700">
            产品主图参考
            <input className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2" accept="image/*" type="file" onChange={onReferenceImageChange} />
          </label>
        )}
      </div>
      {includeReference && (
        <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_2fr]">
          {referenceImage?.preview ? (
            <div className="flex items-center gap-3 rounded bg-white p-3 text-sm text-slate-600 ring-1 ring-slate-200">
              <img alt="主图参考预览" className="h-16 w-16 rounded object-contain ring-1 ring-slate-200" src={referenceImage.preview} />
              <div>
                <div className="font-semibold text-slate-800">{referenceImage.file_name}</div>
                <div>用于约束产品外观，同行链接只借鉴结构和卖点。</div>
              </div>
            </div>
          ) : (
            <div className="rounded bg-white p-3 text-sm text-slate-500 ring-1 ring-slate-200">可上传自己的产品主图，让图片 Prompt 和 A+ 图文方向保持真实外观一致。</div>
          )}
          <label className="block text-sm font-semibold text-slate-700">
            主图参考说明，可选
            <input
              className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2"
              placeholder="例如：以黑色磨轮外观、孔径、包装数量为准"
              value={referenceImage?.note || ''}
              onChange={(event) => onReferenceNoteChange?.(event.target.value)}
            />
          </label>
        </div>
      )}
      <button
        className="mt-4 rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50"
        disabled={loading}
        onClick={onGenerate}
        type="button"
      >
        {loading ? '生成中...' : buttonLabel}
      </button>
    </div>
  );
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

function projectTypeLabel(value?: string) {
  if (value === 'competitor_parse') return '竞品解析型';
  return '资料录入型';
}

function hasImportedCompetitorData(item: any) {
  return Boolean(
    item?.competitor_title ||
    item?.competitor_bullets ||
    item?.competitor_description ||
    item?.competitor_price ||
    item?.competitor_rating ||
    item?.competitor_review_count ||
    item?.competitor_image_notes
  );
}

function competitorToStructuredReference(item: any, index: number): SimilarProductReference {
  const url = String(item?.competitor_url || '');
  const asin = extractAsin(url);
  const thumbnail = extractFirstUrl(String(item?.competitor_image_notes || ''));
  return {
    id: `saved-competitor-${item?.id || asin || index}`,
    url,
    asin,
    amazonDomain: domainFromAmazonUrl(url),
    platform: 'amazon',
    referenceType: 'competitor',
    permissionStatus: 'public_analysis_only',
    allowedUsage: 'public_analysis_only',
    userNotes: [item?.what_to_reference, item?.what_to_avoid].filter(Boolean).join('\n'),
    title: item?.competitor_title || asin || url,
    thumbnail,
    productData: {
      source: 'serpapi_amazon_product',
      asin,
      amazonDomain: domainFromAmazonUrl(url),
      title: item?.competitor_title || '',
      productLink: url,
      mainImage: thumbnail,
      rating: item?.competitor_rating || undefined,
      reviews: item?.competitor_review_count || undefined,
      extractedPrice: item?.competitor_price || undefined,
      aboutItem: splitLines(item?.competitor_bullets),
      productDescription: item?.competitor_description || '',
      normalizedFacts: {},
      warnings: ['Imported from saved competitor reference; no repeated SerpApi call on this page.'],
    },
  };
}

function buildLocalReferenceInsightsFromCompetitors(items: any[]): ReferenceInsights {
  const text = items
    .map((item) => [item.competitor_title, item.competitor_bullets, item.competitor_description, item.competitor_image_notes].filter(Boolean).join('\n'))
    .join('\n')
    .toLowerCase();
  const imageTypes = new Set<ReferenceInsights['commonImageTypes'][number]>(['main_image_clean', 'dimension', 'feature']);
  if (/compat|fit|replacement|model|for\s+[a-z0-9-]+/.test(text)) imageTypes.add('compatibility');
  if (/use|cut|grind|sharpen|glass|metal|wood|workshop/.test(text)) imageTypes.add('application');
  if (/pack|package|include|set|pcs|pieces/.test(text)) imageTypes.add('package');
  const risky = ['official', 'original', 'authorized', 'best', 'guaranteed', 'lifetime'].filter((word) => text.includes(word));
  return {
    categorySignals: topTerms(text, 10),
    commonVisualPatterns: ['白底主图突出产品本体', '尺寸规格图降低误购', '卖点图强调材质/耐用/适配', '使用场景图展示工具应用'],
    commonImageTypes: Array.from(imageTypes),
    safeStyleHints: ['只参考公开商品的结构和信息层级，不复制图片、包装、Logo 或原文', '兼容类产品使用 Compatible with / Replacement for 表达'],
    safeCompositionHints: ['主图保持白底、无文字、无多余配件', '副图用自己的产品图做主体，参考竞品的信息组织方式'],
    buyerConcernHints: ['尺寸是否匹配', '材质和寿命', '包装数量', '适配型号', '是否容易误买'],
    overlayTextPatterns: ['Size / Specs', 'Compatible With', 'Package Includes', 'Application', 'Material Feature'],
    productFactsCandidates: {
      title_terms: topTerms(text, 16),
    },
    riskyClaimsFound: risky,
    brandOrTrademarkRisks: [],
    unsafeToCopy: ['竞品标题原文', '竞品五点原文', '竞品图片构图', '品牌名/Logo', '官方/授权等归属暗示'],
    recommendedQuestionsForUser: ['请确认自己的产品尺寸、材质、包装数量和兼容型号，模型生成时以你自己的事实为准。'],
    warnings: ['这些洞察来自已保存竞品参考，本页未再次调用 SerpApi。'],
    analysisMode: 'local_saved_competitor_import',
  };
}

function extractAsin(url?: string) {
  const match = String(url || '').match(/(?:\/dp\/|\/gp\/product\/|^)(B0[A-Z0-9]{8}|B00[A-Z0-9]{7})/i);
  return match?.[1]?.toUpperCase() || '';
}

function extractFirstUrl(value?: string) {
  return String(value || '').match(/https?:\/\/\S+/)?.[0]?.replace(/[),.;]+$/, '') || '';
}

function splitLines(value?: string) {
  return String(value || '')
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function domainFromAmazonUrl(url?: string) {
  try {
    const host = new URL(String(url || '')).hostname.replace(/^www\./, '');
    return host.includes('amazon.') ? host : 'amazon.com';
  } catch {
    return 'amazon.com';
  }
}

function topTerms(text: string, limit: number) {
  const stop = new Set(['with', 'from', 'this', 'that', 'amazon', 'product', 'products', 'inch', 'and', 'the', 'for', 'your', 'you', 'are', 'not']);
  const counts = new Map<string, number>();
  (text.match(/[a-z][a-z0-9-]{3,}/g) || []).forEach((word) => {
    if (stop.has(word)) return;
    counts.set(word, (counts.get(word) || 0) + 1);
  });
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([word]) => word);
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

function buildAmazonListingUploadCsv({
  brand,
  category,
  images,
  inputs,
  listing,
  project,
  variation,
}: {
  brand: string;
  category: string;
  images: any[];
  inputs: Record<string, any>;
  listing: any;
  project: any;
  variation?: {
    enabled: boolean;
    theme: string;
    parentSku: string;
    variants: VariantDraft[];
  };
}) {
  const orderedImages = orderAmazonImages(images).slice(0, 9);
  const bullets = [listing.bullet_1, listing.bullet_2, listing.bullet_3, listing.bullet_4, listing.bullet_5].map((item) => String(item || ''));
  const categoryText = normalizeSpaces(category);
  const productType = inferAmazonProductType(categoryText, project, inputs);
  const keywords = buildAmazonKeywords(project, inputs, listing);
  const baseRow: Record<string, string> = {
    sku: buildAmazonSku(project, listing),
    product_type: productType,
    category_path: categoryText,
    brand_name: normalizeSpaces(brand),
    item_name: normalizeSpaces(listing.title || project.product_name || project.project_name),
    standard_price: project.target_price ? String(project.target_price) : '',
    product_description: normalizeSpaces(listing.description || ''),
    bullet_point1: normalizeSpaces(bullets[0]),
    bullet_point2: normalizeSpaces(bullets[1]),
    bullet_point3: normalizeSpaces(bullets[2]),
    bullet_point4: normalizeSpaces(bullets[3]),
    bullet_point5: normalizeSpaces(bullets[4]),
    generic_keywords: keywords,
    main_image_url: orderedImages[0]?.url || '',
    other_image_url1: orderedImages[1]?.url || '',
    other_image_url2: orderedImages[2]?.url || '',
    other_image_url3: orderedImages[3]?.url || '',
    other_image_url4: orderedImages[4]?.url || '',
    other_image_url5: orderedImages[5]?.url || '',
    other_image_url6: orderedImages[6]?.url || '',
    other_image_url7: orderedImages[7]?.url || '',
    other_image_url8: orderedImages[8]?.url || '',
    fulfillment_channel: project.fulfillment_method || '',
    update_delete: 'Update',
    marketplace: project.marketplace || 'US',
    source_listing_version: listing.version_name || '',
    parent_child: '',
    parent_sku: '',
    relationship_type: '',
    variation_theme: '',
    size_name: '',
    color_name: '',
    package_quantity: '',
  };
  const rows: Record<string, string>[] = variation?.enabled
    ? buildVariationRows(baseRow, orderedImages, variation, project)
    : [baseRow];
  const headers = Object.keys(baseRow);
  const csv = `\uFEFF${headers.join(',')}\n${rows.map((row) => headers.map((header) => csvEscape(row[header])).join(',')).join('\n')}\n`;
  return {
    csv,
    fileName: `${variation?.enabled ? (variation.parentSku || buildParentSku(project, listing)) : buildAmazonSku(project, listing)}-amazon-listing-upload.csv`,
  };
}

function buildVariationRows(baseRow: Record<string, string>, orderedImages: any[], variation: { theme: string; parentSku: string; variants: VariantDraft[] }, project: any): Record<string, string>[] {
  const parentSkuValue = normalizeSku(variation.parentSku) || buildParentSku(project, { id: baseRow.source_listing_version || 'PARENT' });
  const parentRow: Record<string, string> = {
    ...baseRow,
    sku: parentSkuValue,
    parent_child: 'parent',
    standard_price: '',
    parent_sku: '',
    relationship_type: '',
    variation_theme: variation.theme,
  };
  const children = variation.variants
    .filter((variant) => variant.value || variant.color || variant.sku || variant.price)
    .map((variant, index) => {
      const value = normalizeSpaces(variant.value || variant.color || `Variant ${index + 1}`);
      const childSku = normalizeSku(variant.sku) || `${parentSkuValue}-${slugPart(value || variant.color || String(index + 1))}`;
      const mainImage = imageForVariant(orderedImages, variant.imageType) || orderedImages[0];
      const otherImages = orderedImages.filter((image) => image.id !== mainImage?.id).slice(0, 8);
      return {
        ...baseRow,
        sku: childSku,
        item_name: normalizeSpaces(`${baseRow.item_name} ${value}`),
        standard_price: variant.price || baseRow.standard_price,
        parent_child: 'child',
        parent_sku: parentSkuValue,
        relationship_type: 'variation',
        variation_theme: variation.theme,
        size_name: variation.theme.includes('SizeName') ? value : '',
        color_name: variation.theme.includes('ColorName') ? (variant.color || value) : '',
        package_quantity: variation.theme === 'PackageQuantity' ? value.replace(/[^\d.]/g, '') || value : '',
        main_image_url: mainImage?.url || '',
        other_image_url1: otherImages[0]?.url || '',
        other_image_url2: otherImages[1]?.url || '',
        other_image_url3: otherImages[2]?.url || '',
        other_image_url4: otherImages[3]?.url || '',
        other_image_url5: otherImages[4]?.url || '',
        other_image_url6: otherImages[5]?.url || '',
        other_image_url7: otherImages[6]?.url || '',
        other_image_url8: otherImages[7]?.url || '',
      };
    });
  return [parentRow, ...children];
}

function imageForVariant(images: any[], imageType: string) {
  return images.find((item) => item.image_type === imageType) || images[0];
}

function orderAmazonImages(images: any[]) {
  const priority: Record<string, number> = {
    main_image: 0,
    dimension: 1,
    feature: 2,
    compatibility: 3,
    application: 4,
    package: 5,
    other: 6,
    aplus: 7,
  };
  return [...images]
    .filter((item) => item?.url)
    .sort((a, b) => (priority[a.image_type] ?? 99) - (priority[b.image_type] ?? 99) || Number(a.id || 0) - Number(b.id || 0));
}

function buildAmazonKeywords(project: any, inputs: Record<string, any>, listing: any) {
  const parts = [
    listing.backend_search_terms,
    inputs.main_keywords,
    inputs.compatibility,
    inputs.use_cases,
    project.product_name,
    project.category,
  ];
  const seen = new Set<string>();
  return parts
    .join(' ')
    .split(/[,\n;]+|\s{2,}/)
    .map((value) => normalizeSpaces(value).toLowerCase())
    .filter(Boolean)
    .filter((value) => {
      if (seen.has(value)) return false;
      seen.add(value);
      return true;
    })
    .join(' ')
    .slice(0, 240);
}

function buildAmazonSku(project: any, listing: any) {
  const seed = `project:${project.id || ''}|listing:${listing.id || ''}|${project.project_name || ''}|${project.product_name || ''}`;
  return hashedSku(project.product_name || project.project_name || 'SKU', seed);
}

function buildParentSku(project: any, listing: any) {
  const seed = `project:${project.id || ''}|parent|listing:${listing.id || ''}|${project.project_name || ''}|${project.product_name || ''}`;
  return hashedSku(project.product_name || project.project_name || 'PARENT', seed, 'P');
}

function normalizeSku(value?: string) {
  return String(value || '')
    .replace(/[^a-z0-9-]+/gi, '-')
    .replace(/^-+|-+$/g, '')
    .toUpperCase()
    .slice(0, 40);
}

function slugPart(value?: string) {
  return normalizeSku(value).slice(0, 18) || 'VARIANT';
}

function buildVariantSku(parentSku: string, value: string, index: number) {
  const digest = shortHash(`${parentSku}|${value}|${index}`).slice(0, 6);
  const valueSlug = slugPart(value || `V${index}`).slice(0, 8);
  return [normalizeSku(parentSku).slice(0, 24), valueSlug || `V${index}`, digest].filter(Boolean).join('-').slice(0, 40);
}

function hashedSku(value: string, seed: string, suffix = '') {
  const base = normalizeSku(value).replace(/^AMAZON-LISTING$/, '') || 'SKU';
  return [base.slice(0, 26), suffix, shortHash(seed).slice(0, 8)].filter(Boolean).join('-').slice(0, 40);
}

function shortHash(value: string) {
  let hash = 2166136261;
  const text = String(value || '');
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).toUpperCase().padStart(8, '0');
}

function createVariantDraft(): VariantDraft {
  return {
    id: `v-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    sku: '',
    value: '',
    color: '',
    price: '',
    imageType: 'main_image',
  };
}

function inferAmazonProductType(category: string, project: any, inputs: Record<string, any>) {
  const text = [category, project.product_name, inputs.main_keywords, inputs.material, inputs.use_cases].join(' ').toLowerCase();
  if (/band\s*saw|saw\s*blade|blade/.test(text)) return 'saw_blades';
  if (/grinding\s*wheel|cbn|abrasive\s*wheel|bench\s*grinder/.test(text)) return 'abrasive_wheels';
  if (/grinder\s*bit|stained\s*glass|glass/.test(text)) return 'craft_supplies';
  if (/disc|disk|grinding\s*disc/.test(text)) return 'abrasive_discs';
  if (/replacement|part|accessor/.test(text)) return 'tools';
  return 'industrial_supplies';
}

function normalizeSpaces(value?: any) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function csvEscape(value?: string) {
  const text = String(value || '');
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function downloadTextFile(fileName: string, text: string) {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  downloadBlobFile(fileName, blob);
}

function downloadBlobFile(fileName: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function filenameFromContentDisposition(header: string | null) {
  if (!header) return '';
  const utfMatch = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) return decodeURIComponent(utfMatch[1]);
  const match = header.match(/filename="?([^";]+)"?/i);
  return match?.[1] || '';
}

function ListingCard({ item }: { item: any }) {
  const bullets = [item.bullet_1, item.bullet_2, item.bullet_3, item.bullet_4, item.bullet_5].filter(Boolean);
  const model = item.generated_model || modelFromText(item.generation_notes) || '旧版本未记录模型';
  const allText = [
    item.title,
    ...bullets,
    item.description,
    item.backend_search_terms ? `Backend Search Terms: ${item.backend_search_terms}` : '',
  ].filter(Boolean).join('\n\n');
  return (
    <details className="rounded border bg-slate-50 p-4">
      <summary className="cursor-pointer list-none">
        <div>
          <h3 className="font-bold">{item.version_name}</h3>
          <ModelBadge model={model} />
        </div>
      </summary>
      <div className="mt-4 border-t border-slate-200 pt-4">
        <div className="flex justify-end"><CopyButton text={allText} /></div>
        <CopyBlock title="Title" text={item.title} />
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm">
          {bullets.map((bullet, index) => <li key={index}>{bullet}</li>)}
        </ol>
        <CopyBlock title="Description" text={item.description} />
        <CopyBlock title="Backend Search Terms" text={item.backend_search_terms} />
        <p className="mt-2 text-xs text-slate-500">SEO {item.seo_score || '-'} · Conversion {item.conversion_score || '-'} · {item.compliance_risk_notes}</p>
        {item.generation_notes && <p className="mt-1 text-xs text-slate-500">{item.generation_notes}</p>}
      </div>
    </details>
  );
}

function PromptCard({ item }: { item: any }) {
  const legacyTemplate = isLegacyTemplatePrompt(item);
  const model = item.generated_model || modelFromText(item.notes) || (legacyTemplate ? '旧模板生成，建议重新生成' : '旧版本未记录模型');
  const allPromptText = [item.prompt_en, item.prompt_cn, item.negative_prompt].filter(Boolean).join('\n\n');
  return (
    <details className="rounded border bg-slate-50 p-4">
      <summary className="cursor-pointer list-none">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className="font-bold">{item.version_name}</h3>
            <ModelBadge model={model} />
          </div>
          <ImageToolButtons prompt={item.prompt_en || allPromptText} />
        </div>
        <p className="mt-1 text-sm text-slate-600">{item.image_type || 'Listing Image'} · {item.image_goal}</p>
      </summary>
      <div className="mt-4 border-t border-slate-200 pt-4">
        <div className="flex flex-wrap justify-end gap-2">
          <ImageToolButtons prompt={item.prompt_en || allPromptText} compact />
          <CopyButton text={allPromptText} />
        </div>
        {legacyTemplate && (
          <div className="mt-3 rounded border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700">
            这是旧版本记录，内容里仍包含旧模板句式，不代表当前模型生成结果。请在上方选择模型后重新点击“生成图片 Prompt”。
          </div>
        )}
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          <CopyBlock title="英文 Prompt" text={item.prompt_en} />
          <CopyBlock title="中文 Prompt" text={item.prompt_cn} />
        </div>
        <CopyBlock title="Negative Prompt" text={item.negative_prompt} />
        <p className="mt-2 text-sm text-slate-500">图片中文字：{item.image_text || '-'} · 尺寸建议：{item.size_recommendation || '-'}</p>
        {item.notes && <p className="mt-1 text-xs text-slate-500">{item.notes}</p>}
      </div>
    </details>
  );
}

function ImageToolButtons({ prompt, compact = false }: { prompt?: string; compact?: boolean }) {
  const [copied, setCopied] = useState(false);

  async function openTool(url: string) {
    if (prompt) {
      try {
        await navigator.clipboard.writeText(prompt);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      } catch {
        setCopied(false);
      }
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  return (
    <div className="flex flex-wrap justify-end gap-2">
      {imageTools.map((tool) => (
        <button
          className={`${compact ? 'px-2 py-1 text-xs' : 'px-3 py-2 text-sm'} rounded border border-blue-700 bg-white font-semibold text-blue-700 hover:bg-blue-50 disabled:opacity-50`}
          disabled={!prompt}
          key={tool.label}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            openTool(tool.url);
          }}
          title={`复制 Prompt 并打开 ${tool.label}`}
          type="button"
        >
          {copied ? '已复制' : compact ? tool.shortLabel : tool.label}
        </button>
      ))}
    </div>
  );
}

const imageTools = [
  { label: '复制并打开 ChatGPT', shortLabel: 'ChatGPT', url: 'https://chatgpt.com/' },
  { label: '复制并打开 Gemini', shortLabel: 'Gemini', url: 'https://gemini.google.com/app' },
  { label: '复制并打开 Midjourney', shortLabel: 'Midjourney', url: 'https://www.midjourney.com/imagine' },
  { label: '复制并打开 Ideogram', shortLabel: 'Ideogram', url: 'https://ideogram.ai/' },
  { label: '复制并打开 Krea', shortLabel: 'Krea', url: 'https://www.krea.ai/' },
];

function AplusCard({ item }: { item: any }) {
  const model = item.generated_model || modelFromText(item.image_prompt_notes) || '旧版本未记录模型';
  const allText = [
    item.banner_copy,
    item.brand_story_copy,
    item.feature_modules,
    item.specification_module,
    item.application_module,
    item.comparison_chart,
    item.image_prompt_notes,
  ].filter(Boolean).join('\n\n');
  return (
    <details className="rounded border bg-slate-50 p-4">
      <summary className="cursor-pointer list-none">
        <div>
          <h3 className="font-bold">{item.version_name}</h3>
          <ModelBadge model={model} />
        </div>
      </summary>
      <div className="mt-4 border-t border-slate-200 pt-4">
        <div className="flex justify-end"><CopyButton text={allText} /></div>
        <CopyBlock title="Banner Copy" text={item.banner_copy} />
        <CopyBlock title="Brand Story" text={item.brand_story_copy} />
        <CopyBlock title="Feature Modules" text={item.feature_modules} />
        <CopyBlock title="Specification Module" text={item.specification_module} />
        <CopyBlock title="Application Module" text={item.application_module} />
        <CopyBlock title="Comparison Chart" text={item.comparison_chart} />
        <CopyBlock title="Image Prompt Notes" text={item.image_prompt_notes} />
      </div>
    </details>
  );
}

function modelFromText(text?: string) {
  const match = String(text || '').match(/Model:\s*([^\n]+)/);
  return match?.[1]?.trim().replace(/\.$/, '') || '';
}

function ModelBadge({ model }: { model?: string }) {
  if (!model) return null;
  const isLegacy = model.includes('旧');
  return (
    <span className={`mt-1 inline-flex rounded-full px-2 py-1 text-xs font-semibold ${isLegacy ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'}`}>
      模型来源：{model}
    </span>
  );
}

function imageTypeLabel(type?: string) {
  const map: Record<string, string> = {
    main_image: '主图',
    dimension: '尺寸图',
    feature: '卖点图',
    compatibility: '适配图',
    application: '场景图',
    package: '包装图',
    aplus: 'A+ 图片',
    other: '其他',
  };
  return map[String(type || '')] || type || '其他';
}

function formatBytes(value?: number) {
  const bytes = Number(value || 0);
  if (!bytes) return '-';
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function isLegacyTemplatePrompt(item: any) {
  const text = [item.prompt_en, item.prompt_cn, item.reference_usage_notes, item.notes].filter(Boolean).join('\n');
  return /Use the uploaded product photo as the exact product reference|保持真实产品外观|Use competitor reference only as layout inspiration/i.test(text);
}

function CopyBlock({ title, text }: { title: string; text?: string }) {
  return (
    <div className="mt-3 rounded bg-white p-3 text-sm">
      <div className="mb-1 flex items-center justify-between gap-3">
        <div className="font-semibold text-slate-700">{title}</div>
        <CopyButton text={text || ''} />
      </div>
      <pre className="whitespace-pre-wrap font-sans text-slate-700">{text || '-'}</pre>
    </div>
  );
}

function CopyButton({ text }: { text?: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }
  return (
    <button
      className="rounded border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40"
      disabled={!text}
      onClick={copy}
      type="button"
    >
      {copied ? '已复制' : '复制'}
    </button>
  );
}
