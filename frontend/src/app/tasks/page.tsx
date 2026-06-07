'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, ListChecks, RotateCcw, ArrowRight } from 'lucide-react';

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

async function fetchTasks() {
  const res = await fetch(`${API_BASE}/api/v1/tasks`);
  if (!res.ok) throw new Error('加载任务列表失败');
  const json = await res.json();
  return json.data as TaskItem[];
}

async function retryTask(taskId: string) {
  const res = await fetch(`${API_BASE}/api/v1/tasks/${taskId}/retry`, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '重跑任务失败');
  }
  const json = await res.json();
  return json.data as TaskItem;
}

const statusStyles: Record<string, string> = {
  pending: 'bg-yellow-500/20 text-yellow-200 border-yellow-500/30',
  running: 'bg-blue-500/20 text-blue-200 border-blue-500/30',
  succeeded: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/30',
  failed: 'bg-red-500/20 text-red-200 border-red-500/30',
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [retryingTaskId, setRetryingTaskId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setTasks(await fetchTasks());
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="space-y-6 text-slate-900">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-900"><ListChecks size={18} /> 任务监控</CardTitle>
          <CardDescription className="text-slate-600">查看文档解析、回流、批处理等任务的执行状态。</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3 text-slate-900">
          <Button onClick={() => void load()} disabled={loading} variant="outline">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
          </Button>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-700">
            当前共 {tasks.length} 个任务
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {tasks.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-sm text-slate-600">暂无任务</CardContent>
          </Card>
        ) : (
          tasks.map((task) => (
            <Card key={task.task_id}>
              <CardContent className="space-y-3 p-6 text-slate-900">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="font-medium text-slate-900">{task.task_type}</div>
                    <div className="mt-1 text-xs text-slate-600">{task.task_id}</div>
                  </div>
                  <Badge className={statusStyles[task.status] ?? 'bg-slate-100 text-slate-700 border-slate-200'}>{task.status}</Badge>
                </div>
                <div className="grid gap-2 text-sm text-slate-700 md:grid-cols-4">
                  <div>关联文档：{task.related_document_id ?? '-'}</div>
                  <div>重试次数：{task.retry_count}</div>
                  <div>创建时间：{task.created_at ?? '-'}</div>
                  <div>更新时间：{task.updated_at ?? '-'}</div>
                </div>
                {task.error_message ? (
                  <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                    错误：{task.error_message}
                  </div>
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
                        <ArrowRight size={14} />
                        查看文档
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
