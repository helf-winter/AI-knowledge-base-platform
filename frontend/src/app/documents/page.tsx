'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, FileUp, RefreshCw, Search, UploadCloud, Trash2, Sparkles, FileText } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type DocumentItem = {
  document_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  parse_status: string;
  visibility: string;
  created_at?: string | null;
  updated_at?: string | null;
};

type SearchItem = {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  page_start?: number | null;
  page_end?: number | null;
  score?: number | null;
  source_file_name?: string | null;
  file_type?: string | null;
  updated_at?: string | null;
};

const MULTIMODAL_HINTS: Record<string, string> = {
  pdf: 'PDF 文档',
  docx: 'Word 文档',
  txt: '纯文本',
  md: 'Markdown',
  png: '图片',
  jpg: '图片',
  jpeg: '图片',
  csv: '表格 / CSV',
  xlsx: 'Excel 表格',
  xls: 'Excel 表格',
};

function getToken() {
  return typeof window !== 'undefined' ? localStorage.getItem('kb_token') : null;
}

function getCurrentUserId() {
  try {
    const raw = typeof window !== 'undefined' ? localStorage.getItem('kb_user') : null;
    return raw ? (JSON.parse(raw) as { user_id?: string }).user_id : null;
  } catch {
    return null;
  }
}

async function authedFetch(url: string, init?: RequestInit) {
  const token = getToken();
  const headers = new Headers(init?.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...init, headers });
}

async function fetchDocuments() {
  const res = await authedFetch(`${API_BASE}/api/v1/documents?limit=50&offset=0`);
  if (!res.ok) throw new Error('加载文档列表失败');
  const json = await res.json();
  return json.data as DocumentItem[];
}

async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await authedFetch(`${API_BASE}/api/v1/documents/upload`, { method: 'POST', body: formData });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '上传失败');
  }
  return res.json();
}

async function searchKnowledge(query: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/knowledge/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, user_id: getCurrentUserId() || 'anonymous', top_k: 8 }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '检索失败');
  }
  const json = await res.json();
  return json.data?.results as SearchItem[];
}

export default function DocumentsPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchItem[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const items = await fetchDocuments();
      setDocuments(items);
      if (!selectedDocId && items.length > 0) {
        setSelectedDocId(items[0].document_id);
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const filteredDocuments = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return documents;
    return documents.filter((doc) => [doc.file_name, doc.file_type, doc.parse_status, doc.visibility].some((v) => v?.toLowerCase().includes(q)));
  }, [documents, query]);

  const selectedDocument = filteredDocuments.find((doc) => doc.document_id === selectedDocId) ?? filteredDocuments[0] ?? null;

  const groupedSearchResults = useMemo(() => {
    const map = new Map<string, SearchItem[]>();
    searchResults.forEach((item) => {
      const list = map.get(item.document_id) ?? [];
      list.push(item);
      map.set(item.document_id, list);
    });
    return Array.from(map.entries()).map(([documentId, items]) => ({
      documentId,
      fileName: items[0]?.source_file_name ?? 'unknown',
      fileType: items[0]?.file_type ?? 'unknown',
      updatedAt: items[0]?.updated_at ?? '-',
      items,
      bestScore: items[0]?.score ?? 0,
      summary: items[0]?.content?.slice(0, 220) ?? '',
    }));
  }, [searchResults]);

  return (
    <div className="space-y-6">
      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader className="border-b border-slate-100 pb-4">
          <CardTitle className="flex items-center gap-2 text-base text-slate-950"><Sparkles size={16} /> 知识检索</CardTitle>
          <CardDescription className="text-slate-700">先检索再定位文档内容，适合快速找到相关知识片段。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <div className="relative flex-1">
              <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="输入检索关键词，例如：VPN、审批、报销" className="w-full pl-9" />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={async () => {
                  try {
                    setSearchLoading(true);
                    const items = await searchKnowledge(searchQuery);
                    setSearchResults(items);
                  } catch (error) {
                    alert(error instanceof Error ? error.message : '检索失败');
                  } finally {
                    setSearchLoading(false);
                  }
                }}
                disabled={!searchQuery || searchLoading}
              >
                {searchLoading ? '检索中...' : '开始检索'}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults([]);
                }}
              >
                清空结果
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">Vector Search</Badge>
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">Keyword Search</Badge>
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">Rerank</Badge>
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">ACL Filter</Badge>
          </div>

          {groupedSearchResults.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">还没有检索结果。</div>
          ) : (
            <div className="space-y-3">
              {groupedSearchResults.map((group) => (
                <div key={group.documentId} className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-3">
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2 text-sm font-medium text-slate-950">
                        <FileText size={16} className="text-slate-700" />
                        <span className="truncate">{group.fileName}</span>
                      </div>
                      <div className="text-xs text-slate-600">类型：{group.fileType} · 更新：{group.updatedAt} · 命中 {group.items.length} 条</div>
                      <div className="text-xs text-slate-600">文档 ID：{group.documentId}</div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">Score {group.bestScore.toFixed(4)}</Badge>
                      <Button asChild variant="outline" className="rounded-full bg-white">
                        <Link href={`/documents/${group.documentId}?highlight=${encodeURIComponent(searchQuery.trim())}`}>查看详情 <ArrowRight size={14} /></Link>
                      </Button>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">内容摘要</div>
                    <p className="mt-2 text-sm leading-7 text-slate-900">{group.summary || '暂无可展示摘要'}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader className="space-y-4 border-b border-slate-100 pb-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle className="text-base text-slate-950">知识文档</CardTitle>
                <CardDescription className="text-slate-700">在这里查看最近上传的文档，并选择一个文档查看详情。</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索文件名、类型或状态" className="w-[280px] pl-9" />
                </div>
                <Button variant="outline" onClick={() => void load()} disabled={loading} className="text-slate-700">
                  <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {filteredDocuments.length === 0 ? (
              <div className="p-6">
                <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-sm text-slate-500">还没有文档。先上传一个文件开始使用。</div>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {filteredDocuments.map((doc) => {
                  const active = selectedDocument?.document_id === doc.document_id;
                  return (
                    <button
                      key={doc.document_id}
                      type="button"
                      onClick={() => router.push(`/documents/${doc.document_id}`)}
                      className={`w-full px-6 py-4 text-left transition ${active ? 'bg-slate-50' : 'hover:bg-slate-50'}`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <div className="truncate text-sm font-medium text-slate-950">{doc.file_name}</div>
                            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{doc.parse_status}</Badge>
                          </div>
                          <div className="mt-1 text-xs text-slate-600">{doc.document_id}</div>
                          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                            <span>类型：{doc.file_type}</span>
                            <span>大小：{doc.file_size}</span>
                            <span>可见性：{doc.visibility}</span>
                            <span>更新：{doc.updated_at ?? '-'}</span>
                          </div>
                        </div>
                        <ArrowRight size={16} className="mt-1 shrink-0 text-slate-400" />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base text-slate-950"><UploadCloud size={16} /> 上传文档</CardTitle>
              <CardDescription className="text-slate-700">选择一个文件后上传，系统会自动解析。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input type="file" accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.csv,.xlsx,.xls" onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)} />
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{selectedFile ? MULTIMODAL_HINTS[selectedFile.name.split('.').pop()?.toLowerCase() || ''] || '未知类型' : '尚未选择文件'}</Badge>
                <Button
                  onClick={async () => {
                    if (!selectedFile) {
                      alert('请先选择文件');
                      return;
                    }
                    if (selectedFile.size <= 0) {
                      alert('空文件无法上传');
                      return;
                    }
                    try {
                      setUploading(true);
                      const result = await uploadDocument(selectedFile);
                      await load();
                      const documentId = result?.data?.document_id;
                      if (documentId) router.push(`/documents/${documentId}`);
                    } catch (error) {
                      alert(error instanceof Error ? error.message : '上传失败');
                    } finally {
                      setUploading(false);
                    }
                  }}
                  disabled={!selectedFile || uploading}
                >
                  {uploading ? '上传中...' : '开始上传'}
                </Button>
                <Button variant="outline" onClick={() => void load()} disabled={loading}>
                  <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新列表
                </Button>
              </div>
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600">图片和表格会尝试进行基础 OCR / 结构化抽取。上传成功后会自动进入知识库。</div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base text-slate-950"><FileUp size={16} /> 文档摘要</CardTitle>
              <CardDescription className="text-slate-700">快速查看当前选中文档的信息。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedDocument ? (
                <>
                  <div>
                    <div className="text-base font-medium text-slate-950">{selectedDocument.file_name}</div>
                    <div className="mt-1 text-xs text-slate-600">{selectedDocument.document_id}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm text-slate-700">
                    <div className="rounded-2xl bg-slate-50 p-3">类型：{selectedDocument.file_type}</div>
                    <div className="rounded-2xl bg-slate-50 p-3">状态：{selectedDocument.parse_status}</div>
                    <div className="rounded-2xl bg-slate-50 p-3">大小：{selectedDocument.file_size}</div>
                    <div className="rounded-2xl bg-slate-50 p-3">可见性：{selectedDocument.visibility}</div>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Button asChild className="w-full" variant="outline">
                      <Link href={`/documents/${selectedDocument.document_id}`}>查看详情 <ArrowRight size={14} /></Link>
                    </Button>
                    <Button
                      variant="destructive"
                      className="w-full"
                      onClick={async () => {
                        const ok = confirm(`确定删除文档「${selectedDocument.file_name}」吗？此操作不可恢复。`);
                        if (!ok) return;
                        try {
                          const res = await authedFetch(`${API_BASE}/api/v1/documents/${selectedDocument.document_id}`, { method: 'DELETE' });
                          if (!res.ok) {
                            const text = await res.text().catch(() => '');
                            throw new Error(text || '删除失败');
                          }
                          await load();
                          setSelectedDocId(null);
                        } catch (error) {
                          alert(error instanceof Error ? error.message : '删除失败');
                        }
                      }}
                    >
                      <Trash2 size={14} /> 删除文档
                    </Button>
                  </div>
                </>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">请选择左侧一条文档查看摘要。</div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
