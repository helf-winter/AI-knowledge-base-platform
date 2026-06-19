'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Building2, Eye, EyeOff, LockKeyhole, Network, ShieldCheck, Sparkles } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type AuthPayload = {
  access_token: string;
  username: string;
  employee_no?: string | null;
  display_name: string;
  department?: string | null;
  position?: string | null;
  permission_level: number;
  is_first_login: boolean;
  status: string;
  roles: string[];
};

function normalizeLoginError(status: number, body: string) {
  let detail = body;
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === 'string') {
      detail = parsed.detail;
    }
  } catch {
    detail = body;
  }

  const normalized = detail.toLowerCase();
  if (status === 401 || normalized.includes('invalid credentials')) {
    return '账号或密码错误，请重新输入';
  }
  if (status === 403 || normalized.includes('disabled')) {
    return '该账号已被禁用，请联系管理员';
  }
  if (status >= 500) {
    return '服务器暂时不可用，请稍后再试';
  }
  return detail || '登录失败，请检查账号或密码';
}

async function login(account: string, password: string) {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_no: account, password }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(normalizeLoginError(res.status, text));
  }
  const json = await res.json();
  return json.data as AuthPayload;
}

export default function LoginPage() {
  const router = useRouter();
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#06111f] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(45,212,191,0.22),transparent_32%),radial-gradient(circle_at_82%_14%,rgba(59,130,246,0.24),transparent_30%),linear-gradient(135deg,#07111f_0%,#0f2543_46%,#07111f_100%)]" />
      <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(148,163,184,0.12)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.12)_1px,transparent_1px)] [background-size:42px_42px]" />
      <div className="absolute left-[12%] top-[18%] h-56 w-56 rounded-full border border-cyan-300/20 bg-cyan-300/10 blur-2xl" />
      <div className="absolute bottom-[8%] right-[8%] h-72 w-72 rounded-full border border-blue-300/20 bg-blue-500/10 blur-3xl" />
      <div className="pointer-events-none absolute left-[8%] top-[55%] hidden w-64 rotate-[-7deg] rounded-2xl border border-white/10 bg-white/8 p-4 shadow-2xl backdrop-blur md:block">
        <div className="mb-3 flex items-center gap-2 text-xs text-cyan-100"><Network size={14} /> Knowledge Flow</div>
        <div className="space-y-2">
          <div className="h-2 w-4/5 rounded bg-cyan-200/50" />
          <div className="h-2 w-3/5 rounded bg-blue-200/35" />
          <div className="h-2 w-2/3 rounded bg-slate-200/25" />
        </div>
      </div>
      <div className="pointer-events-none absolute right-[34%] top-[18%] hidden w-52 rotate-6 rounded-2xl border border-white/10 bg-white/10 p-4 shadow-2xl backdrop-blur lg:block">
        <div className="mb-3 flex items-center gap-2 text-xs text-blue-100"><Sparkles size={14} /> AI Review</div>
        <div className="grid grid-cols-3 gap-2">
          <div className="h-10 rounded-lg bg-cyan-300/20" />
          <div className="h-10 rounded-lg bg-blue-300/20" />
          <div className="h-10 rounded-lg bg-white/15" />
        </div>
      </div>

      <div className="relative mx-auto grid min-h-screen max-w-6xl gap-8 px-6 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <section className="space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm text-blue-100 backdrop-blur">
            <Building2 size={16} />
            企业内部知识管理平台
          </div>
          <div className="space-y-4">
            <h1 className="max-w-2xl text-4xl font-semibold tracking-tight md:text-5xl">
              让企业知识被安全生产、流转和复用
            </h1>
            <p className="max-w-xl text-base leading-7 text-slate-300">
              面向企业内部员工开放。请使用企业工号或管理员账号登录，首次登录需要完成密码修改。
            </p>
          </div>
          <div className="grid gap-3 text-sm text-slate-200 md:grid-cols-3">
            <div className="rounded-xl bg-white/6 px-4 py-3 backdrop-blur">员工身份认证</div>
            <div className="rounded-xl bg-white/6 px-4 py-3 backdrop-blur">首次登录改密</div>
            <div className="rounded-xl bg-white/6 px-4 py-3 backdrop-blur">角色与权限审计</div>
          </div>
        </section>

        <Card className="border-white/20 bg-white/95 text-slate-950 shadow-2xl backdrop-blur">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl text-slate-950">
              <ShieldCheck size={20} />
              企业账号登录
            </CardTitle>
            <CardDescription className="text-slate-600">生产环境不开放自助注册，由管理员分配账号。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-800">工号 / 管理员账号</label>
              <Input value={account} onChange={(e) => setAccount(e.target.value.trim())} placeholder="例如 admin 或 E1001" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-800">密码</label>
              <div className="relative">
                <Input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type={showPassword ? 'text' : 'password'}
                  placeholder="请输入密码"
                  className="pr-12"
                />
                <button
                  type="button"
                  aria-label="按住显示密码"
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
                  onMouseDown={() => setShowPassword(true)}
                  onMouseUp={() => setShowPassword(false)}
                  onMouseLeave={() => setShowPassword(false)}
                  onTouchStart={() => setShowPassword(true)}
                  onTouchEnd={() => setShowPassword(false)}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

            <Button
              className="w-full"
              disabled={loading || !account || !password}
              onClick={async () => {
                try {
                  setLoading(true);
                  setError('');
                  const result = await login(account, password);
                  localStorage.setItem('kb_token', result.access_token);
                  localStorage.setItem('kb_user', JSON.stringify(result));
                  router.replace(result.is_first_login ? '/change-password' : '/');
                } catch (err) {
                  setError(err instanceof Error ? err.message : '登录失败，请稍后重试');
                } finally {
                  setLoading(false);
                }
              }}
            >
              {loading ? '登录中...' : '登录'}
            </Button>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs leading-5 text-slate-700">
              <div className="flex items-center gap-2 font-medium text-slate-900">
                <LockKeyhole size={14} />
                演示账号
              </div>
              <div className="mt-2">管理员：admin / 初始密码 123456</div>
              <div>普通员工：E1001、E1002、E1003 / 初始密码 654321</div>
              <div className="mt-2 text-slate-500">首次登录后必须修改密码，才能进入系统首页。</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
