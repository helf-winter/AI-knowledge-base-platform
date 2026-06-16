'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  BookOpenCheck,
  Bot,
  FileText,
  History,
  ListChecks,
  RefreshCw,
  Search,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type DocumentItem = {
  document_id: string;
  file_name: string;
  file_type: string;
  parse_status: string;
  updated_at?: string | null;
};

type TaskItem = {
  task_id: string;
  task_type: string;
  status: string;
  retry_count: number;
  updated_at?: string | null;
};

type KnowledgeMetadata = {
  knowledge_id: string;
  document_id: string;
  title: string;
  status: string;
  knowledge_type: string;
};

type ConversationTurn = {
  turn_id: string;
  query_text: string;
  confidence?: number | null;
  created_at?: string | null;
};

type LearningAnalysis = {
  total_gaps?: number;
  insights?: Array<{
    topic: string;
    count: number;
    suggested_title: string;
  }>;
};

function getToken() {
  return typeof window !== 'undefined' ? localStorage.getItem('kb_token') : null;
}

async function authedFetch(url: string, init?: RequestInit) {
  const token = getToken();
  const headers = new Headers(init?.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...init, headers });
}

async function fetchJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await authedFetch(`${API_BASE}${path}`);
    if (!res.ok) return fallback;
    const json = await res.json();
    return (json.data ?? fallback) as T;
  } catch {
    return fallback;
  }
}

function statusTone(status: string) {
  if (['succeeded', 'available', 'active'].includes(status)) return 'bg-emerald-50 text-emerald-700 hover:bg-emerald-50';
  if (['failed', 'disabled'].includes(status)) return 'bg-red-50 text-red-700 hover:bg-red-50';
  if (['running', 'reviewing'].includes(status)) return 'bg-blue-50 text-blue-700 hover:bg-blue-50';
  return 'bg-slate-100 text-slate-700 hover:bg-slate-100';
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeMetadata[]>([]);
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [learning, setLearning] = useState<LearningAnalysis>({});
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [docItems, taskItems, knowledgeItems, turnItems, learningData] = await Promise.all([
        fetchJson<DocumentItem[]>('/api/v1/documents?limit=8&offset=0', []),
        fetchJson<TaskItem[]>('/api/v1/tasks', []),
        fetchJson<KnowledgeMetadata[]>('/api/v1/admin/knowledge-metadata', []),
        fetchJson<ConversationTurn[]>('/api/v1/conversation/turns', []),
        fetchJson<LearningAnalysis>('/api/v1/flywheel/learning?status=pending', {}),
      ]);
      setDocuments(docItems);
      setTasks(taskItems);
      setKnowledge(knowledgeItems);
      setTurns(turnItems);
      setLearning(learningData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const summary = useMemo(() => {
    const failedTasks = tasks.filter((task) => task.status === 'failed').length;
    const runningTasks = tasks.filter((task) => task.status === 'running' || task.status === 'pending').length;
    const availableKnowledge = knowledge.filter((item) => item.status === 'available').length;
    return [
      { label: '知识文档', value: documents.length, hint: '可检索文档', icon: FileText },
      { label: '知识条目', value: knowledge.length, hint: `${availableKnowledge} 条可用`, icon: BookOpenCheck },
      { label: '自动学习', value: learning.total_gaps ?? 0, hint: '待处理缺口', icon: Sparkles },
      { label: '任务状态', value: tasks.length, hint: `${runningTasks} 执行中 / ${failedTasks} 失败`, icon: ListChecks },
    ];
  }, [documents.length, knowledge, learning.total_gaps, tasks]);

  const latestTasks = tasks.slice(0, 5);
  const latestTurns = turns.slice(0, 4);
  const topInsights = learning.insights?.slice(0, 3) ?? [];

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
              <TrendingUp size={14} /> 企业知识工作台
            </div>
            <h1 className="text-2xl font-semibold text-slate-950 md:text-3xl">知识生产、管理、消费与自动学习闭环</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              这里汇总文档导入、知识条目、问答记录和自动学习任务，适合作为项目演示的第一屏。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild>
              <Link href="/documents">
                <Search size={16} /> 检索知识
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/tasks">
                <Sparkles size={16} /> 自动学习
              </Link>
            </Button>
            <Button onClick={() => void load()} disabled={loading} variant="outline">
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summary.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.label} className="rounded-2xl border-slate-200 bg-white shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm text-slate-500">{item.label}</div>
                    <div className="mt-2 text-3xl font-semibold text-slate-950">{item.value}</div>
                    <div className="mt-1 text-xs text-slate-500">{item.hint}</div>
                  </div>
                  <div className="rounded-xl bg-blue-50 p-2 text-blue-700">
                    <Icon size={18} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-950">
              <Sparkles size={16} /> 自动学习入口
            </CardTitle>
            <CardDescription className="text-slate-600">从低置信度问答和反馈中提炼知识缺口，再进入任务队列。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {topInsights.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
                暂无待提炼缺口。可以先在右下角助手里提出无法命中的问题，再回到这里观察闭环。
              </div>
            ) : (
              topInsights.map((item) => (
                <div key={item.topic} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-medium text-slate-950">{item.suggested_title || item.topic}</div>
                    <Badge className="bg-blue-50 text-blue-700 hover:bg-blue-50">{item.count} 次</Badge>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">主题：{item.topic}</div>
                </div>
              ))
            )}
            <div className="flex flex-wrap gap-2">
              <Button asChild>
                <Link href="/tasks">
                  查看自动学习 <ArrowRight size={14} />
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/admin">处理知识条目</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-950">
              <Bot size={16} /> 最近问答
            </CardTitle>
            <CardDescription className="text-slate-600">用于证明知识消费端已经能记录回答、引用和置信度。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {latestTurns.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">暂无问答记录。</div>
            ) : (
              latestTurns.map((turn) => (
                <div key={turn.turn_id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="line-clamp-2 text-sm font-medium text-slate-950">{turn.query_text}</div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span>置信度：{turn.confidence == null ? '-' : turn.confidence.toFixed(2)}</span>
                    <span>时间：{turn.created_at ?? '-'}</span>
                  </div>
                </div>
              ))
            )}
            <Button asChild variant="outline" className="w-full">
              <Link href="/conversations">
                <History size={14} /> 查看问答记录
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="text-base text-slate-950">最近文档</CardTitle>
            <CardDescription className="text-slate-600">快速回到文档详情，检查解析和检索效果。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {documents.slice(0, 5).map((doc) => (
              <Link key={doc.document_id} href={`/documents/${doc.document_id}`} className="block rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-blue-200 hover:bg-blue-50">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0 truncate text-sm font-medium text-slate-950">{doc.file_name}</div>
                  <Badge className={statusTone(doc.parse_status)}>{doc.parse_status}</Badge>
                </div>
                <div className="mt-2 text-xs text-slate-500">类型：{doc.file_type} · 更新：{doc.updated_at ?? '-'}</div>
              </Link>
            ))}
            {documents.length === 0 ? <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">暂无文档。</div> : null}
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="text-base text-slate-950">任务队列</CardTitle>
            <CardDescription className="text-slate-600">包含文档解析、批处理和自动学习任务。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {latestTasks.map((task) => (
              <div key={task.task_id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-medium text-slate-950">{task.task_type}</div>
                  <Badge className={statusTone(task.status)}>{task.status}</Badge>
                </div>
                <div className="mt-2 text-xs text-slate-500">重试：{task.retry_count} · 更新：{task.updated_at ?? '-'}</div>
              </div>
            ))}
            {latestTasks.length === 0 ? <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">暂无任务。</div> : null}
            <Button asChild variant="outline" className="w-full">
              <Link href="/tasks">进入任务监控</Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
