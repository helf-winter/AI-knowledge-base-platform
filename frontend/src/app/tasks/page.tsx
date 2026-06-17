'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, BrainCircuit, ListChecks, Play, RefreshCw, RotateCcw, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { issueTypeLabel, reviewStatusLabel, taskStatusLabel, taskTypeLabel } from '@/lib/display-labels';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type TaskItem = {
  task_id: string;
  task_type: string;
  related_document_id?: string | null;
  status: string;
  retry_count: number;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type LearningInsight = {
  topic: string;
  count: number;
  sample_questions: string[];
  suggested_title: string;
  suggested_content: string;
};

type LearningAnalysis = {
  insights: LearningInsight[];
  total_gaps: number;
  status: string;
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

async function fetchTasks() {
  const res = await authedFetch(`${API_BASE}/api/v1/tasks`);
  if (!res.ok) throw new Error('加载任务列表失败');
  const json = await res.json();
  return json.data as TaskItem[];
}

async function fetchLearning(status: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/flywheel/learning?status=${encodeURIComponent(status)}`);
  if (!res.ok) throw new Error('加载自动学习分析失败');
  const json = await res.json();
  return json.data as LearningAnalysis;
}

async function runLearning(hours: number, minConfidence: number) {
  const url = `${API_BASE}/api/v1/flywheel/run?hours=${hours}&min_confidence=${minConfidence}`;
  const res = await authedFetch(url, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '触发自动学习失败');
  }
  const json = await res.json();
  return json.data as { task_id: string; status: string };
}

async function retryTask(taskId: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/tasks/${taskId}/retry`, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '重跑任务失败');
  }
  const json = await res.json();
  return json.data as TaskItem;
}

const statusStyles: Record<string, string> = {
  pending: 'bg-yellow-50 text-yellow-700 hover:bg-yellow-50',
  running: 'bg-blue-50 text-blue-700 hover:bg-blue-50',
  succeeded: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-50',
  failed: 'bg-red-50 text-red-700 hover:bg-red-50',
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [learning, setLearning] = useState<LearningAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [retryingTaskId, setRetryingTaskId] = useState<string | null>(null);
  const [gapStatus, setGapStatus] = useState('pending');
  const [hours, setHours] = useState(24);
  const [minConfidence, setMinConfidence] = useState(0.45);

  const load = async () => {
    setLoading(true);
    try {
      const [taskItems, learningData] = await Promise.all([fetchTasks(), fetchLearning(gapStatus)]);
      setTasks(taskItems);
      setLearning(learningData);
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [gapStatus]);

  const taskSummary = useMemo(() => {
    const autoLearning = tasks.filter((task) => task.task_type === 'auto_learning').length;
    const failed = tasks.filter((task) => task.status === 'failed').length;
    const runningCount = tasks.filter((task) => task.status === 'running' || task.status === 'pending').length;
    return { autoLearning, failed, runningCount };
  }, [tasks]);

  return (
    <div className="space-y-6 text-slate-900">
      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-950">
              <BrainCircuit size={18} /> 自动学习入口
            </CardTitle>
            <CardDescription className="text-slate-600">
              基于低置信度问答和用户反馈，自动分析知识缺口并生成学习任务。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs text-slate-500">待处理缺口</div>
                <div className="mt-2 text-2xl font-semibold text-slate-950">{learning?.total_gaps ?? 0}</div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs text-slate-500">自动学习任务</div>
                <div className="mt-2 text-2xl font-semibold text-slate-950">{taskSummary.autoLearning}</div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs text-slate-500">执行中 / 失败</div>
                <div className="mt-2 text-2xl font-semibold text-slate-950">{taskSummary.runningCount} / {taskSummary.failed}</div>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
              <Input type="number" min={1} max={168} value={hours} onChange={(e) => setHours(Number(e.target.value) || 24)} placeholder="分析小时数" />
              <Input type="number" min={0} max={1} step={0.05} value={minConfidence} onChange={(e) => setMinConfidence(Number(e.target.value) || 0.45)} placeholder="最低置信度" />
              <Button
                disabled={running}
                onClick={async () => {
                  try {
                    setRunning(true);
                    await runLearning(hours, minConfidence);
                    await load();
                  } catch (error) {
                    alert(error instanceof Error ? error.message : '触发失败');
                  } finally {
                    setRunning(false);
                  }
                }}
              >
                <Play size={16} /> {running ? '触发中...' : '触发学习'}
              </Button>
            </div>

            <div className="flex flex-wrap gap-2">
              {['pending', 'approved', 'rejected'].map((status) => (
                <Button key={status} size="sm" variant={gapStatus === status ? 'default' : 'outline'} onClick={() => setGapStatus(status)}>
                  {reviewStatusLabel(status)}
                </Button>
              ))}
              <Button size="sm" variant="outline" onClick={() => void load()} disabled={loading}>
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> 刷新
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-950">
              <Sparkles size={18} /> 知识缺口建议
            </CardTitle>
            <CardDescription className="text-slate-600">系统会把相似问题聚类，并给出可沉淀的知识草稿方向。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {!learning || learning.insights.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                暂无缺口建议。可以先通过问答助手提出知识库无法回答的问题。
              </div>
            ) : (
              learning.insights.map((insight) => (
                <div key={insight.topic} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="font-medium text-slate-950">{insight.suggested_title || insight.topic}</div>
                      <div className="mt-1 text-xs text-slate-500">主题：{issueTypeLabel(insight.topic)}</div>
                    </div>
                    <Badge className="bg-blue-50 text-blue-700 hover:bg-blue-50">命中 {insight.count}</Badge>
                  </div>
                  <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-700">{insight.suggested_content}</p>
                  {insight.sample_questions.length > 0 ? (
                    <div className="mt-3 rounded-lg bg-white p-3 text-xs text-slate-500">
                      示例问题：{insight.sample_questions.slice(0, 2).join(' / ')}
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>

      <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
        <CardHeader className="border-b border-slate-100 pb-4">
          <CardTitle className="flex items-center gap-2 text-base text-slate-950">
            <ListChecks size={18} /> 任务监控
          </CardTitle>
          <CardDescription className="text-slate-600">查看文档解析、自动学习、批处理等任务的执行状态。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => void load()} disabled={loading} variant="outline">
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
            </Button>
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-700">
              当前共 {tasks.length} 个任务
            </div>
          </div>

          <div className="grid gap-4">
            {tasks.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">暂无任务</div>
            ) : (
              tasks.map((task) => (
                <div key={task.task_id} className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="font-medium text-slate-950">{taskTypeLabel(task.task_type)}</div>
                      <div className="mt-1 text-xs text-slate-500">{task.task_id}</div>
                    </div>
                    <Badge className={statusStyles[task.status] ?? 'bg-slate-100 text-slate-700 hover:bg-slate-100'}>{taskStatusLabel(task.status)}</Badge>
                  </div>
                  <div className="grid gap-2 text-sm text-slate-600 md:grid-cols-4">
                    <div>关联文档：{task.related_document_id ?? '-'}</div>
                    <div>重试次数：{task.retry_count}</div>
                    <div>创建时间：{task.created_at ?? '-'}</div>
                    <div>更新时间：{task.updated_at ?? '-'}</div>
                  </div>
                  {task.error_message ? (
                    <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">错误：{task.error_message}</div>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    {task.status === 'failed' ? (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={retryingTaskId === task.task_id}
                        onClick={async () => {
                          try {
                            setRetryingTaskId(task.task_id);
                            await retryTask(task.task_id);
                            await load();
                          } catch (error) {
                            alert(error instanceof Error ? error.message : '重跑失败');
                          } finally {
                            setRetryingTaskId(null);
                          }
                        }}
                      >
                        <RotateCcw size={14} className={retryingTaskId === task.task_id ? 'animate-spin' : ''} />
                        {retryingTaskId === task.task_id ? '重跑中...' : '重跑任务'}
                      </Button>
                    ) : null}
                    {task.related_document_id ? (
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/documents/${task.related_document_id}`}>
                          <ArrowRight size={14} /> 查看文档
                        </Link>
                      </Button>
                    ) : null}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
