import { vi } from "vitest";

type Handler = (url: URL, init?: RequestInit) => unknown;

/** Route `fetch` calls to handlers keyed by "METHOD /path"; records every call. */
export function mockApi(routes: Record<string, Handler>) {
  const calls: { key: string; url: URL; body: unknown }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const key = `${init?.method ?? "GET"} ${url.pathname}`;
    calls.push({ key, url, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const handler = routes[key];
    if (!handler) return new Response(JSON.stringify({ detail: `no mock for ${key}` }), { status: 404 });
    const result = handler(url, init);
    if (result instanceof Response) return result;
    return new Response(JSON.stringify(result), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}
