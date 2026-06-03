import './globals.css';
import type { Metadata } from 'next';
import ModuleNav from './module-nav';

export const metadata: Metadata = {
  title: 'Amazon Seller Growth Copilot',
  description: 'Amazon 店铺增长运营助手',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <ModuleNav />
        {children}
      </body>
    </html>
  );
}
