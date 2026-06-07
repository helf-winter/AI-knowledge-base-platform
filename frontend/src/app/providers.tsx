'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

function installAuthFetch() {
  if (typeof window === 'undefined') return;

  const originalFetch = window.fetch.bind(window);
  if ((window as Window & { __kb_fetch_patched?: boolean }).__kb_fetch_patched) return;

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const token = localStorage.getItem('kb_token');
    const headers = new Headers(init?.headers || {});

    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await originalFetch(input, {
      ...init,
      headers,
    });

    if (response.status === 401) {
      localStorage.removeItem('kb_token');
      localStorage.removeItem('kb_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    return response;
  };

  (window as Window & { __kb_fetch_patched?: boolean }).__kb_fetch_patched = true;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());

  useEffect(() => {
    installAuthFetch();
  }, []);

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
