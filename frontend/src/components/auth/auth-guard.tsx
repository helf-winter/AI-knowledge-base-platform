'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

const PUBLIC_PATHS = ['/login'];
const CHANGE_PASSWORD_PATH = '/change-password';
const ADMIN_PATHS = ['/admin', '/tasks'];

type StoredUser = {
  is_first_login?: boolean;
  roles?: string[];
};

function readStoredToken() {
  try {
    return localStorage.getItem('kb_token');
  } catch {
    return null;
  }
}

function readStoredUser(): StoredUser | null {
  try {
    const raw = localStorage.getItem('kb_user');
    return raw ? (JSON.parse(raw) as StoredUser) : null;
  } catch {
    return null;
  }
}

function clearStoredAuth() {
  try {
    localStorage.removeItem('kb_token');
    localStorage.removeItem('kb_user');
  } catch {
    // Ignore storage failures and let the router send the user back to login.
  }
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let token: string | null = null;
    let user: StoredUser | null = null;
    try {
      token = typeof window !== 'undefined' ? readStoredToken() : null;
      user = typeof window !== 'undefined' ? readStoredUser() : null;
    } catch {
      clearStoredAuth();
      token = null;
      user = null;
    }
    const isPublic = PUBLIC_PATHS.includes(pathname);
    const isChangePassword = pathname === CHANGE_PASSWORD_PATH;
    const isAdminPath = ADMIN_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
    const isAdminUser = Boolean(user?.roles?.includes('admin') || user?.roles?.includes('reviewer'));

    if (!token && !isPublic) {
      setReady(true);
      router.replace('/login');
      return;
    }

    if (token && user?.is_first_login && !isChangePassword) {
      setReady(false);
      router.replace(CHANGE_PASSWORD_PATH);
      return;
    }

    if (token && isAdminPath && !isAdminUser) {
      setReady(false);
      router.replace('/');
      return;
    }

    if (token && !user?.is_first_login && (pathname === '/login' || isChangePassword)) {
      setReady(true);
      router.replace('/');
      return;
    }

    setReady(true);
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-sm text-slate-200">
        正在验证登录状态...
      </div>
    );
  }

  return <>{children}</>;
}
