'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Settings2, RefreshCw, Sparkles } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type SettingRow = { label: string; value: string };

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingRow[]>([
    { label: 'API Base', value: API_BASE },
    { label: 'Model', value: 'deepseek' },
    { label: 'Embedding', value: 'bge-m3 / 1024 dim' },
    { label: 'Storage', value: 'PostgreSQL + pgvector' },
  ]);
  const [apiBase, setApiBase] = useState(API_BASE);

  useEffect(() => {
    setSettings([
      { label: 'API Base', value: apiBase },
      { label: 'Model', value: 'deepseek' },
      { label: 'Embedding', value: 'bge-m3 / 1024 dim' },
      { label: 'Storage', value: 'PostgreSQL + pgvector' },
    ]);
  }, [apiBase]);

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Settings2 size={18} /> 系统设置</CardTitle>
          <CardDescription>API、模型、存储与运行参数管理。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted">
          <p>后续这里会放系统配置表单、环境状态、服务开关和模型切换。</p>
          <Input value={apiBase} onChange={(e) => setApiBase(e.target.value)} placeholder="API Base URL" />
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setApiBase(API_BASE)}>
              <RefreshCw size={16} /> 重置
            </Button>
            <Badge>API Base</Badge>
            <Badge>Model Config</Badge>
            <Badge>Storage</Badge>
            <Badge>Feature Flags</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>配置方向</CardTitle>
          <CardDescription>让平台参数化，不把关键配置写死在代码里。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted">
          {settings.map((item) => (
            <div key={item.label} className="rounded-2xl border border-border bg-white/5 p-4">
              <div className="text-xs text-muted">{item.label}</div>
              <div className="mt-1 text-sm text-text">{item.value}</div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="xl:col-span-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Sparkles size={18} /> 下一步扩展</CardTitle>
          <CardDescription>后续会加入模型配置、鉴权配置、环境开关和运行状态面板。</CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
