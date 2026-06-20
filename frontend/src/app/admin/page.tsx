'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Bot, CheckCircle2, FileText, ListChecks, PencilLine, PlusCircle, RefreshCw, ShieldCheck, UploadCloud, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { knowledgeTypeLabel, metadataStatusLabel, reviewStatusLabel, riskLevelLabel, sourceTypeLabel, suggestionLabel as displaySuggestionLabel } from '@/lib/display-labels';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type AccessRequest = {
  request_id: string;
  user_id: string;
  document_id: string;
  applicant_name?: string | null;
  applicant_employee_no?: string | null;
  applicant_department?: string | null;
  applicant_permission_level?: number | null;
  document_name?: string | null;
  document_security_level?: string | null;
  document_min_permission_level?: number | null;
  reason: string;
  business_purpose: string;
  expected_duration?: string | null;
  status: 'pending' | 'approved' | 'rejected';
  ai_suggestion?: string | null;
  ai_risk_level?: string | null;
  ai_reason?: string | null;
  reviewed_by?: string | null;
  review_comment?: string | null;
  reviewed_at?: string | null;
  created_at?: string | null;
};

type KnowledgeMetadata = {
  knowledge_id: string;
  document_id: string;
  title: string;
  author?: string | null;
  knowledge_type: string;
  version: string;
  status: string;
  source_type: string;
  acl_json?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type PublishRequest = {
  request_id: string;
  document_id: string;
  requester_id: string;
  requester_name?: string | null;
  requester_employee_no?: string | null;
  document_name?: string | null;
  document_content_preview?: string | null;
  target_category: string;
  allowed_job_categories: string;
  publish_reason: string;
  business_purpose: string;
  status: 'pending' | 'approved' | 'rejected';
  reviewed_by?: string | null;
  review_comment?: string | null;
  reviewed_at?: string | null;
  created_at?: string | null;
};

type KnowledgeSuggestion = {
  suggestion_id: string;
  document_id: string;
  document_name?: string | null;
  public_ref_id?: string | null;
  requester_id: string;
  requester_name?: string | null;
  requester_employee_no?: string | null;
  suggestion_type: string;
  question: string;
  suggestion: string;
  business_impact: string;
  status: 'pending' | 'accepted' | 'rejected' | 'need_more_info';
  reviewed_by?: string | null;
  review_comment?: string | null;
  reviewed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type KnowledgeMergeSuggestion = {
  suggestion_id: string;
  source_document_ids: string[];
  source_document_names: string[];
  suggested_title: string;
  suggested_category?: string | null;
  suggested_outline?: string | null;
  suggested_content: string;
  similarity_reason: string;
  generation_method?: 'deepseek' | 'rule_fallback' | string;
  conflict_notes?: string | null;
  source_attributions?: string | null;
  status: 'pending' | 'approved' | 'rejected';
  requester_id?: string | null;
  reviewed_by?: string | null;
  review_comment?: string | null;
  merged_document_id?: string | null;
  reviewed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
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

async function fetchAccessRequests(status: string) {
  const url = new URL(`${API_BASE}/api/v1/admin/access-requests`);
  if (status) url.searchParams.set('status', status);
  const res = await authedFetch(url.toString());
  if (!res.ok) throw new Error(res.status === 403 ? '当前账号无权访问管理员审核页面' : '加载权限申请失败');
  const json = await res.json();
  return (json.data ?? []) as AccessRequest[];
}

async function runAiReview(requestId: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/access-requests/${requestId}/ai-review`, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || 'AI 辅助审核失败');
  }
  return res.json();
}

async function reviewAccessRequest(requestId: string, approve: boolean, reviewComment: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/access-requests/${requestId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approve, review_comment: reviewComment || null }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '提交审核结果失败');
  }
  return res.json();
}

async function fetchPublishRequests(status: string) {
  const url = new URL(`${API_BASE}/api/v1/admin/publish-requests`);
  if (status) url.searchParams.set('status', status);
  const res = await authedFetch(url.toString());
  if (!res.ok) throw new Error(res.status === 403 ? '当前账号无权访问发布审核' : '加载发布申请失败');
  const json = await res.json();
  return (json.data ?? []) as PublishRequest[];
}

async function reviewPublishRequest(requestId: string, approve: boolean, reviewComment: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/publish-requests/${requestId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approve, review_comment: reviewComment || null }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '提交发布审核失败');
  }
  return res.json();
}

async function fetchKnowledgeSuggestions(status: string) {
  const url = new URL(`${API_BASE}/api/v1/admin/knowledge-suggestions`);
  if (status) url.searchParams.set('status', status);
  const res = await authedFetch(url.toString());
  if (!res.ok) throw new Error(res.status === 403 ? '当前账号无权访问公有知识建议' : '加载公有知识建议失败');
  const json = await res.json();
  return (json.data ?? []) as KnowledgeSuggestion[];
}

async function reviewKnowledgeSuggestion(suggestionId: string, status: 'accepted' | 'rejected' | 'need_more_info', reviewComment: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/knowledge-suggestions/${suggestionId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, review_comment: reviewComment }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '处理公有知识建议失败');
  }
  return res.json();
}

async function scanKnowledgeMergeSuggestions() {
  const res = await authedFetch(`${API_BASE}/api/v1/knowledge/merge-suggestions/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ min_score: 0.3 }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '扫描相似知识失败');
  }
  return res.json();
}

async function fetchKnowledgeMergeSuggestions(status: string) {
  const url = new URL(`${API_BASE}/api/v1/admin/knowledge-merge-suggestions`);
  if (status) url.searchParams.set('status', status);
  const res = await authedFetch(url.toString());
  if (!res.ok) throw new Error(res.status === 403 ? '当前账号无权访问知识整合建议' : '加载知识整合建议失败');
  const json = await res.json();
  return (json.data ?? []) as KnowledgeMergeSuggestion[];
}

async function reviewKnowledgeMergeSuggestion(suggestionId: string, approve: boolean, reviewComment: string, archiveSources = false) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/knowledge-merge-suggestions/${suggestionId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approve, review_comment: reviewComment || null, archive_sources: archiveSources }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '处理知识整合建议失败');
  }
  return res.json();
}

async function fetchMetadata(status?: string, documentId?: string) {
  const url = new URL(`${API_BASE}/api/v1/admin/knowledge-metadata`);
  if (status) url.searchParams.set('status', status);
  if (documentId) url.searchParams.set('document_id', documentId);
  const res = await authedFetch(url.toString());
  if (!res.ok) throw new Error('加载知识条目失败');
  const json = await res.json();
  return (json.data ?? []) as KnowledgeMetadata[];
}

async function createMetadata(payload: Partial<KnowledgeMetadata> & { document_id: string; title: string; knowledge_type: string }) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/knowledge-metadata`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '创建失败');
  }
  return res.json();
}

async function updateMetadata(knowledgeId: string, payload: Partial<KnowledgeMetadata>) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/knowledge-metadata/${knowledgeId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '更新失败');
  }
  return res.json();
}

async function reviewMetadata(knowledgeId: string, approve: boolean) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/knowledge-metadata/${knowledgeId}/review?approve=${approve}`, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '审核失败');
  }
  return res.json();
}

async function archiveMetadata(knowledgeId: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/knowledge-metadata/${knowledgeId}/archive`, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '归档失败');
  }
  return res.json();
}

async function deleteMetadata(knowledgeId: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/knowledge-metadata/${knowledgeId}`, { method: 'DELETE' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '删除失败');
  }
  return res.json();
}

function statusLabel(status: string) {
  return reviewStatusLabel(status);
}

function suggestionStatusLabel(status: string) {
  if (status === 'accepted') return '已采纳';
  if (status === 'rejected') return '暂不采纳';
  if (status === 'need_more_info') return '需补充';
  return '待处理';
}

function suggestionTypeLabel(type: string) {
  const labels: Record<string, string> = {
    content_error: '内容错误',
    outdated: '内容过期',
    missing_steps: '缺少步骤',
    unclear: '表述不清',
    other: '其他',
  };
  return labels[type] || type;
}

function suggestionLabel(suggestion?: string | null) {
  return suggestion ? displaySuggestionLabel(suggestion) : '尚未生成';
}

function riskClass(level?: string | null) {
  if (level === 'high') return 'bg-red-50 text-red-700 hover:bg-red-50';
  if (level === 'medium') return 'bg-amber-50 text-amber-700 hover:bg-amber-50';
  if (level === 'low') return 'bg-emerald-50 text-emerald-700 hover:bg-emerald-50';
  return 'bg-slate-100 text-slate-700 hover:bg-slate-100';
}

export default function AdminPage() {
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [requestStatus, setRequestStatus] = useState('pending');
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [requestLoading, setRequestLoading] = useState(false);
  const [aiLoadingId, setAiLoadingId] = useState<string | null>(null);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [reviewComment, setReviewComment] = useState('');
  const [publishRequests, setPublishRequests] = useState<PublishRequest[]>([]);
  const [publishStatus, setPublishStatus] = useState('pending');
  const [selectedPublishId, setSelectedPublishId] = useState<string | null>(null);
  const [publishLoading, setPublishLoading] = useState(false);
  const [publishReviewingId, setPublishReviewingId] = useState<string | null>(null);
  const [publishReviewComment, setPublishReviewComment] = useState('');
  const [knowledgeSuggestions, setKnowledgeSuggestions] = useState<KnowledgeSuggestion[]>([]);
  const [suggestionStatus, setSuggestionStatus] = useState('pending');
  const [selectedSuggestionId, setSelectedSuggestionId] = useState<string | null>(null);
  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const [suggestionReviewingId, setSuggestionReviewingId] = useState<string | null>(null);
  const [suggestionReviewComment, setSuggestionReviewComment] = useState('');
  const [mergeSuggestions, setMergeSuggestions] = useState<KnowledgeMergeSuggestion[]>([]);
  const [mergeStatus, setMergeStatus] = useState('pending');
  const [mergeLoading, setMergeLoading] = useState(false);
  const [mergeReviewingId, setMergeReviewingId] = useState<string | null>(null);
  const [mergeArchiveSources, setMergeArchiveSources] = useState<Record<string, boolean>>({});

  const [items, setItems] = useState<KnowledgeMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  const [documentFilter, setDocumentFilter] = useState('');
  const [draft, setDraft] = useState({ document_id: '', title: '', author: '', knowledge_type: 'policy', version: 'v1.0.0', status: 'reviewing', source_type: 'upload', acl_json: '' });
  const [editingId, setEditingId] = useState<string | null>(null);

  const selectedRequest = useMemo(() => requests.find((item) => item.request_id === selectedRequestId) ?? requests[0] ?? null, [requests, selectedRequestId]);
  const selectedPublishRequest = useMemo(() => publishRequests.find((item) => item.request_id === selectedPublishId) ?? publishRequests[0] ?? null, [publishRequests, selectedPublishId]);
  const selectedSuggestion = useMemo(() => knowledgeSuggestions.find((item) => item.suggestion_id === selectedSuggestionId) ?? knowledgeSuggestions[0] ?? null, [knowledgeSuggestions, selectedSuggestionId]);
  const filtered = useMemo(() => items.filter((item) => !filter || item.status === filter), [items, filter]);

  const loadRequests = async () => {
    setRequestLoading(true);
    try {
      const data = await fetchAccessRequests(requestStatus);
      setRequests(data);
      setSelectedRequestId(data[0]?.request_id ?? null);
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载权限申请失败');
    } finally {
      setRequestLoading(false);
    }
  };

  const loadMetadata = async () => {
    setLoading(true);
    try {
      setItems(await fetchMetadata(filter || undefined, documentFilter || undefined));
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const loadPublishRequests = async () => {
    setPublishLoading(true);
    try {
      const data = await fetchPublishRequests(publishStatus);
      setPublishRequests(data);
      setSelectedPublishId(data[0]?.request_id ?? null);
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载发布申请失败');
    } finally {
      setPublishLoading(false);
    }
  };

  const loadKnowledgeSuggestions = async () => {
    setSuggestionLoading(true);
    try {
      const data = await fetchKnowledgeSuggestions(suggestionStatus);
      setKnowledgeSuggestions(data);
      setSelectedSuggestionId(data[0]?.suggestion_id ?? null);
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载公有知识建议失败');
    } finally {
      setSuggestionLoading(false);
    }
  };

  const loadMergeSuggestions = async () => {
    setMergeLoading(true);
    try {
      setMergeSuggestions(await fetchKnowledgeMergeSuggestions(mergeStatus));
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载知识整合建议失败');
    } finally {
      setMergeLoading(false);
    }
  };

  useEffect(() => { void loadRequests(); }, [requestStatus]);
  useEffect(() => { void loadPublishRequests(); }, [publishStatus]);
  useEffect(() => { void loadKnowledgeSuggestions(); }, [suggestionStatus]);
  useEffect(() => { void loadMergeSuggestions(); }, [mergeStatus]);
  useEffect(() => { void loadMetadata(); }, [filter, documentFilter]);

  return (
    <div className="space-y-6">
      <section>
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><Bot size={16} /> 知识整合 Agent</CardTitle>
            <CardDescription className="text-slate-700">扫描相似知识文档，生成可审核的整合建议；通过后会创建新的整合知识文档，原始文档不会被删除。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="flex flex-wrap gap-2">
              {['pending', 'approved', 'rejected'].map((item) => (
                <Button key={item} size="sm" variant={mergeStatus === item ? 'default' : 'outline'} onClick={() => setMergeStatus(item)}>
                  {statusLabel(item)}
                </Button>
              ))}
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  try {
                    setMergeLoading(true);
                    await scanKnowledgeMergeSuggestions();
                    await loadMergeSuggestions();
                  } catch (error) {
                    alert(error instanceof Error ? error.message : '扫描相似知识失败');
                  } finally {
                    setMergeLoading(false);
                  }
                }}
                disabled={mergeLoading}
              >
                <RefreshCw size={14} className={mergeLoading ? 'animate-spin' : ''} /> 扫描相似知识
              </Button>
            </div>

            {mergeSuggestions.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">当前状态下暂无知识整合建议。</div>
            ) : (
              <div className="grid gap-3 xl:grid-cols-2">
                {mergeSuggestions.map((item) => (
                  <div key={item.suggestion_id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <div className="text-sm font-medium text-slate-950">{item.suggested_title}</div>
                        <div className="mt-1 text-xs text-slate-600">{item.suggested_category || '整合知识'}</div>
                      </div>
                      <Badge className="bg-white text-slate-700 hover:bg-white">{statusLabel(item.status)}</Badge>
                    </div>
                    <div className="mt-3 rounded-lg bg-white p-3 text-xs leading-5 text-slate-700">
                      <div className="font-medium text-slate-900">相似原因</div>
                      <div className="mt-1">{item.similarity_reason}</div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      <Badge className={item.generation_method === 'deepseek' ? 'bg-blue-50 text-blue-700 hover:bg-blue-50' : 'bg-amber-50 text-amber-700 hover:bg-amber-50'}>
                        {item.generation_method === 'deepseek' ? 'DeepSeek 智能整合' : '规则降级草稿'}
                      </Badge>
                    </div>
                    <details className="mt-3 rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-700">
                      <summary className="cursor-pointer font-medium text-slate-900">查看整合草稿与来源标注</summary>
                      {item.suggested_outline ? <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-slate-50 p-3">{item.suggested_outline}</pre> : null}
                      <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 leading-5">{item.suggested_content}</pre>
                      {item.source_attributions ? <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-blue-50 p-3 text-blue-900">来源标注：{item.source_attributions}</pre> : null}
                    </details>
                    {item.conflict_notes ? (
                      <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
                        <div className="font-medium">冲突与待确认事项</div>
                        <div className="mt-1 whitespace-pre-wrap">{item.conflict_notes}</div>
                      </div>
                    ) : null}
                    <div className="mt-3 text-xs text-slate-600">
                      <span className="font-medium text-slate-900">来源文档：</span>
                      {(item.source_document_names?.length ? item.source_document_names : item.source_document_ids).join('、')}
                    </div>
                    {item.merged_document_id ? (
                      <div className="mt-2 text-xs text-emerald-700">已生成整合文档：{item.merged_document_id}</div>
                    ) : null}
                    {item.status === 'pending' ? (
                      <div className="mt-3 space-y-3">
                        <label className="flex items-center gap-2 text-xs text-slate-700">
                          <input
                            type="checkbox"
                            checked={Boolean(mergeArchiveSources[item.suggestion_id])}
                            onChange={(event) => setMergeArchiveSources((current) => ({ ...current, [item.suggestion_id]: event.target.checked }))}
                          />
                          同时归档来源文档（原文件保留，仅退出检索）
                        </label>
                        <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          disabled={mergeReviewingId === item.suggestion_id}
                          onClick={async () => {
                            try {
                              setMergeReviewingId(item.suggestion_id);
                              await reviewKnowledgeMergeSuggestion(item.suggestion_id, true, '确认整合相似知识', Boolean(mergeArchiveSources[item.suggestion_id]));
                              await loadMergeSuggestions();
                            } catch (error) {
                              alert(error instanceof Error ? error.message : '通过整合建议失败');
                            } finally {
                              setMergeReviewingId(null);
                            }
                          }}
                        >
                          通过并生成整合文档
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={mergeReviewingId === item.suggestion_id}
                          onClick={async () => {
                            try {
                              setMergeReviewingId(item.suggestion_id);
                              await reviewKnowledgeMergeSuggestion(item.suggestion_id, false, '暂不整合');
                              await loadMergeSuggestions();
                            } catch (error) {
                              alert(error instanceof Error ? error.message : '拒绝整合建议失败');
                            } finally {
                              setMergeReviewingId(null);
                            }
                          }}
                        >
                          拒绝
                        </Button>
                        </div>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><ShieldCheck size={16} /> 权限申请审核</CardTitle>
            <CardDescription className="text-slate-700">AI 只提供建议，管理员需要手动选择通过或拒绝。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="flex flex-wrap gap-2">
              {['pending', 'approved', 'rejected'].map((item) => (
                <Button key={item} size="sm" variant={requestStatus === item ? 'default' : 'outline'} onClick={() => setRequestStatus(item)}>
                  {statusLabel(item)}
                </Button>
              ))}
              <Button variant="outline" size="sm" onClick={() => void loadRequests()} disabled={requestLoading}>
                <RefreshCw size={14} className={requestLoading ? 'animate-spin' : ''} /> 刷新
              </Button>
            </div>

            {requests.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">当前状态下暂无申请。</div>
            ) : (
              <div className="space-y-3">
                {requests.map((item) => (
                  <button
                    key={item.request_id}
                    type="button"
                    onClick={() => {
                      setSelectedRequestId(item.request_id);
                      setReviewComment(item.review_comment || '');
                    }}
                    className={`w-full rounded-xl border p-4 text-left transition ${selectedRequest?.request_id === item.request_id ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-slate-50 hover:bg-slate-100'}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-slate-950">{item.document_name || item.document_id}</div>
                        <div className="mt-1 text-xs text-slate-600">{item.applicant_name || item.user_id} · {item.applicant_employee_no || '-'}</div>
                      </div>
                      <Badge className="bg-white text-slate-700 hover:bg-white">{statusLabel(item.status)}</Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                      <span>部门：{item.applicant_department || '-'}</span>
                      <span>用户等级：L{item.applicant_permission_level ?? '-'}</span>
                      <span>文档等级：L{item.document_min_permission_level ?? '-'}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><FileText size={16} /> 申请详情</CardTitle>
            <CardDescription className="text-slate-700">查看申请人与文档信息，生成 AI 建议后再人工审核。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {selectedRequest ? (
              <>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">申请人：{selectedRequest.applicant_name || '-'}（{selectedRequest.applicant_employee_no || '-'}）</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">部门：{selectedRequest.applicant_department || '-'}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">用户等级：L{selectedRequest.applicant_permission_level ?? '-'}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">状态：{statusLabel(selectedRequest.status)}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700 md:col-span-2">文档：{selectedRequest.document_name || selectedRequest.document_id}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">安全等级：{selectedRequest.document_security_level || '-'}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">文档要求：L{selectedRequest.document_min_permission_level ?? '-'}</div>
                </div>

                <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
                  <div>
                    <div className="text-xs font-medium text-slate-500">申请原因</div>
                    <p className="mt-1 text-sm leading-7 text-slate-900">{selectedRequest.reason}</p>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-slate-500">业务用途</div>
                    <p className="mt-1 text-sm leading-7 text-slate-900">{selectedRequest.business_purpose}</p>
                  </div>
                  <div className="text-sm text-slate-700">预计使用时长：{selectedRequest.expected_duration || '-'}</div>
                </div>

                <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-slate-950"><Bot size={16} /> AI 辅助审核</div>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={aiLoadingId === selectedRequest.request_id}
                      onClick={async () => {
                        try {
                          setAiLoadingId(selectedRequest.request_id);
                          await runAiReview(selectedRequest.request_id);
                          await loadRequests();
                        } catch (error) {
                          alert(error instanceof Error ? error.message : 'AI 辅助审核失败');
                        } finally {
                          setAiLoadingId(null);
                        }
                      }}
                    >
                      {aiLoadingId === selectedRequest.request_id ? '生成中...' : '生成 / 更新建议'}
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge className="bg-white text-slate-700 hover:bg-white">{suggestionLabel(selectedRequest.ai_suggestion)}</Badge>
                    <Badge className={riskClass(selectedRequest.ai_risk_level)}>风险：{riskLevelLabel(selectedRequest.ai_risk_level)}</Badge>
                  </div>
                  <p className="text-sm leading-7 text-slate-700">{selectedRequest.ai_reason || '尚未生成 AI 建议。DeepSeek 不可用时，系统会使用规则 fallback 生成建议。'}</p>
                </div>

                <div className="space-y-3">
                  <Textarea value={reviewComment} onChange={(event) => setReviewComment(event.target.value)} placeholder="填写审核意见，例如：通过原因或拒绝原因" className="bg-white text-slate-900 placeholder:text-slate-400" />
                  <div className="flex flex-wrap gap-2">
                    <Button asChild variant="outline">
                      <Link href={`/documents/${selectedRequest.document_id}`}>
                        <ArrowRight size={14} /> 查看文档
                      </Link>
                    </Button>
                    <Button
                      disabled={selectedRequest.status !== 'pending' || reviewingId === selectedRequest.request_id}
                      onClick={async () => {
                        try {
                          setReviewingId(selectedRequest.request_id);
                          await reviewAccessRequest(selectedRequest.request_id, true, reviewComment);
                          await loadRequests();
                        } catch (error) {
                          alert(error instanceof Error ? error.message : '通过失败');
                        } finally {
                          setReviewingId(null);
                        }
                      }}
                    >
                      <CheckCircle2 size={14} /> 通过
                    </Button>
                    <Button
                      variant="destructive"
                      disabled={selectedRequest.status !== 'pending' || reviewingId === selectedRequest.request_id}
                      onClick={async () => {
                        try {
                          setReviewingId(selectedRequest.request_id);
                          await reviewAccessRequest(selectedRequest.request_id, false, reviewComment);
                          await loadRequests();
                        } catch (error) {
                          alert(error instanceof Error ? error.message : '拒绝失败');
                        } finally {
                          setReviewingId(null);
                        }
                      }}
                    >
                      <XCircle size={14} /> 拒绝
                    </Button>
                  </div>
                  {selectedRequest.status !== 'pending' && (
                    <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
                      已审核：{selectedRequest.reviewed_at || '-'}；意见：{selectedRequest.review_comment || '-'}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">请选择左侧申请查看详情。</div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><PencilLine size={16} /> 公有知识建议处理</CardTitle>
            <CardDescription className="text-slate-700">普通员工不能直接修改公有知识，但可以提交问题和修改建议给审核员处理。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="flex flex-wrap gap-2">
              {['pending', 'accepted', 'rejected', 'need_more_info'].map((item) => (
                <Button key={item} size="sm" variant={suggestionStatus === item ? 'default' : 'outline'} onClick={() => setSuggestionStatus(item)}>
                  {suggestionStatusLabel(item)}
                </Button>
              ))}
              <Button variant="outline" size="sm" onClick={() => void loadKnowledgeSuggestions()} disabled={suggestionLoading}>
                <RefreshCw size={14} className={suggestionLoading ? 'animate-spin' : ''} /> 刷新
              </Button>
            </div>
            {knowledgeSuggestions.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">当前状态下暂无公有知识建议。</div>
            ) : (
              <div className="space-y-3">
                {knowledgeSuggestions.map((item) => (
                  <button
                    key={item.suggestion_id}
                    type="button"
                    onClick={() => {
                      setSelectedSuggestionId(item.suggestion_id);
                      setSuggestionReviewComment(item.review_comment || '');
                    }}
                    className={`w-full rounded-xl border p-4 text-left transition ${selectedSuggestion?.suggestion_id === item.suggestion_id ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-slate-50 hover:bg-slate-100'}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-slate-950">{item.document_name || item.document_id}</div>
                        <div className="mt-1 text-xs text-slate-600">{item.requester_name || item.requester_id} · {item.requester_employee_no || '-'}</div>
                      </div>
                      <Badge className="bg-white text-slate-700 hover:bg-white">{suggestionStatusLabel(item.status)}</Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                      <span>类型：{suggestionTypeLabel(item.suggestion_type)}</span>
                      <span>提交：{item.created_at || '-'}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><FileText size={16} /> 建议详情</CardTitle>
            <CardDescription className="text-slate-700">审核员只处理建议状态，不会自动修改公有知识正文。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {selectedSuggestion ? (
              <>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">提交人：{selectedSuggestion.requester_name || '-'}（{selectedSuggestion.requester_employee_no || '-'}）</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">状态：{suggestionStatusLabel(selectedSuggestion.status)}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700 md:col-span-2">文档：{selectedSuggestion.document_name || selectedSuggestion.document_id}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">建议类型：{suggestionTypeLabel(selectedSuggestion.suggestion_type)}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">公有引用：{selectedSuggestion.public_ref_id || '-'}</div>
                </div>
                <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
                  <div>
                    <div className="text-xs font-medium text-slate-500">问题描述</div>
                    <p className="mt-1 text-sm leading-7 text-slate-900">{selectedSuggestion.question}</p>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-slate-500">建议修改内容</div>
                    <p className="mt-1 text-sm leading-7 text-slate-900">{selectedSuggestion.suggestion}</p>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-slate-500">业务影响</div>
                    <p className="mt-1 text-sm leading-7 text-slate-900">{selectedSuggestion.business_impact}</p>
                  </div>
                </div>
                <Textarea value={suggestionReviewComment} onChange={(event) => setSuggestionReviewComment(event.target.value)} placeholder="填写处理意见，例如：采纳原因、暂不采纳原因，或需要用户补充什么信息" className="bg-white text-slate-900 placeholder:text-slate-400" />
                <div className="flex flex-wrap gap-2">
                  <Button asChild variant="outline">
                    <Link href={`/documents/${selectedSuggestion.document_id}`}>
                      <ArrowRight size={14} /> 查看文档
                    </Link>
                  </Button>
                  {(['accepted', 'need_more_info', 'rejected'] as const).map((status) => (
                    <Button
                      key={status}
                      variant={status === 'rejected' ? 'destructive' : 'default'}
                      disabled={selectedSuggestion.status !== 'pending' || suggestionReviewingId === selectedSuggestion.suggestion_id || !suggestionReviewComment.trim()}
                      onClick={async () => {
                        try {
                          setSuggestionReviewingId(selectedSuggestion.suggestion_id);
                          await reviewKnowledgeSuggestion(selectedSuggestion.suggestion_id, status, suggestionReviewComment.trim());
                          await loadKnowledgeSuggestions();
                        } catch (error) {
                          alert(error instanceof Error ? error.message : '处理公有知识建议失败');
                        } finally {
                          setSuggestionReviewingId(null);
                        }
                      }}
                    >
                      {suggestionStatusLabel(status)}
                    </Button>
                  ))}
                </div>
                {selectedSuggestion.status !== 'pending' && (
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
                    已处理：{selectedSuggestion.reviewed_at || '-'}；意见：{selectedSuggestion.review_comment || '-'}
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">请选择左侧建议查看详情。</div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><UploadCloud size={16} /> 公有知识发布审核</CardTitle>
            <CardDescription className="text-slate-700">个人知识只有审核通过后才会转入公有知识库，并进入公共检索范围。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="flex flex-wrap gap-2">
              {['pending', 'approved', 'rejected'].map((item) => (
                <Button key={item} size="sm" variant={publishStatus === item ? 'default' : 'outline'} onClick={() => setPublishStatus(item)}>
                  {statusLabel(item)}
                </Button>
              ))}
              <Button variant="outline" size="sm" onClick={() => void loadPublishRequests()} disabled={publishLoading}>
                <RefreshCw size={14} className={publishLoading ? 'animate-spin' : ''} /> 刷新
              </Button>
            </div>
            {publishRequests.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">当前状态下暂无发布申请。</div>
            ) : (
              <div className="space-y-3">
                {publishRequests.map((item) => (
                  <button
                    key={item.request_id}
                    type="button"
                    onClick={() => {
                      setSelectedPublishId(item.request_id);
                      setPublishReviewComment(item.review_comment || '');
                    }}
                    className={`w-full rounded-xl border p-4 text-left transition ${selectedPublishRequest?.request_id === item.request_id ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-slate-50 hover:bg-slate-100'}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-slate-950">{item.document_name || item.document_id}</div>
                        <div className="mt-1 text-xs text-slate-600">{item.requester_name || item.requester_id} · {item.requester_employee_no || '-'}</div>
                      </div>
                      <Badge className="bg-white text-slate-700 hover:bg-white">{statusLabel(item.status)}</Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                      <span>类别：{item.target_category}</span>
                      <span>可访问：{item.allowed_job_categories}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><FileText size={16} /> 发布详情</CardTitle>
            <CardDescription className="text-slate-700">审核通过会把知识空间从个人知识转为公有知识。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {selectedPublishRequest ? (
              <>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">申请人：{selectedPublishRequest.requester_name || '-'}（{selectedPublishRequest.requester_employee_no || '-'}）</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">状态：{statusLabel(selectedPublishRequest.status)}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700 md:col-span-2">文档：{selectedPublishRequest.document_name || selectedPublishRequest.document_id}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">目标类别：{selectedPublishRequest.target_category}</div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">可访问人员：{selectedPublishRequest.allowed_job_categories}</div>
                </div>
                <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
                  <div>
                    <div className="text-xs font-medium text-slate-500">发布理由</div>
                    <p className="mt-1 text-sm leading-7 text-slate-900">{selectedPublishRequest.publish_reason}</p>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-slate-500">业务用途</div>
                    <p className="mt-1 text-sm leading-7 text-slate-900">{selectedPublishRequest.business_purpose}</p>
                  </div>
                </div>
                <Textarea value={publishReviewComment} onChange={(event) => setPublishReviewComment(event.target.value)} placeholder="填写发布审核意见" className="bg-white text-slate-900 placeholder:text-slate-400" />
                <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
                  <div className="text-xs font-medium text-blue-700">发布审核预览</div>
                  <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-900">
                    {selectedPublishRequest.document_content_preview || '该申请当前没有可预览的正文内容。'}
                  </pre>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    disabled={selectedPublishRequest.status !== 'pending' || publishReviewingId === selectedPublishRequest.request_id}
                    onClick={async () => {
                      try {
                        setPublishReviewingId(selectedPublishRequest.request_id);
                        await reviewPublishRequest(selectedPublishRequest.request_id, true, publishReviewComment);
                        await loadPublishRequests();
                      } catch (error) {
                        alert(error instanceof Error ? error.message : '发布通过失败');
                      } finally {
                        setPublishReviewingId(null);
                      }
                    }}
                  >
                    <CheckCircle2 size={14} /> 通过发布
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={selectedPublishRequest.status !== 'pending' || publishReviewingId === selectedPublishRequest.request_id}
                    onClick={async () => {
                      try {
                        setPublishReviewingId(selectedPublishRequest.request_id);
                        await reviewPublishRequest(selectedPublishRequest.request_id, false, publishReviewComment);
                        await loadPublishRequests();
                      } catch (error) {
                        alert(error instanceof Error ? error.message : '发布拒绝失败');
                      } finally {
                        setPublishReviewingId(null);
                      }
                    }}
                  >
                    <XCircle size={14} /> 拒绝发布
                  </Button>
                </div>
                {selectedPublishRequest.status !== 'pending' && (
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
                    已审核：{selectedPublishRequest.reviewed_at || '-'}；意见：{selectedPublishRequest.review_comment || '-'}
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">请选择左侧发布申请查看详情。</div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><PlusCircle size={16} /> 新建或编辑知识条目</CardTitle>
            <CardDescription className="text-slate-700">从已上传文档中整理出结构化知识信息。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            <div className="grid gap-3">
              <Input placeholder="document_id" value={draft.document_id} onChange={(e) => setDraft((c) => ({ ...c, document_id: e.target.value }))} />
              <Input placeholder="标题" value={draft.title} onChange={(e) => setDraft((c) => ({ ...c, title: e.target.value }))} />
              <Input placeholder="作者" value={draft.author} onChange={(e) => setDraft((c) => ({ ...c, author: e.target.value }))} />
              <Input placeholder="知识类型" value={draft.knowledge_type} onChange={(e) => setDraft((c) => ({ ...c, knowledge_type: e.target.value }))} />
              <Input placeholder="版本" value={draft.version} onChange={(e) => setDraft((c) => ({ ...c, version: e.target.value }))} />
              <Input placeholder="来源类型" value={draft.source_type} onChange={(e) => setDraft((c) => ({ ...c, source_type: e.target.value }))} />
              <Textarea placeholder="ACL JSON" value={draft.acl_json} onChange={(e) => setDraft((c) => ({ ...c, acl_json: e.target.value }))} className="bg-white text-slate-900 placeholder:text-slate-400" />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={async () => {
                  try {
                    if (editingId) {
                      await updateMetadata(editingId, { ...draft, author: draft.author || null, acl_json: draft.acl_json || null });
                    } else {
                      await createMetadata({ ...draft, author: draft.author || null, acl_json: draft.acl_json || null });
                    }
                    setEditingId(null);
                    await loadMetadata();
                  } catch (error) {
                    alert(error instanceof Error ? error.message : '保存失败');
                  }
                }}
              >
                {editingId ? '保存' : '创建'}
              </Button>
              <Button variant="outline" onClick={() => { setEditingId(null); setDraft({ document_id: '', title: '', author: '', knowledge_type: 'policy', version: 'v1.0.0', status: 'reviewing', source_type: 'upload', acl_json: '' }); }}>
                重置
              </Button>
              <Button variant="outline" onClick={() => void loadMetadata()} disabled={loading}>
                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><ListChecks size={16} /> 知识条目列表</CardTitle>
            <CardDescription className="text-slate-700">查看、筛选和处理知识条目。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            <div className="grid gap-3 md:grid-cols-[1fr_auto]">
              <Input placeholder="按 document_id 过滤" value={documentFilter} onChange={(e) => setDocumentFilter(e.target.value)} />
              <div className="flex flex-wrap gap-2">
                {['', 'reviewing', 'available', 'disabled'].map((item) => (
                  <Button key={item || 'all'} size="sm" variant={filter === item ? 'default' : 'outline'} onClick={() => setFilter(item)}>
                    {item ? metadataStatusLabel(item) : '全部'}
                  </Button>
                ))}
              </div>
            </div>

            {filtered.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">还没有知识条目。</div>
            ) : (
              filtered.map((item) => (
                <div key={item.knowledge_id} className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="font-medium text-slate-900">{item.title}</div>
                      <div className="text-xs text-slate-500">{item.document_id}</div>
                    </div>
                    <Badge className="bg-white text-slate-700 hover:bg-white">{metadataStatusLabel(item.status)}</Badge>
                  </div>
                  <div className="grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                    <div>类型：{knowledgeTypeLabel(item.knowledge_type)}</div>
                    <div>版本：{item.version}</div>
                    <div>来源：{sourceTypeLabel(item.source_type)}</div>
                    <div>作者：{item.author || '-'}</div>
                  </div>
                  <div className="break-all text-xs text-slate-500">ACL：{item.acl_json || '-'}</div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setEditingId(item.knowledge_id);
                        setDraft({
                          document_id: item.document_id,
                          title: item.title,
                          author: item.author || '',
                          knowledge_type: item.knowledge_type,
                          version: item.version,
                          status: item.status,
                          source_type: item.source_type,
                          acl_json: item.acl_json || '',
                        });
                      }}
                    >
                      <PencilLine size={14} /> 编辑
                    </Button>
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/documents/${item.document_id}`}>
                        <ArrowRight size={14} /> 文档详情
                      </Link>
                    </Button>
                    <Button size="sm" onClick={async () => { try { await reviewMetadata(item.knowledge_id, true); await loadMetadata(); } catch (error) { alert(error instanceof Error ? error.message : '审核失败'); } }}>
                      <ShieldCheck size={14} /> 通过
                    </Button>
                    <Button size="sm" variant="outline" onClick={async () => { try { await archiveMetadata(item.knowledge_id); await loadMetadata(); } catch (error) { alert(error instanceof Error ? error.message : '归档失败'); } }}>
                      归档
                    </Button>
                    <Button size="sm" variant="destructive" onClick={async () => { try { await deleteMetadata(item.knowledge_id); await loadMetadata(); } catch (error) { alert(error instanceof Error ? error.message : '删除失败'); } }}>
                      删除
                    </Button>
                  </div>
                  <div className="text-[11px] text-slate-500">创建：{item.created_at ?? '-'} · 更新：{item.updated_at ?? '-'}</div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
