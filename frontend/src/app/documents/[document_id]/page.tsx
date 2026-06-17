'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RefreshCw, FileText, ListChecks, ShieldCheck, PencilLine, ArrowRight, ArrowLeft } from 'lucide-react';
import { knowledgeSpaceLabel, knowledgeTypeLabel, metadataStatusLabel, parseStatusLabel, publishStatusLabel, sourceTypeLabel, taskStatusLabel, taskTypeLabel, visibilityLabel } from '@/lib/display-labels';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type ChunkItem = {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  page_start?: number | null;
  page_end?: number | null;
  source_file_name?: string | null;
};

type DocumentDetail = {
  document_id: string;
  owner_user_id?: string | null;
  effective_knowledge_space?: string | null;
  public_ref_id?: string | null;
  public_ref_status?: string | null;
  public_ref_category?: string | null;
  file_name: string;
  file_type: string;
  file_size: number;
  parse_status: string;
  visibility: string;
  knowledge_space?: string;
  publish_status?: string;
  storage_path: string;
  checksum: string;
  content_text?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  chunks: ChunkItem[];
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
};

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

function getToken() {
  return typeof window !== 'undefined' ? localStorage.getItem('kb_token') : null;
}

function getCurrentUserRoles() {
  try {
    const raw = typeof window !== 'undefined' ? localStorage.getItem('kb_user') : null;
    const roles = raw ? (JSON.parse(raw) as { roles?: string[] }).roles : null;
    return Array.isArray(roles) ? roles : [];
  } catch {
    return [];
  }
}

async function authedFetch(url: string, init?: RequestInit) {
  const token = getToken();
  const headers = new Headers(init?.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...init, headers });
}

async function fetchDocument(documentId: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/documents/${documentId}`);
  if (!res.ok) throw new Error('加载文档详情失败');
  const json = await res.json();
  return json.data as DocumentDetail;
}

function effectiveKnowledgeSpace(doc: DocumentDetail) {
  return doc.effective_knowledge_space || doc.knowledge_space || 'public';
}

async function fetchTasks(documentId: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/tasks?related_document_id=${encodeURIComponent(documentId)}`);
  if (!res.ok) throw new Error('加载任务状态失败');
  const json = await res.json();
  return json.data as TaskItem[];
}

async function fetchMetadata(documentId: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/knowledge-metadata`);
  if (!res.ok) throw new Error('加载知识元数据失败');
  const json = await res.json();
  const items = json.data as KnowledgeMetadata[];
  return items.filter((item) => item.document_id === documentId);
}

export default function DocumentDetailPage({ params }: { params: Promise<{ document_id: string }> }) {
  const searchParams = useSearchParams();
  const highlight = searchParams.get('highlight')?.toLowerCase() ?? '';
  const currentUserRoles = getCurrentUserRoles();
  const isAdminUser = currentUserRoles.includes('admin') || currentUserRoles.includes('reviewer');
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [metadata, setMetadata] = useState<KnowledgeMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [rawText, setRawText] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      const resolved = await params;
      setLoading(true);
      try {
        const [item, taskItems, metadataItems] = await Promise.all([
          fetchDocument(resolved.document_id),
          fetchTasks(resolved.document_id),
          fetchMetadata(resolved.document_id),
        ]);
        if (mounted) {
          setDetail(item);
          setTasks(taskItems);
          setMetadata(metadataItems);
        }
      } catch (error) {
        alert(error instanceof Error ? error.message : '加载失败');
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [params]);

  useEffect(() => {
    if (!detail || detail.file_type.toLowerCase() !== 'pdf') {
      setPdfUrl(null);
      return;
    }

    let objectUrl: string | null = null;
    let cancelled = false;
    (async () => {
      try {
        const res = await authedFetch(`${API_BASE}/api/v1/documents/${detail.document_id}/raw`);
        if (!res.ok) throw new Error('PDF raw file is not available');
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPdfUrl(objectUrl);
      } catch {
        if (!cancelled) setPdfUrl(null);
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [detail]);

  useEffect(() => {
    if (!detail || detail.file_type.toLowerCase() !== 'csv') {
      setRawText(null);
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const res = await authedFetch(`${API_BASE}/api/v1/documents/${detail.document_id}/raw`);
        if (!res.ok) throw new Error('CSV raw file is not available');
        const text = await res.text();
        if (!cancelled) setRawText(text);
      } catch {
        if (!cancelled) setRawText(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [detail]);

  const renderHighlighted = (text: string) => {
    if (!highlight || !text) return text;
    const lower = text.toLowerCase();
    const idx = lower.indexOf(highlight);
    if (idx === -1) return text;
    const before = text.slice(0, idx);
    const match = text.slice(idx, idx + highlight.length);
    const after = text.slice(idx + highlight.length);
    return (
      <>
        {before}
        <mark className="rounded bg-yellow-200 px-1 text-slate-950">{match}</mark>
        {after}
      </>
    );
  };

  const renderInlineMarkdown = (text: string) => {
    return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index} className="font-semibold text-slate-950">{part.slice(2, -2)}</strong>;
      }
      return <span key={index}>{renderHighlighted(part)}</span>;
    });
  };

  const renderMarkdownPreview = (text: string) => {
    const nodes: ReactNode[] = [];
    let listItems: ReactNode[] = [];
    const flushList = () => {
      if (listItems.length) {
        nodes.push(<ul key={`ul-${nodes.length}`} className="my-2 list-disc space-y-1 pl-5">{listItems}</ul>);
        listItems = [];
      }
    };

    text.split('\n').forEach((raw, index) => {
      const line = raw.trimEnd();
      if (!line.trim()) {
        flushList();
        nodes.push(<div key={`br-${index}`} className="h-2" />);
        return;
      }
      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        flushList();
        const size = heading[1].length === 1 ? 'text-xl' : heading[1].length === 2 ? 'text-lg' : 'text-base';
        nodes.push(<div key={`h-${index}`} className={`${size} mt-3 font-semibold text-slate-950`}>{renderInlineMarkdown(heading[2])}</div>);
        return;
      }
      const bullet = line.match(/^[-*]\s+(.+)$/);
      const ordered = line.match(/^\d+[.)]\s+(.+)$/);
      if (bullet || ordered) {
        listItems.push(<li key={`li-${index}`}>{renderInlineMarkdown((bullet || ordered)?.[1] || line)}</li>);
        return;
      }
      flushList();
      nodes.push(<p key={`p-${index}`} className="my-1 leading-7">{renderInlineMarkdown(line)}</p>);
    });
    flushList();
    return nodes;
  };

  const parseCsv = (text: string) => {
    const rows: string[][] = [];
    let row: string[] = [];
    let cell = '';
    let inQuotes = false;

    for (let i = 0; i < text.length; i += 1) {
      const char = text[i];
      const next = text[i + 1];
      if (char === '"') {
        if (inQuotes && next === '"') {
          cell += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
        continue;
      }
      if (char === ',' && !inQuotes) {
        row.push(cell.trim());
        cell = '';
        continue;
      }
      if ((char === '\n' || char === '\r') && !inQuotes) {
        if (char === '\r' && next === '\n') i += 1;
        row.push(cell.trim());
        if (row.some((value) => value)) rows.push(row);
        row = [];
        cell = '';
        continue;
      }
      cell += char;
    }

    row.push(cell.trim());
    if (row.some((value) => value)) rows.push(row);
    return rows;
  };

  const tableRowsFromParsedText = (text: string) => {
    return text
      .split('\n')
      .map((line) => line.split(' | ').map((cell) => cell.trim()))
      .filter((row) => row.some((value) => value));
  };

  const renderTablePreview = (rows: string[][]) => {
    if (!rows.length) {
      return (
        <div className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 text-sm text-[color:var(--muted)]">
          暂无可展示的表格内容。
        </div>
      );
    }
    const [header, ...body] = rows;
    return (
      <div className="max-h-[32rem] overflow-auto rounded-2xl border border-[color:var(--border)] bg-white/80">
        <table className="min-w-full border-collapse text-left text-sm text-[color:var(--text)]">
          <thead className="sticky top-0 bg-slate-100 text-xs uppercase tracking-wide text-slate-600">
            <tr>
              {header.map((cell, index) => (
                <th key={`${cell}-${index}`} className="border-b border-slate-200 px-4 py-3 font-semibold">
                  {renderHighlighted(cell || `列 ${index + 1}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, rowIndex) => (
              <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                {header.map((_, cellIndex) => (
                  <td key={cellIndex} className="border-b border-slate-100 px-4 py-3 align-top">
                    {renderHighlighted(row[cellIndex] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderFullPreview = (doc: DocumentDetail) => {
    const content = doc.content_text || '暂无内容';
    const fileType = doc.file_type.toLowerCase();
    if (fileType === 'md') {
      return (
        <div className="max-h-[28rem] overflow-auto rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 text-sm text-[color:var(--text)]">
          {renderMarkdownPreview(content)}
        </div>
      );
    }
    if (fileType === 'csv') {
      const rows = rawText ? parseCsv(rawText) : tableRowsFromParsedText(content);
      return renderTablePreview(rows);
    }
    if (fileType === 'pdf') {
      if (pdfUrl) {
        return (
          <iframe
            title={doc.file_name}
            src={pdfUrl}
            className="h-[32rem] w-full rounded-2xl border border-[color:var(--border)] bg-white"
          />
        );
      }
      return (
        <div className="space-y-3">
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            PDF 原文件暂不可直接预览，下面展示系统解析后的文本内容。
          </div>
          <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 text-sm leading-6 text-[color:var(--text)]">
            {renderHighlighted(content)}
          </pre>
        </div>
      );
    }
    return (
      <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 text-sm leading-6 text-[color:var(--text)]">
        {renderHighlighted(content)}
      </pre>
    );
  };

  return (
    <div className="space-y-6">
      <Button asChild variant="outline" size="sm">
        <Link href="/documents">
          <ArrowLeft size={14} /> 返回知识库
        </Link>
      </Button>

      <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[color:var(--text)]"><FileText size={18} /> 文档详情</CardTitle>
          <CardDescription className="text-[color:var(--muted)]">查看文档元信息、全文、chunk 列表与任务状态。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 text-sm text-[color:var(--muted)]">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            {loading ? '加载中...' : '已加载'}
          </div>
        </CardContent>
      </Card>

      {detail && (
        <>
          <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
            <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
              <CardHeader>
                <CardTitle className="text-[color:var(--text)]">{detail.file_name}</CardTitle>
                <CardDescription className="text-[color:var(--muted)]">{detail.document_id}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-[color:var(--muted)]">
                <div className="flex flex-wrap gap-2">
                  <Badge>{parseStatusLabel(detail.parse_status)}</Badge>
                  <Badge>{detail.file_type}</Badge>
                  <Badge>{visibilityLabel(detail.visibility)}</Badge>
                  <Badge>{knowledgeSpaceLabel(effectiveKnowledgeSpace(detail))}</Badge>
                  <Badge>{publishStatusLabel(detail.publish_status || 'none')}</Badge>
                </div>
                {detail.public_ref_id && detail.knowledge_space === 'personal' ? (
                  <div className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-3 text-xs text-[color:var(--muted)]">
                    当前通过公有知识引用访问，原始文档仍属于{knowledgeSpaceLabel(detail.knowledge_space)}。
                  </div>
                ) : null}
                <div>大小：{detail.file_size}</div>
                <div>Checksum：{detail.checksum}</div>
                <div>Storage：{detail.storage_path}</div>
                <div>创建：{detail.created_at ?? '-'}</div>
                <div>更新：{detail.updated_at ?? '-'}</div>
                {highlight ? <div className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-3 text-xs text-[color:var(--muted)]">当前高亮关键词：{highlight}</div> : null}
              </CardContent>
            </Card>

            <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-[color:var(--text)]"><ShieldCheck size={18} /> 知识元数据</CardTitle>
                <CardDescription className="text-[color:var(--muted)]">该文档关联的知识治理信息。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {metadata.length === 0 ? (
                  <div className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 text-sm text-[color:var(--muted)]">暂无知识元数据</div>
                ) : (
                  metadata.map((item) => (
                    <div key={item.knowledge_id} className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 space-y-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-sm font-medium text-[color:var(--text)]">{item.title}</div>
                        <Badge>{metadataStatusLabel(item.status)}</Badge>
                      </div>
                      <div className="grid gap-2 text-xs text-[color:var(--muted)] md:grid-cols-2">
                        <div>类型：{knowledgeTypeLabel(item.knowledge_type)}</div>
                        <div>版本：{item.version}</div>
                        <div>来源：{sourceTypeLabel(item.source_type)}</div>
                        <div>作者：{item.author || '-'}</div>
                      </div>
                      <div className="text-xs break-all text-[color:var(--muted)]">ACL：{item.acl_json || '-'}</div>
                      {isAdminUser ? (
                        <div className="flex flex-wrap gap-2">
                          <Button asChild size="sm" variant="outline">
                            <Link href="/admin">
                              <PencilLine size={14} /> 去治理页
                            </Link>
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
            <CardHeader>
              <CardTitle className="text-[color:var(--text)]">处理任务</CardTitle>
              <CardDescription className="text-[color:var(--muted)]">展示该文档关联的解析任务状态。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {tasks.length === 0 ? (
                <div className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 text-sm text-[color:var(--muted)]">暂无任务</div>
              ) : (
                tasks.map((task) => (
                  <div key={task.task_id} className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-medium text-[color:var(--text)]">{taskTypeLabel(task.task_type)}</div>
                      <Badge>{taskStatusLabel(task.status)}</Badge>
                    </div>
                    <div className="mt-2 grid gap-2 text-xs text-[color:var(--muted)] md:grid-cols-2">
                      <div>重试：{task.retry_count}</div>
                      <div>任务ID：{task.task_id}</div>
                      <div>创建：{task.created_at ?? '-'}</div>
                      <div>更新：{task.updated_at ?? '-'}</div>
                    </div>
                    {task.error_message ? <div className="mt-2 rounded-2xl border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-700">{task.error_message}</div> : null}
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
            <CardHeader>
              <CardTitle className="text-[color:var(--text)]">全文预览</CardTitle>
              <CardDescription className="text-[color:var(--muted)]">按文件类型展示预览：txt 保留原文格式，md 渲染 Markdown，csv 展示表格，pdf 优先展示原文件。</CardDescription>
            </CardHeader>
            <CardContent>
              {renderFullPreview(detail)}
            </CardContent>
          </Card>

          <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-[color:var(--text)]"><ListChecks size={18} /> Chunks</CardTitle>
              <CardDescription className="text-[color:var(--muted)]">展示该文档切分后的片段。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {detail.chunks.length === 0 ? (
                <div className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 text-sm text-[color:var(--muted)]">暂无 chunk</div>
              ) : (
                detail.chunks.map((chunk) => {
                  const isHighlighted = Boolean(highlight && chunk.content.toLowerCase().includes(highlight));
                  return (
                    <div
                      key={chunk.chunk_id}
                      id={`chunk-${chunk.chunk_index}`}
                      className={`rounded-2xl border p-4 ${isHighlighted ? 'border-blue-300 bg-blue-50/70' : 'border-[color:var(--border)] bg-white/70'}`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[color:var(--muted)]">
                        <span>Chunk #{chunk.chunk_index}</span>
                        <span>
                          Page {chunk.page_start ?? '-'} - {chunk.page_end ?? '-'}
                        </span>
                      </div>
                      <div className="mt-3 text-sm leading-6 text-[color:var(--text)]">{renderHighlighted(chunk.content)}</div>
                      {isHighlighted ? <div className="mt-3 text-xs text-blue-700">已命中当前搜索关键词</div> : null}
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
