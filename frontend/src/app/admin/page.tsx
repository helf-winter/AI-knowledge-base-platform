'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ArrowRight, PencilLine, PlusCircle, RefreshCw, ShieldCheck, ListChecks } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

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

async function fetchMetadata(status?: string, documentId?: string) {
  const url = new URL(`${API_BASE}/api/v1/admin/knowledge-metadata`);
  if (status) url.searchParams.set('status', status);
  if (documentId) url.searchParams.set('document_id', documentId);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('加载知识条目失败');
  const json = await res.json();
  return json.data as KnowledgeMetadata[];
}

async function createMetadata(payload: Partial<KnowledgeMetadata> & { document_id: string; title: string; knowledge_type: string }) {
  const res = await fetch(`${API_BASE}/api/v1/admin/knowledge-metadata`, {
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
  const res = await fetch(`${API_BASE}/api/v1/admin/knowledge-metadata/${knowledgeId}`, {
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
  const res = await fetch(`${API_BASE}/api/v1/admin/knowledge-metadata/${knowledgeId}/review?approve=${approve}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '审核失败');
  }
  return res.json();
}

async function archiveMetadata(knowledgeId: string) {
  const res = await fetch(`${API_BASE}/api/v1/admin/knowledge-metadata/${knowledgeId}/archive`, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '归档失败');
  }
  return res.json();
}

async function deleteMetadata(knowledgeId: string) {
  const res = await fetch(`${API_BASE}/api/v1/admin/knowledge-metadata/${knowledgeId}`, { method: 'DELETE' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '删除失败');
  }
  return res.json();
}

export default function AdminPage() {
  const [items, setItems] = useState<KnowledgeMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  const [documentFilter, setDocumentFilter] = useState('');
  const [draft, setDraft] = useState({ document_id: '', title: '', author: '', knowledge_type: 'policy', version: 'v1.0.0', status: 'reviewing', source_type: 'upload', acl_json: '' });
  const [editingId, setEditingId] = useState<string | null>(null);

  const filtered = useMemo(() => items.filter((item) => !filter || item.status === filter), [items, filter]);

  const load = async () => {
    setLoading(true);
    try {
      setItems(await fetchMetadata(filter || undefined, documentFilter || undefined));
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [filter, documentFilter]);

  return (
    <div className="space-y-6">
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
              <Textarea placeholder="ACL JSON" value={draft.acl_json} onChange={(e) => setDraft((c) => ({ ...c, acl_json: e.target.value }))} />
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
                    await load();
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
              <Button variant="outline" onClick={() => void load()} disabled={loading}>
                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-slate-900"><ListChecks size={16} /> 知识条目列表</CardTitle>
            <CardDescription className="text-slate-700">查看、筛选和处理条目。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            <div className="grid gap-3 md:grid-cols-[1fr_auto]">
              <Input placeholder="按 document_id 过滤" value={documentFilter} onChange={(e) => setDocumentFilter(e.target.value)} />
              <div className="flex flex-wrap gap-2">
                {['', 'reviewing', 'available', 'disabled'].map((item) => (
                  <Button key={item || 'all'} size="sm" variant={filter === item ? 'default' : 'outline'} onClick={() => setFilter(item)}>
                    {item || '全部'}
                  </Button>
                ))}
              </div>
            </div>

            {filtered.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                还没有知识条目。
              </div>
            ) : (
              filtered.map((item) => (
                <div key={item.knowledge_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="font-medium text-slate-900">{item.title}</div>
                      <div className="text-xs text-slate-500">{item.document_id}</div>
                    </div>
                    <Badge className="bg-white text-slate-700 hover:bg-white">{item.status}</Badge>
                  </div>
                  <div className="grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                    <div>类型：{item.knowledge_type}</div>
                    <div>版本：{item.version}</div>
                    <div>来源：{item.source_type}</div>
                    <div>作者：{item.author || '-'}</div>
                  </div>
                  <div className="text-xs text-slate-500 break-all">ACL：{item.acl_json || '-'}</div>
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
                    <Button size="sm" onClick={async () => { try { await reviewMetadata(item.knowledge_id, true); await load(); } catch (error) { alert(error instanceof Error ? error.message : '审核失败'); } }}>
                      <ShieldCheck size={14} /> 通过
                    </Button>
                    <Button size="sm" variant="outline" onClick={async () => { try { await archiveMetadata(item.knowledge_id); await load(); } catch (error) { alert(error instanceof Error ? error.message : '归档失败'); } }}>
                      归档
                    </Button>
                    <Button size="sm" variant="destructive" onClick={async () => { try { await deleteMetadata(item.knowledge_id); await load(); } catch (error) { alert(error instanceof Error ? error.message : '删除失败'); } }}>
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
