'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ShieldCheck, Sparkles } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type AuthPayload = { access_token: string; username: string; display_name: string; roles: string[] };

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
  return json.data as AuthPayload;
}

async function register(username: string, password: string, displayName: string, email: string) {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, display_name: displayName, email: email || undefined }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '注册失败');
  }
  const json = await res.json();
  return json.data as AuthPayload;
}

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('123456');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);

  return (
    <div className="mx-auto flex min-h-screen max-w-md items-center px-4">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ShieldCheck size={18} /> {mode === 'login' ? '登录系统' : '注册账号'}</CardTitle>
          <CardDescription>{mode === 'login' ? '已有账号请直接登录进入系统。' : '注册后即可直接使用知识库与问答能力。'}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {mode === 'register' ? (
            <>
              <Input placeholder="昵称 / 显示名称" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
              <Input placeholder="邮箱（可选）" value={email} onChange={(e) => setEmail(e.target.value)} />
            </>
          ) : null}
          <Input placeholder="用户名" value={username} onChange={(e) => setUsername(e.target.value)} />
          <Input placeholder="密码" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Button
            className="w-full"
            disabled={loading || (mode === 'register' && (!displayName || !username || !password))}
            onClick={async () => {
              try {
                setLoading(true);
                const result = mode === 'login'
                  ? await login(username, password)
                  : await register(username, password, displayName, email);
                localStorage.setItem('kb_token', result.access_token);
                localStorage.setItem('kb_user', JSON.stringify(result));
                router.push('/');
              } catch (error) {
                alert(error instanceof Error ? error.message : (mode === 'login' ? '登录失败' : '注册失败'));
              } finally {
                setLoading(false);
              }
            }}
          >
            {loading ? (mode === 'login' ? '登录中...' : '注册中...') : (mode === 'login' ? '登录' : '注册并进入系统')}
          </Button>
          <button type="button" className="w-full text-sm text-blue-600" onClick={() => setMode((v) => (v === 'login' ? 'register' : 'login'))}>
            {mode === 'login' ? '没有账号？去注册' : '已有账号？去登录'}
          </button>
          <div className="flex items-center gap-2 text-xs text-muted"><Sparkles size={14} /> 登录或注册后即可访问知识库、Agent 与问答能力。</div>
        </CardContent>
      </Card>
    </div>
  );
}
