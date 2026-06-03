'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { API_BASE, readApiJson, saveAuth } from '@/lib/api';

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setLoading(true);
    setError('');
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: String(form.get('name') || ''),
          email: String(form.get('email') || ''),
          password: String(form.get('password') || ''),
        }),
      });
      const data = await readApiJson(response);
      if (!response.ok) throw new Error(data.detail || '注册失败');
      saveAuth(data.access_token, data.user);
      router.push('/');
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setError('注册请求超时，请确认后端服务已启动后再试。');
      } else {
        setError(err instanceof Error ? err.message : '注册失败');
      }
    } finally {
      window.clearTimeout(timeout);
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-12">
      <h1 className="text-3xl font-bold">注册</h1>
      <p className="mt-2 text-slate-600">创建自用账号。不同账号的数据默认隔离。</p>
      <form className="mt-6 space-y-4 rounded-lg border bg-white p-5" onSubmit={submit}>
        <Input name="name" label="名称，可选" type="text" required={false} />
        <Input name="email" label="邮箱" type="email" />
        <Input name="password" label="密码，至少 6 位" type="password" />
        {error && <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <button className="w-full rounded-md bg-blue-700 px-4 py-2 font-semibold text-white disabled:opacity-50" disabled={loading}>
          {loading ? '注册中...' : '注册并登录'}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-600">已有账号？<Link className="font-semibold text-blue-700" href="/login">去登录</Link></p>
    </main>
  );
}

function Input({ name, label, type, required = true }: { name: string; label: string; type: string; required?: boolean }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {label}
      <input className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2" name={name} type={type} required={required} />
    </label>
  );
}
