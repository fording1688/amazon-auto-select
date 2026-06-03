import Link from 'next/link';

export default function ListingSubnav({ projectId }: { projectId?: string }) {
  const detailBase = projectId ? `/listing-projects/detail?id=${projectId}` : '/listing-projects';
  const links = [
    ['项目列表', '/listing-projects'],
    ['新建项目', '/listing-projects/new'],
    ['同行参考资料', projectId ? `${detailBase}#competitors` : '/listing-projects'],
    ['文案生成', projectId ? `${detailBase}#generate` : '/listing-projects'],
    ['图片 Prompt', projectId ? `${detailBase}#image-prompts` : '/listing-projects'],
    ['A+ 页面', projectId ? `${detailBase}#aplus` : '/listing-projects'],
    ['版本管理', projectId ? `${detailBase}#versions` : '/listing-projects'],
  ];
  return (
    <div className="mb-6 flex flex-wrap gap-2 rounded-lg border bg-white p-3">
      {links.map(([label, href]) => (
        <Link className="rounded-md px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-blue-50 hover:text-blue-700" href={href} key={`${label}-${href}`}>
          {label}
        </Link>
      ))}
    </div>
  );
}
