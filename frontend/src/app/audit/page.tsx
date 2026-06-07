'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RefreshCw, FileSearch, Filter, Sparkles, ArrowRight, ShieldCheck, MessageSquareText, FileUp } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type AuditLog = {
  log_id: string;
  user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  trace_id: string;
  payload_json?: string | null;
  created_at?: string | null;
};

type AuditSummary = {
  total: number;
  by_action: Record<string, number>;
  by_resource: Record<string, number>;
};

async function fetchAuditLogs(traceId?: string) {
  const url = new URL(`${API_BASE}/api/v1/audit/logs`);
  if (traceId) url.searchParams.set('trace_id', traceId);
  const res = await fetch(url.toString());
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `加载审计日志失败 (${res.status})`);
  }
  const json = await res.json();
  return json.data as AuditLog[];
}

const ACTION_LABELS: Record<string, string> = {
  login: '登录',
  upload_document: '上传文档',
  delete_document: '删除文档',
  chat_stream: 'AI问答',
  chat_stream_failed: 'AI问答失败',
  feedback: '反馈',
  create_gap: '创建知识缺口',
  create_metadata: '创建知识条目',
  update_metadata: '更新知识条目',
  review_metadata: '审核知识条目',
  archive_metadata: '归档知识条目',
  delete_metadata: '删除知识条目',
};

function getActionLabel(action: string) {
  return ACTION_LABELS[action] ?? action;
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [traceId, setTraceId] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [resourceFilter, setResourceFilter] = useState('');

  const summary = useMemo<AuditSummary>(() => {
    const byAction: Record<string, number> = {};
    const byResource: Record<string, number> = {};
    logs.forEach((log) => {
      byAction[log.action] = (byAction[log.action] || 0) + 1;
      byResource[log.resource_type] = (byResource[log.resource_type] || 0) + 1;
    });
    return { total: logs.length, by_action: byAction, by_resource: byResource };
  }, [logs]);

  const load = async () => {
    setLoading(true);
    try {
      setLogs(await fetchAuditLogs(traceId || undefined));
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [traceId]);

  const filteredLogs = logs.filter((log) => {
    const actionOk = !actionFilter || log.action.includes(actionFilter);
    const resourceOk = !resourceFilter || log.resource_type.includes(resourceFilter);
    return actionOk && resourceOk;
  });

  const quickStats = [
    { label: '问答', value: summary.by_resource.conversation || 0, href: '/conversations', icon: MessageSquareText },
    { label: '任务', value: summary.by_resource.task || 0, href: '/tasks', icon: FileUp },
    { label: '知识', value: summary.by_resource.document || 0, href: '/documents', icon: ShieldCheck },
    { label: '更多', value: summary.total, href: '/skills', icon: ArrowRight },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        {quickStats.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.label} href={item.href} className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_28px_rgba(15,23,42,0.08)]">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-xs font-medium uppercase tracking-[0.18em] text-[color:var(--muted)]">{item.label}</div>
                  <div className="mt-2 text-2xl font-semibold text-[color:var(--text)]">{item.value}</div>
                </div>
                <div className="rounded-2xl bg-slate-100 p-3 text-slate-700">
                  <Icon size={18} />
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-900"><FileSearch size={18} /> 操作筛选</CardTitle>
          <CardDescription className="text-slate-700">按 trace、动作、资源类型快速过滤。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-3">
            <Input placeholder="按 trace_id 过滤" value={traceId} onChange={(e) => setTraceId(e.target.value)} />
            <Input placeholder="按 action 过滤" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} />
            <Input placeholder="按 resource_type 过滤" value={resourceFilter} onChange={(e) => setResourceFilter(e.target.value)} />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => void load()} disabled={loading} variant="outline">
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
            </Button>
            <Button variant="outline" onClick={() => { setTraceId(''); setActionFilter(''); setResourceFilter(''); }} disabled={loading && !traceId && !actionFilter && !resourceFilter}>
              清空过滤
            </Button>
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700">
              当前共 {summary.total} 条记录
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-slate-700">
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">动作：{Object.keys(summary.by_action).length}</Badge>
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">资源：{Object.keys(summary.by_resource).length}</Badge>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {filteredLogs.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-sm text-muted">暂无审计记录</CardContent>
          </Card>
        ) : (
          filteredLogs.map((log) => (
            <Card key={log.log_id} className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
              <CardContent className="space-y-4 p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--text)]">
                      <span>{getActionLabel(log.action)}</span>
                      <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{log.resource_type}</Badge>
                    </div>
                    <div className="mt-1 text-xs text-[color:var(--muted)]">{log.resource_type} / {log.resource_id || '-'}</div>
                  </div>
                  <Badge className="bg-slate-100 text-slate-900 hover:bg-slate-100">{log.user_id || 'system'}</Badge>
                </div>

                <div className="grid gap-2 text-sm text-[color:var(--muted)] md:grid-cols-3">
                  <div>Trace：{log.trace_id}</div>
                  <div>时间：{log.created_at ?? '-'}</div>
                  <div>资源：{log.resource_type}</div>
                </div>

                <div className="rounded-2xl border border-[color:var(--border)] bg-black/20 p-4 text-xs leading-6 text-[color:var(--text)] break-all">
                  {log.payload_json || '无 payload'}
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/audit?trace_id=${encodeURIComponent(log.trace_id)}`}>
                      <Filter size={14} /> 按 Trace 过滤
                    </Link>
                  </Button>
                  {log.resource_type === 'conversation' ? (
                    <Button asChild size="sm" variant="outline">
                      <Link href="/conversations">
                        <MessageSquareText size={14} /> 去问答记录
                      </Link>
                    </Button>
                  ) : null}
                  {log.resource_type === 'document' ? (
                    <Button asChild size="sm" variant="outline">
                      <Link href="/documents">
                        <FileUp size={14} /> 去知识库
                      </Link>
                    </Button>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
