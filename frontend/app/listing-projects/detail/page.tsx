'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import ListingProjectDetailPage from './client-page';

export default function ListingProjectDetailRoute() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-7xl px-6 py-8 text-slate-600">加载中...</main>}>
      <DetailContent />
    </Suspense>
  );
}

function DetailContent() {
  const searchParams = useSearchParams();
  const id = searchParams.get('id') || '';
  if (!id) {
    return <main className="mx-auto max-w-7xl px-6 py-8 text-slate-600">缺少 Listing 项目 ID。</main>;
  }
  return <ListingProjectDetailPage params={{ id }} />;
}
