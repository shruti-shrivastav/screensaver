export const API = {
  async get(url: string, opts: RequestInit = {}) {
    opts.credentials = 'include';
    const res = await fetch(url, opts);
    if (res.status === 401) {
      window.dispatchEvent(new Event('app:unauthorized'));
      return null;
    }
    return res;
  },

  async post(url: string, body: any, opts: RequestInit = {}) {
    opts.method = 'POST';
    opts.headers = { ...opts.headers, 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
    opts.credentials = 'include';
    const res = await fetch(url, opts);
    if (res.status === 401) {
      window.dispatchEvent(new Event('app:unauthorized'));
      return null;
    }
    return res;
  },

  async json(res: Response | null) {
    if (!res) return null;
    try {
      return await res.json();
    } catch {
      return null;
    }
  }
}
