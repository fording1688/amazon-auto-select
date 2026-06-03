'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { clearAuth, currentUser, getToken } from '@/lib/api';

const modules = [
  {
    label: '数据中心',
    href: '/uploads',
    items: [
      ['报表上传', '/uploads'],
      ['SKU Health', '/sku-health'],
      ['业务总览', '/'],
    ],
  },
  {
    label: '广告模块',
    href: '/ads-diagnosis',
    items: [
      ['广告诊断', '/ads-diagnosis'],
      ['建议中心', '/recommendations'],
    ],
  },
  {
    label: 'Listing 模块',
    href: '/listing-projects',
    items: [
      ['Listing 项目列表', '/listing-projects'],
      ['新建 Listing 项目', '/listing-projects/new'],
      ['Listing 优化', '/listing-optimization'],
    ],
  },
  {
    label: '选品机会',
    href: '/product-opportunity',
    items: [
      ['机会中心', '/product-opportunity'],
      ['利润计算器', '/profit-calculator'],
    ],
  },
  {
    label: '常用工具',
    href: '/tools/made-in-china',
    public: true,
    items: [
      ['添加 Made in China', '/tools/made-in-china'],
    ],
  },
] as const;

export default function ModuleNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const publicPage = pathname === '/login' || pathname === '/register' || pathname.startsWith('/tools');

  useEffect(() => {
    const token = getToken();
    setUser(currentUser());
    if (!token && !publicPage) router.replace('/login');
  }, [pathname, publicPage, router]);

  function logout() {
    clearAuth();
    setUser(null);
    router.push('/login');
  }

  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-6 py-4">
        <Link className="mr-4 font-bold text-slate-950" href="/">Seller Growth Copilot</Link>
        {modules
          .filter((module) => user || ('public' in module && module.public))
          .map((module) => {
          const active = module.items.some(([, href]) => pathname === href || pathname.startsWith(`${href}/`));
          return (
            <div className="group relative" key={module.label}>
              <Link
                className={`inline-flex rounded-md px-3 py-2 text-sm font-semibold ${
                  active ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50 hover:text-blue-700'
                }`}
                href={module.href}
              >
                {module.label}
              </Link>
              <div className="invisible absolute left-0 top-full z-20 min-w-52 rounded-md border bg-white p-2 opacity-0 shadow-lg transition group-hover:visible group-hover:opacity-100">
                {module.items.map(([label, href]) => (
                  <Link
                    className={`block rounded px-3 py-2 text-sm ${
                      pathname === href ? 'bg-blue-50 font-semibold text-blue-700' : 'text-slate-700 hover:bg-slate-50'
                    }`}
                    href={href}
                    key={href}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
        <div className="ml-auto flex items-center gap-3">
          {user ? (
            <>
              <span className="text-sm text-slate-500">{user.email}</span>
              <button className="rounded border px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50" onClick={logout}>退出</button>
            </>
          ) : (
            <Link className="rounded border px-3 py-2 text-sm font-semibold text-blue-700" href="/login">登录</Link>
          )}
        </div>
      </div>
    </nav>
  );
}
