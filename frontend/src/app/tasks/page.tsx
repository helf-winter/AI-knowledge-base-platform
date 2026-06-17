'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, BrainCircuit, FileText, ListChecks, Play, RefreshCw, RotateCcw, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
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

type LearningGap = {
  gap_id: string;
  query_text: string;
  issue_type: string;
  confidence: number;
  evidence?: string | null;
  normalized_question?: string | null;
  hit_count: number;
  suggested_title?: string | null;
  suggested_content?: string | null;
  draft_document_id?: string | null;
  ai_draft_content?: string | null;
  pending_confirmations?: string | null;
  admin_final_content?: string | null;
  target_category?: string | null;
  allowed_job_categories?: string | null;
  business_purpose?: string | null;
  review_comment?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
};

const statusStyles: Record<string, string> = {
  pending: 'bg-yellow-50 text-yellow-700 hover:bg-yellow-50',
  clustered: 'bg-blue-50 text-blue-700 hover:bg-blue-50',
  drafted: 'bg-purple-50 text-purple-700 hover:bg-purple-50',
  approved: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-50',
  rejected: 'bg-red-50 text-red-700 hover:bg-red-50',
  running: 'bg-blue-50 text-blue-700 hover:bg-blue-50',
  succeeded: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-50',
  failed: 'bg-red-50 text-red-700 hover:bg-red-50',
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

async function fetchLearningGaps(status: string) {
  const query = status === 'all' ? '' : `?status=${encodeURIComponent(status)}`;
  const res = await authedFetch(`${API_BASE}/api/v1/admin/learning-gaps${query}`);
  if (!res.ok) throw new Error('加载知识缺口失败');
  const json = await res.json();
  return json.data as LearningGap[];
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

async function generateDraft(gap: LearningGap, targetCategory: string, allowedJobCategories: string, businessPurpose: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/learning-gaps/${gap.gap_id}/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_category: targetCategory,
      allowed_job_categories: allowedJobCategories,
      business_purpose: businessPurpose,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '生成草稿失败');
  }
  return res.json();
}

async function reviewDraft(gap: LearningGap, approve: boolean, finalContent: string, targetCategory: string, allowedJobCategories: string, reviewComment: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/learning-gaps/${gap.gap_id}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      approve,
      admin_final_content: finalContent || null,
      target_category: targetCategory || null,
      allowed_job_categories: allowedJobCategories || null,
      review_comment: reviewComment || null,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '审核草稿失败');
  }
  return res.json();
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

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [learning, setLearning] = useState<LearningAnalysis | null>(null);
  const [gaps, setGaps] = useState<LearningGap[]>([]);
  const [selectedGapId, setSelectedGapId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [draftingGapId, setDraftingGapId] = useState<string | null>(null);
  const [reviewingGapId, setReviewingGapId] = useState<string | null>(null);
  const [retryingTaskId, setRetryingTaskId] = useState<string | null>(null);
  const [gapStatus, setGapStatus] = useState('pending');
  const [hours, setHours] = useState(24);
  const [minConfidence, setMinConfidence] = useState(0.45);
  const [targetCategory, setTargetCategory] = useState('IT流程');
  const [allowedJobCategories, setAllowedJobCategories] = useState('全公司');
  const [businessPurpose, setBusinessPurpose] = useState('补齐企业知识库缺口，提升后续问答命中率');
  const [finalContent, setFinalContent] = useState('');
  const [reviewComment, setReviewComment] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const [taskItems, learningData, gapItems] = await Promise.all([fetchTasks(), fetchLearning(gapStatus === 'all' ? 'pending' : gapStatus), fetchLearningGaps(gapStatus)]);
      setTasks(taskItems);
      setLearning(learningData);
      setGaps(gapItems);
      if (!selectedGapId && gapItems.length > 0) setSelectedGapId(gapItems[0].gap_id);
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [gapStatus]);

  const selectedGap = useMemo(() => gaps.find((item) => item.gap_id === selectedGapId) ?? gaps[0] ?? null, [gaps, selectedGapId]);

  useEffect(() => {
    if (!selectedGap) return;
    setTargetCategory(selectedGap.target_category || 'IT流程');
    setAllowedJobCategories(selectedGap.allowed_job_categories || '全公司');
    setBusinessPurpose(selectedGap.business_purpose || '补齐企业知识库缺口，提升后续问答命中率');
    setFinalContent(selectedGap.admin_final_content || selectedGap.ai_draft_content || selectedGap.suggested_content || '');
    setReviewComment(selectedGap.review_comment || '');
  }, [selectedGap?.gap_id]);

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
              从低置信度问答和用户反馈中发现知识缺口，生成待审核草稿，管理员确认后再发布为公有知识。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs text-slate-500">当前筛选缺口</div>
                <div className="mt-2 text-2xl font-semibold text-slate-950">{gaps.length}</div>
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
              <Input type="number" min={1} max={168} value={hours} onChange={(event) => setHours(Number(event.target.value) || 24)} placeholder="分析小时数" />
              <Input type="number" min={0} max={1} step={0.05} value={minConfidence} onChange={(event) => setMinConfidence(Number(event.target.value) || 0.45)} placeholder="最低置信度" />
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
              {['pending', 'clustered', 'drafted', 'approved', 'rejected', 'all'].map((status) => (
                <Button key={status} size="sm" variant={gapStatus === status ? 'default' : 'outline'} onClick={() => setGapStatus(status)}>
                  {status === 'all' ? '全部' : reviewStatusLabel(status)}
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
              <Sparkles size={18} /> 自动学习成效
            </CardTitle>
            <CardDescription className="text-slate-600">系统会把相似问题聚合，辅助判断哪些知识值得沉淀。</CardDescription>
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
                      <div className="font-medium text-slate-950">{insight.suggested_title || issueTypeLabel(insight.topic)}</div>
                      <div className="mt-1 text-xs text-slate-500">主题：{issueTypeLabel(insight.topic)}</div>
                    </div>
                    <Badge className="bg-blue-50 text-blue-700 hover:bg-blue-50">命中 {insight.count}</Badge>
                  </div>
                  <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-700">{insight.suggested_content}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_0.95fr]">
        <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-950">
              <FileText size={18} /> 知识缺口列表
            </CardTitle>
            <CardDescription className="text-slate-600">选择一个缺口后，可以生成 AI 草稿并进行管理员定稿。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {gaps.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">当前状态下暂无知识缺口。</div>
            ) : (
              gaps.map((gap) => (
                <button
                  key={gap.gap_id}
                  type="button"
                  onClick={() => setSelectedGapId(gap.gap_id)}
                  className={`w-full rounded-xl border p-4 text-left transition ${selectedGap?.gap_id === gap.gap_id ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-slate-50 hover:bg-slate-100'}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate font-medium text-slate-950">{gap.query_text}</div>
                      <div className="mt-1 text-xs text-slate-500">类型：{issueTypeLabel(gap.issue_type)} · 出现 {gap.hit_count || 1} 次 · 置信度 {Number(gap.confidence || 0).toFixed(2)}</div>
                    </div>
                    <Badge className={statusStyles[gap.status] ?? 'bg-slate-100 text-slate-700 hover:bg-slate-100'}>{reviewStatusLabel(gap.status)}</Badge>
                  </div>
                  {gap.evidence ? <div className="mt-3 line-clamp-2 text-xs text-slate-600">证据：{gap.evidence}</div> : null}
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-950">
              <Sparkles size={18} /> 草稿审核
            </CardTitle>
            <CardDescription className="text-slate-600">AI 只生成草稿，最终内容和发布范围必须由管理员确认。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {!selectedGap ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">请选择左侧知识缺口。</div>
            ) : (
              <>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="text-sm font-medium text-slate-950">{selectedGap.query_text}</div>
                  <div className="mt-2 text-xs text-slate-600">状态：{reviewStatusLabel(selectedGap.status)} · 草稿文档：{selectedGap.draft_document_id || '-'}</div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <Input value={targetCategory} onChange={(event) => setTargetCategory(event.target.value)} placeholder="目标分类，例如 IT流程" />
                  <Input value={allowedJobCategories} onChange={(event) => setAllowedJobCategories(event.target.value)} placeholder="可访问人员，例如 全公司" />
                </div>
                <Textarea value={businessPurpose} onChange={(event) => setBusinessPurpose(event.target.value)} placeholder="业务用途" />

                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    disabled={draftingGapId === selectedGap.gap_id || selectedGap.status === 'approved' || selectedGap.status === 'rejected'}
                    onClick={async () => {
                      try {
                        setDraftingGapId(selectedGap.gap_id);
                        await generateDraft(selectedGap, targetCategory.trim(), allowedJobCategories.trim(), businessPurpose.trim());
                        await load();
                      } catch (error) {
                        alert(error instanceof Error ? error.message : '生成草稿失败');
                      } finally {
                        setDraftingGapId(null);
                      }
                    }}
                  >
                    <Sparkles size={14} /> {draftingGapId === selectedGap.gap_id ? '生成中...' : '生成 AI 草稿'}
                  </Button>
                  {selectedGap.draft_document_id ? (
                    <Button asChild variant="outline">
                      <Link href={`/documents/${selectedGap.draft_document_id}`}>
                        查看草稿文档 <ArrowRight size={14} />
                      </Link>
                    </Button>
                  ) : null}
                </div>

                {selectedGap.pending_confirmations ? (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                    <div className="font-medium">待确认事项</div>
                    <pre className="mt-2 whitespace-pre-wrap font-sans leading-6">{selectedGap.pending_confirmations}</pre>
                  </div>
                ) : null}

                <div>
                  <div className="mb-2 text-sm font-medium text-slate-800">管理员定稿内容</div>
                  <Textarea className="min-h-64 bg-white text-slate-900" value={finalContent} onChange={(event) => setFinalContent(event.target.value)} placeholder="生成草稿后可在这里修改最终发布内容" />
                </div>

                <div>
                  <div className="mb-2 text-sm font-medium text-slate-800">审核意见</div>
                  <Textarea value={reviewComment} onChange={(event) => setReviewComment(event.target.value)} placeholder="记录通过或拒绝的原因" />
                </div>

                <div className="flex flex-wrap justify-end gap-2">
                  <Button
                    variant="outline"
                    disabled={reviewingGapId === selectedGap.gap_id || !selectedGap.draft_document_id || selectedGap.status === 'approved' || selectedGap.status === 'rejected'}
                    onClick={async () => {
                      try {
                        setReviewingGapId(selectedGap.gap_id);
                        await reviewDraft(selectedGap, false, finalContent.trim(), targetCategory.trim(), allowedJobCategories.trim(), reviewComment.trim());
                        await load();
                      } catch (error) {
                        alert(error instanceof Error ? error.message : '拒绝失败');
                      } finally {
                        setReviewingGapId(null);
                      }
                    }}
                  >
                    拒绝
                  </Button>
                  <Button
                    disabled={reviewingGapId === selectedGap.gap_id || !selectedGap.draft_document_id || !finalContent.trim() || selectedGap.status === 'approved' || selectedGap.status === 'rejected'}
                    onClick={async () => {
                      try {
                        setReviewingGapId(selectedGap.gap_id);
                        await reviewDraft(selectedGap, true, finalContent.trim(), targetCategory.trim(), allowedJobCategories.trim(), reviewComment.trim());
                        await load();
                      } catch (error) {
                        alert(error instanceof Error ? error.message : '发布失败');
                      } finally {
                        setReviewingGapId(null);
                      }
                    }}
                  >
                    通过并发布
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </section>

      <Card className="rounded-2xl border-slate-200 bg-white shadow-sm">
        <CardHeader className="border-b border-slate-100 pb-4">
          <CardTitle className="flex items-center gap-2 text-base text-slate-950">
            <ListChecks size={18} /> 任务监控
          </CardTitle>
          <CardDescription className="text-slate-600">查看文档解析、自动学习、批处理等任务状态。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => void load()} disabled={loading} variant="outline">
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
            </Button>
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-700">当前共 {tasks.length} 个任务</div>
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
                  {task.error_message ? <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">错误：{task.error_message}</div> : null}
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
