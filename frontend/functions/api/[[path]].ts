type PagesContext = {
  request: Request;
  env: {
    BACKEND_API_URL?: string;
  };
  params: {
    path?: string | string[];
  };
};

const DEFAULT_BACKEND = 'https://api.toolsfinderhub.com/amazon-auto-select';

function backendUrl(context: PagesContext) {
  const backend = (context.env.BACKEND_API_URL || DEFAULT_BACKEND).replace(/\/+$/, '');
  const path = Array.isArray(context.params.path) ? context.params.path.join('/') : context.params.path || '';
  const source = new URL(context.request.url);
  const target = new URL(`${backend}/api/${path}`);
  target.search = source.search;
  return target;
}

export async function onRequest(context: PagesContext) {
  const target = backendUrl(context);
  const headers = new Headers(context.request.headers);
  headers.delete('host');

  const response = await fetch(target.toString(), {
    method: context.request.method,
    headers,
    body: ['GET', 'HEAD'].includes(context.request.method) ? undefined : context.request.body,
    redirect: 'manual',
  });

  const nextHeaders = new Headers(response.headers);
  nextHeaders.set('Access-Control-Allow-Origin', '*');
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: nextHeaders,
  });
}
