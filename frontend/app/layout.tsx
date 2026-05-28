import './globals.css';
import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Amazon Seller Growth Copilot',
  description: 'Amazon 店铺增长运营助手',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const links = [
    ['/', 'Dashboard'],
    ['/uploads', '报表上传'],
    ['/sku-health', 'SKU Health'],
    ['/ads-diagnosis', '广告诊断'],
    ['/product-opportunity', '机会中心'],
    ['/listing-optimization', 'Listing 优化'],
    ['/profit-calculator', '利润计算器'],
    ['/recommendations', '建议中心'],
  ];
  return (
    <html lang="zh-CN">
      <body>
        <nav className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-6 py-4">
            <Link className="mr-3 font-bold text-slate-950" href="/">Seller Growth Copilot</Link>
            {links.slice(1).map(([href, label]) => (
              <Link className="text-sm font-medium text-slate-600 hover:text-blue-700" href={href} key={href}>{label}</Link>
            ))}
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
