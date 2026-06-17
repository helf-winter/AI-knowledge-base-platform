'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Building2, LockKeyhole, ShieldCheck } from 'lucide-react';

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

async function login(account: string, password: string) {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_no: account, password }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '登录失败，请检查账号或密码');
  }
  const json = await res.json();
  return json.data as AuthPayload;
}

export default function LoginPage() {
  const router = useRouter();
  const [account, setAccount] = useState('admin');
  const [password, setPassword] = useState('123456');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto grid min-h-screen max-w-6xl gap-8 px-6 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <section className="space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-blue-100">
            <Building2 size={16} />
            企业内部知识管理平台
          </div>
          <div className="space-y-4">
            <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">让企业知识被安全地生产、流转和复用</h1>
            <p className="max-w-xl text-base leading-7 text-slate-300">
              平台面向企业内部员工开放。请使用企业工号或管理员账号登录，首次登录需要完成密码修改。
            </p>
          </div>
          <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">员工身份认证</div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">首次登录改密</div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">角色与权限审计</div>
          </div>
        </section>

        <Card className="border-white/10 bg-white text-slate-950 shadow-2xl">
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
              <Input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="请输入密码" />
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
              <div>普通员工：E1001 / 初始密码 654321</div>
              <div className="mt-2 text-slate-500">首次登录后必须修改密码，才能进入系统首页。</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
