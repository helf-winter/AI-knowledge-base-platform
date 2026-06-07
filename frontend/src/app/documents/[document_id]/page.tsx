'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RefreshCw, FileText, ListChecks, ShieldCheck, PencilLine, ArrowRight } from 'lucide-react';

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
  file_name: string;
  file_type: string;
  file_size: number;
  parse_status: string;
  visibility: string;
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

async function fetchDocument(documentId: string) {
  const res = await fetch(`${API_BASE}/api/v1/documents/${documentId}`);
  if (!res.ok) throw new Error('加载文档详情失败');
  const json = await res.json();
  return json.data as DocumentDetail;
}

async function fetchTasks(documentId: string) {
  const res = await fetch(`${API_BASE}/api/v1/tasks?related_document_id=${encodeURIComponent(documentId)}`);
  if (!res.ok) throw new Error('加载任务状态失败');
  const json = await res.json();
  return json.data as TaskItem[];
}

async function fetchMetadata(documentId: string) {
  const res = await fetch(`${API_BASE}/api/v1/admin/knowledge-metadata`);
  if (!res.ok) throw new Error('加载知识元数据失败');
  const json = await res.json();
  const items = json.data as KnowledgeMetadata[];
  return items.filter((item) => item.document_id === documentId);
}

export default function DocumentDetailPage({ params }: { params: Promise<{ document_id: string }> }) {
  const searchParams = useSearchParams();
  const highlight = searchParams.get('highlight')?.toLowerCase() ?? '';
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [metadata, setMetadata] = useState<KnowledgeMetadata[]>([]);
  const [loading, setLoading] = useState(false);

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

  return (
    <div className="space-y-6">
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
                  <Badge>{detail.parse_status}</Badge>
                  <Badge>{detail.file_type}</Badge>
                  <Badge>{detail.visibility}</Badge>
                </div>
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
                        <Badge>{item.status}</Badge>
                      </div>
                      <div className="grid gap-2 text-xs text-[color:var(--muted)] md:grid-cols-2">
                        <div>类型：{item.knowledge_type}</div>
                        <div>版本：{item.version}</div>
                        <div>来源：{item.source_type}</div>
                        <div>作者：{item.author || '-'}</div>
                      </div>
                      <div className="text-xs break-all text-[color:var(--muted)]">ACL：{item.acl_json || '-'}</div>
                      <div className="flex flex-wrap gap-2">
                        <Button asChild size="sm" variant="outline">
                          <Link href="/admin">
                            <PencilLine size={14} /> 去治理页
                          </Link>
                        </Button>
                      </div>
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
                      <div className="text-sm font-medium text-[color:var(--text)]">{task.task_type}</div>
                      <Badge>{task.status}</Badge>
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
              <CardDescription className="text-[color:var(--muted)]">展示解析后的文本内容，命中关键词会高亮显示。</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 text-sm leading-6 text-[color:var(--text)]">
                {renderHighlighted(detail.content_text || '暂无内容')}
              </pre>
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
