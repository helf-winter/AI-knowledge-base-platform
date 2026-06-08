'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RefreshCw, MessageSquareText, Filter, ArrowRight } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type ConversationItem = {
  turn_id: string;
  session_id: string;
  user_id?: string | null;
  query_text: string;
  answer_text: string;
  confidence: number;
  source_refs_json: string;
  model_name: string;
  prompt_version: string;
  trace_id?: string | null;
};

function getAuthHeaders() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('kb_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchConversations(sessionId?: string) {
  const url = new URL(`${API_BASE}/api/v1/conversation/turns`);
  if (sessionId) url.searchParams.set('session_id', sessionId);
  const res = await fetch(url.toString(), { headers: getAuthHeaders() });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '加载会话历史失败');
  }
  const json = await res.json();
  return json.data as ConversationItem[];
}

export default function ConversationsPage() {
  const [items, setItems] = useState<ConversationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [traceId, setTraceId] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      setItems(await fetchConversations(sessionId || undefined));
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const sessionOk = !sessionId || item.session_id.includes(sessionId);
      const traceOk = !traceId || (item.trace_id ?? '').includes(traceId);
      return sessionOk && traceOk;
    });
  }, [items, sessionId, traceId]);

  const stats = useMemo(() => {
    const total = items.length;
    const avgConfidence = total ? items.reduce((sum, item) => sum + item.confidence, 0) / total : 0;
    const sessions = new Set(items.map((item) => item.session_id)).size;
    return { total, avgConfidence, sessions };
  }, [items]);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="bg-white shadow-sm"><CardContent className="p-4"><div className="text-xs text-slate-600">会话条数</div><div className="mt-2 text-2xl font-semibold text-slate-900">{stats.total}</div></CardContent></Card>
        <Card className="bg-white shadow-sm"><CardContent className="p-4"><div className="text-xs text-slate-600">会话数</div><div className="mt-2 text-2xl font-semibold text-slate-900">{stats.sessions}</div></CardContent></Card>
        <Card className="bg-white shadow-sm"><CardContent className="p-4"><div className="text-xs text-slate-600">平均置信度</div><div className="mt-2 text-2xl font-semibold text-slate-900">{stats.avgConfidence.toFixed(3)}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-900"><Filter size={18} /> 筛选与刷新</CardTitle>
          <CardDescription className="text-slate-600">可按 session_id / trace_id 过滤当前展示结果。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <Input placeholder="按 session_id 过滤" value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
            <Input placeholder="按 trace_id 过滤" value={traceId} onChange={(e) => setTraceId(e.target.value)} />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => void load()} disabled={loading} variant="outline">
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setSessionId('');
                setTraceId('');
              }}
            >
              清空筛选
            </Button>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-700">
              当前显示 {filteredItems.length} 条
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {filteredItems.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-sm text-slate-600">暂无会话记录</CardContent>
          </Card>
        ) : (
          filteredItems.map((item) => (
            <Card key={item.turn_id} className="border-slate-200 bg-white shadow-sm">
              <CardContent className="space-y-4 p-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="font-medium text-slate-900">{item.query_text}</div>
                    <div className="mt-1 text-xs text-slate-500">Session: {item.session_id}</div>
                  </div>
                  <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{item.model_name}</Badge>
                </div>

                <div className="grid gap-2 text-sm text-slate-600 md:grid-cols-4">
                  <div>Confidence: {item.confidence.toFixed(3)}</div>
                  <div>Prompt: {item.prompt_version}</div>
                  <div>Trace: {item.trace_id || '-'}</div>
                  <div>User: {item.user_id || '-'}</div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-900">
                  {item.answer_text}
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600 break-all">
                  Refs: {item.source_refs_json}
                </div>

                <div className="flex flex-wrap gap-2">
                  {item.trace_id ? (
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/audit?trace_id=${encodeURIComponent(item.trace_id)}`}>
                        <ArrowRight size={14} /> 去操作记录
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
