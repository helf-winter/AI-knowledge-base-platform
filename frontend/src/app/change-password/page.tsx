'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { KeyRound, LogOut, ShieldCheck } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type AuthPayload = {
  access_token: string;
  username: string;
  employee_no?: string | null;
  display_name: string;
  is_first_login: boolean;
  roles: string[];
};

async function verifyPassword(password: string) {
  const token = localStorage.getItem('kb_token');
  const res = await fetch(`${API_BASE}/api/v1/auth/verify-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) return false;
  const json = await res.json();
  return Boolean(json.data?.valid);
}

async function changeInitialPassword(oldPassword: string, newPassword: string) {
  const token = localStorage.getItem('kb_token');
  const res = await fetch(`${API_BASE}/api/v1/auth/change-initial-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '修改密码失败');
  }
  const json = await res.json();
  return json.data as AuthPayload;
}

export default function ChangePasswordPage() {
  const router = useRouter();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [oldPasswordValid, setOldPasswordValid] = useState<boolean | null>(null);
  const [checkingOldPassword, setCheckingOldPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const confirmStatus = useMemo(() => {
    if (!confirmPassword) return null;
    return newPassword === confirmPassword;
  }, [confirmPassword, newPassword]);

  const canSubmit = Boolean(oldPassword && newPassword.length >= 8 && confirmStatus && oldPasswordValid !== false);

  async function checkOldPassword(value = oldPassword) {
    if (!value) {
      setOldPasswordValid(null);
      return false;
    }
    setCheckingOldPassword(true);
    const valid = await verifyPassword(value);
    setOldPasswordValid(valid);
    setCheckingOldPassword(false);
    return valid;
  }

  function logoutToLogin() {
    localStorage.removeItem('kb_token');
    localStorage.removeItem('kb_user');
    router.replace('/login');
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-white">
      <Card className="w-full max-w-md border-slate-200 bg-white text-slate-950 shadow-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl text-slate-950">
            <KeyRound size={20} className="text-blue-600" />
            首次登录修改密码
          </CardTitle>
          <CardDescription className="text-slate-700">为了保护企业知识资产，请先设置一个新的登录密码。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-800">旧密码 / 初始密码</label>
            <Input
              type="password"
              placeholder="请输入旧密码"
              value={oldPassword}
              onBlur={() => void checkOldPassword()}
              onChange={(e) => {
                setOldPassword(e.target.value);
                setOldPasswordValid(null);
              }}
            />
            {checkingOldPassword ? <div className="text-xs text-slate-500">正在校验旧密码...</div> : null}
            {oldPasswordValid === true ? <div className="text-xs text-emerald-700">旧密码校验通过</div> : null}
            {oldPasswordValid === false ? <div className="text-xs text-red-700">旧密码不正确，请重新输入</div> : null}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-800">新密码</label>
            <Input type="password" placeholder="至少 8 位" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            {newPassword && newPassword.length < 8 ? <div className="text-xs text-red-700">新密码至少需要 8 位</div> : null}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-800">确认新密码</label>
            <Input type="password" placeholder="请再次输入新密码" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
            {confirmStatus === true ? <div className="text-xs text-emerald-700">两次输入一致</div> : null}
            {confirmStatus === false ? <div className="text-xs text-red-700">两次输入的新密码不一致</div> : null}
          </div>

          {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

          <Button
            className="w-full"
            disabled={loading || !canSubmit}
            onClick={async () => {
              try {
                setLoading(true);
                setError('');
                let oldPasswordOk = oldPasswordValid === true;
                if (!oldPasswordOk) {
                  oldPasswordOk = await checkOldPassword();
                }
                if (!oldPasswordOk) {
                  setError('旧密码不正确，请重新输入');
                  return;
                }
                const result = await changeInitialPassword(oldPassword, newPassword);
                localStorage.setItem('kb_token', result.access_token);
                localStorage.setItem('kb_user', JSON.stringify(result));
                router.replace('/');
              } catch (err) {
                setError(err instanceof Error ? err.message : '修改密码失败，请稍后重试');
              } finally {
                setLoading(false);
              }
            }}
          >
            {loading ? '提交中...' : '确认修改并进入系统'}
          </Button>

          <Button variant="outline" className="w-full border-slate-300 text-slate-700" onClick={logoutToLogin}>
            <LogOut size={16} />
            暂不修改，退出并返回登录
          </Button>

          <div className="flex items-start gap-2 rounded-2xl border border-blue-100 bg-blue-50 p-3 text-xs leading-5 text-blue-900">
            <ShieldCheck size={14} className="mt-0.5 shrink-0" />
            新密码会以哈希形式存储。首次登录用户在修改密码前访问系统其他页面，会被重定向回本页。
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
