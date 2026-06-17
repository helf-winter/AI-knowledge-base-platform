'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

const PUBLIC_PATHS = ['/login'];
const CHANGE_PASSWORD_PATH = '/change-password';

type StoredUser = {
  is_first_login?: boolean;
};

function readStoredUser(): StoredUser | null {
  try {
    const raw = localStorage.getItem('kb_user');
    return raw ? (JSON.parse(raw) as StoredUser) : null;
  } catch {
    return null;
  }
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('kb_token') : null;
    const user = typeof window !== 'undefined' ? readStoredUser() : null;
    const isPublic = PUBLIC_PATHS.includes(pathname);
    const isChangePassword = pathname === CHANGE_PASSWORD_PATH;

    if (!token && !isPublic) {
      setReady(true);
      router.replace('/login');
      return;
    }

    if (token && user?.is_first_login && !isChangePassword) {
      setReady(true);
      router.replace(CHANGE_PASSWORD_PATH);
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
