'use client';

import { ChangeEvent, FormEvent, useMemo, useState } from 'react';
import { API_BASE } from '@/lib/api';

export default function MadeInChinaToolPage() {
  const [file, setFile] = useState<File | null>(null);
  const [labelText, setLabelText] = useState('Made in China');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');
  const [downloadName, setDownloadName] = useState('amazon-labels-made-in-china.pdf');

  const ready = useMemo(() => Boolean(file && !loading), [file, loading]);

  function pickFile(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] || null;
    setFile(nextFile);
    setError('');
    if (downloadUrl) {
      URL.revokeObjectURL(downloadUrl);
      setDownloadUrl('');
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError('请先选择 Amazon 27 格标签 PDF。');
      return;
    }
    const form = new FormData();
    form.append('file', file);
    form.append('label_text', labelText.trim() || 'Made in China');
    setLoading(true);
    setError('');
    if (downloadUrl) {
      URL.revokeObjectURL(downloadUrl);
      setDownloadUrl('');
    }
    try {
      const response = await fetch(`${API_BASE}/api/tools/made-in-china-pdf`, {
        method: 'POST',
        body: form,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'PDF 处理失败');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const baseName = file.name.replace(/\.pdf$/i, '') || 'amazon-labels';
      setDownloadName(`${baseName}-made-in-china.pdf`);
      setDownloadUrl(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PDF 处理失败');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="bg-slate-50 px-6 py-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[260px_1fr]">
        <aside className="overflow-hidden rounded-lg border bg-white">
          <div className="bg-blue-700 px-6 py-5 text-center text-xl font-bold text-white">常用工具</div>
          <nav className="py-3">
            <a className="flex items-center justify-between bg-blue-50 px-5 py-4 font-semibold text-slate-900" href="/tools/made-in-china">
              <span><span className="mr-3 inline-block h-2 w-2 rounded-full bg-blue-500" />添加 Made in China</span>
              <span className="text-xl">›</span>
            </a>
            <div className="px-5 py-4 text-slate-400"><span className="mr-3 inline-block h-2 w-2 rounded-full bg-blue-100" />尾程派送费计算</div>
            <div className="px-5 py-4 text-slate-400"><span className="mr-3 inline-block h-2 w-2 rounded-full bg-blue-100" />FBA 仓库信息</div>
            <div className="px-5 py-4 text-slate-400"><span className="mr-3 inline-block h-2 w-2 rounded-full bg-blue-100" />附加费查询</div>
          </nav>
        </aside>

        <section className="rounded-lg border bg-white p-6">
          <h1 className="text-2xl font-bold">在线一键添加 Made in China</h1>
          <div className="mt-8 grid items-center gap-5 text-center md:grid-cols-[1fr_auto_1fr_auto_1fr]">
            <Step active label="上传 PDF 文件" icon="⇧" />
            <Arrow />
            <Step active={Boolean(file)} label="点击添加 Made in China" icon="+" />
            <Arrow />
            <Step active={Boolean(downloadUrl)} label="下载文件" icon="⇩" />
          </div>

          <form className="mt-8 rounded-lg border border-dashed border-slate-300 p-8 text-center" onSubmit={submit}>
            <div className="mx-auto flex h-28 w-28 items-center justify-center rounded-full bg-slate-50 text-5xl text-red-300">PDF</div>
            <label className="mt-6 inline-flex cursor-pointer rounded-md bg-orange-600 px-8 py-3 font-semibold text-white hover:bg-orange-700">
              点击选择 PDF 文件
              <input className="hidden" type="file" accept="application/pdf,.pdf" onChange={pickFile} />
            </label>
            {file && <p className="mt-4 text-sm text-slate-600">已选择：{file.name}</p>}

            <div className="mx-auto mt-6 max-w-sm text-left">
              <label className="block text-sm font-semibold text-slate-700">
                添加文字
                <input
                  className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={labelText}
                  onChange={(event) => setLabelText(event.target.value)}
                />
              </label>
            </div>

            {error && <div className="mx-auto mt-5 max-w-lg rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <button className="rounded-md bg-blue-700 px-6 py-3 font-semibold text-white disabled:opacity-50" disabled={!ready}>
                {loading ? '处理中...' : '添加 Made in China'}
              </button>
              {downloadUrl && (
                <a className="rounded-md border border-blue-700 px-6 py-3 font-semibold text-blue-700" download={downloadName} href={downloadUrl}>
                  下载处理后的 PDF
                </a>
              )}
            </div>
          </form>

          <p className="mt-4 text-sm text-slate-500">
            适用于 Amazon 常见 27 格产品标签 PDF。工具不需要登录，也不会保存你的 PDF 文件。
          </p>
        </section>
      </div>
    </main>
  );
}

function Step({ active, label, icon }: { active: boolean; label: string; icon: string }) {
  return (
    <div className="flex items-center justify-center gap-4">
      <span className={`flex h-16 w-16 items-center justify-center rounded-full text-3xl ${active ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400'}`}>
        {icon}
      </span>
      <span className={active ? 'text-xl font-semibold text-blue-600' : 'text-xl font-semibold text-slate-500'}>{label}</span>
    </div>
  );
}

function Arrow() {
  return <div className="hidden h-px bg-slate-300 md:block" />;
}
