'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ShieldCheck, Sparkles } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

async function login(username: string, password: string) {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '登录失败');
  }
  const json = await res.json();
  return json.data as { access_token: string; username: string; display_name: string; roles: string[] };
}

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('123456');
  const [loading, setLoading] = useState(false);

  return (
    <div className="mx-auto flex min-h-screen max-w-md items-center px-4">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ShieldCheck size={18} /> 登录系统</CardTitle>
          <CardDescription>企业知识库管理平台登录入口。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input placeholder="用户名" value={username} onChange={(e) => setUsername(e.target.value)} />
          <Input placeholder="密码" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Button
            className="w-full"
            disabled={loading}
            onClick={async () => {
              try {
                setLoading(true);
                const result = await login(username, password);
                localStorage.setItem('kb_token', result.access_token);
                localStorage.setItem('kb_user', JSON.stringify(result));
                router.push('/');
              } catch (error) {
                alert(error instanceof Error ? error.message : '登录失败');
              } finally {
                setLoading(false);
              }
            }}
          >
            {loading ? '登录中...' : '登录'}
          </Button>
          <div className="flex items-center gap-2 text-xs text-muted"><Sparkles size={14} /> 登录后即可访问后台各模块。</div>
        </CardContent>
      </Card>
    </div>
  );
}
