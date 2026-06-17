'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { ReactNode, useEffect, useState } from 'react';
import { FileUp, History, Home, LogOut, Puzzle, ShieldCheck, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { FloatingAssistant } from './floating-assistant';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';
const FULLSCREEN_PATHS = ['/login', '/change-password'];

const primaryNavItems = [
  { href: '/', label: '首页仪表盘', icon: Home },
  { href: '/documents', label: '知识库', icon: FileUp },
  { href: '/skills', label: '助手与技能', icon: Puzzle },
];

const supportNavItems = [
  { href: '/admin', label: '内容管理', icon: ShieldCheck, adminOnly: true },
  { href: '/tasks', label: '自动学习', icon: FileUp },
  { href: '/conversations', label: '问答记录', icon: History },
];

type UserInfo = {
  display_name?: string;
  username?: string;
  employee_no?: string | null;
  department?: string | null;
  position?: string | null;
  is_first_login?: boolean;
  roles?: string[];
};

export function SidebarShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const isAdminUser = Boolean(user?.roles?.includes('admin') || user?.roles?.includes('reviewer'));

  useEffect(() => {
    if (FULLSCREEN_PATHS.includes(pathname)) return;
    let cancelled = false;

    async function loadCurrentUser() {
      const token = localStorage.getItem('kb_token');
      if (!token) {
        setUser(null);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          localStorage.removeItem('kb_token');
          localStorage.removeItem('kb_user');
          setUser(null);
          router.replace('/login');
          return;
        }

        const json = await res.json();
        const current = json.data as UserInfo;
        if (!cancelled) {
          setUser(current);
          localStorage.setItem('kb_user', JSON.stringify(current));
          if (current.is_first_login) {
            router.replace('/change-password');
          }
        }
      } catch {
        if (!cancelled) {
          setUser(null);
        }
      }
    }

    void loadCurrentUser();

    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  if (FULLSCREEN_PATHS.includes(pathname)) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-[#f5f6fa] text-slate-950">
      <div className="flex min-h-screen w-full">
        <aside className="sticky top-0 hidden h-screen w-[272px] shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">
          <div className="flex h-14 items-center gap-3 border-b border-slate-200 px-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
              <Sparkles size={16} />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-semibold leading-5 text-slate-950">AI知识库管理平台</div>
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto px-2 pb-4">
            <div className="space-y-1">
              {primaryNavItems.map((item) => {
                const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition',
                      active ? 'bg-[#dce4fb] text-blue-700' : 'text-slate-700 hover:bg-slate-100 hover:text-slate-950',
                    )}
                  >
                    <Icon size={18} className={active ? 'text-blue-700' : 'text-slate-400'} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>

            <div className="mt-4 px-3 text-[12px] font-medium text-slate-500">管理入口</div>
            <div className="mt-2 space-y-1">
              {supportNavItems.filter((item) => !item.adminOnly || isAdminUser).map((item) => {
                const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition',
                      active ? 'bg-slate-100 text-slate-950' : 'text-slate-700 hover:bg-slate-100 hover:text-slate-950',
                    )}
                  >
                    <Icon size={18} className={active ? 'text-slate-700' : 'text-slate-400'} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </nav>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-14 items-center justify-end border-b border-slate-200 bg-white px-4 md:px-6">
            <div className="flex items-center gap-3 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-500">
              <div className="leading-5">
                <div className="text-slate-950">{user?.display_name || user?.employee_no || user?.username || '未登录'}</div>
                <div>{[user?.department, user?.position].filter(Boolean).join(' / ') || user?.roles?.join('、') || 'no roles'}</div>
              </div>
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-950"
                onClick={() => {
                  localStorage.removeItem('kb_token');
                  localStorage.removeItem('kb_user');
                  router.push('/login');
                }}
              >
                <LogOut size={14} />
                退出
              </button>
            </div>
          </header>

          <main className="min-w-0 flex-1 p-4 md:p-6">{children}</main>
          <FloatingAssistant />
        </div>
      </div>
    </div>
  );
}
