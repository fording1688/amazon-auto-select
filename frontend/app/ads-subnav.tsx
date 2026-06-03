import Link from 'next/link';

export default function AdsSubnav() {
  const links = [
    ['广告诊断', '/ads-diagnosis'],
    ['广告建议中心', '/recommendations'],
  ];
  return (
    <div className="mb-6 flex flex-wrap gap-2 rounded-lg border bg-white p-3">
      {links.map(([label, href]) => (
        <Link className="rounded-md px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-blue-50 hover:text-blue-700" href={href} key={href}>
          {label}
        </Link>
      ))}
    </div>
  );
}
