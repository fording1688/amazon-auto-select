'use client';

import { useEffect, useMemo, useState } from 'react';
import { authFetch } from '@/lib/api';

type Store = {
  id: number;
  name: string;
  marketplace: string;
};

type Batch = {
  id: number;
  store_id: number | null;
  store_name: string;
  business_date: string;
  project_name: string;
  report_type: string;
  row_count: number;
};

function dateOnly(value?: string | null) {
  if (!value) return '';
  return value.slice(0, 10);
}

export default function ContextBar({
  storeId,
  businessDate,
  basePath,
}: {
  storeId?: string;
  businessDate?: string;
  basePath: string;
}) {
  const [stores, setStores] = useState<Store[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedStore, setSelectedStore] = useState(storeId || '');
  const [selectedDate, setSelectedDate] = useState(businessDate || '');

  useEffect(() => {
    authFetch('/api/copilot/context')
      .then((response) => response.json())
      .then((data) => {
        setStores(data.stores || []);
        setBatches(data.batches || []);
        if (!selectedStore && data.stores?.[0]?.id) setSelectedStore(String(data.stores[0].id));
        if (!selectedDate && data.batches?.[0]?.business_date) setSelectedDate(dateOnly(data.batches[0].business_date));
      })
      .catch(() => undefined);
  }, []);

  const dates = useMemo(() => {
    const unique = new Set<string>();
    batches
      .filter((batch) => !selectedStore || String(batch.store_id || '') === selectedStore)
      .forEach((batch) => {
        const value = dateOnly(batch.business_date);
        if (value) unique.add(value);
      });
    return Array.from(unique).sort().reverse();
  }, [batches, selectedStore]);

  const href = `${basePath}?${new URLSearchParams({
    ...(selectedStore ? { store_id: selectedStore } : {}),
    ...(selectedDate ? { business_date: selectedDate } : {}),
  }).toString()}`;

  return (
    <section className="mb-6 rounded-lg border bg-white p-4">
      <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
        <label className="block text-sm font-semibold text-slate-700">
          店铺
          <select
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
            value={selectedStore}
            onChange={(event) => setSelectedStore(event.target.value)}
          >
            <option value="">全部店铺</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name} ({store.marketplace || 'US'})
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-semibold text-slate-700">
          数据日期
          <select
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2"
            value={selectedDate}
            onChange={(event) => setSelectedDate(event.target.value)}
          >
            <option value="">全部日期</option>
            {dates.map((date) => (
              <option key={date} value={date}>
                {date}
              </option>
            ))}
          </select>
        </label>
        <a className="rounded-md bg-blue-700 px-4 py-2 text-center text-sm font-semibold text-white" href={href}>
          查看
        </a>
      </div>
      <p className="mt-3 text-xs text-slate-500">
        建议每天按店铺和真实业务日期上传报表。上传时间只是系统记录，分析默认以这里选择的数据日期为准。
      </p>
    </section>
  );
}
