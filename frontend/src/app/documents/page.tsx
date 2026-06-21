'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, Clock3, FileText, FileUp, LockKeyhole, PenLine, RefreshCw, Search, Send, ShieldCheck, Sparkles, Trash2, UploadCloud } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { knowledgeSpaceLabel, parseStatusLabel, publishStatusLabel, visibilityLabel } from '@/lib/display-labels';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type DocumentItem = {
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
  visibility_type?: string;
  knowledge_space?: string;
  visibility_scope?: string | null;
  allowed_job_categories?: string | null;
  knowledge_category?: string | null;
  publish_status?: string;
  allowed_departments?: string | null;
  min_permission_level?: number;
  security_level?: string;
  is_public?: boolean;
  document_status?: string;
  can_access?: boolean;
  need_apply?: boolean;
  access_reason?: string | null;
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
  can_access?: boolean;
  need_apply?: boolean;
  access_reason?: string | null;
};

type AccessRequestTarget = {
  document_id: string;
  file_name: string;
  reason?: string | null;
};

type MyAccessRequest = {
  request_id: string;
  document_id: string;
  document_name?: string | null;
  status: 'pending' | 'approved' | 'rejected';
  reason: string;
  business_purpose: string;
  expected_duration?: string | null;
  ai_suggestion?: string | null;
  ai_risk_level?: string | null;
  ai_reason?: string | null;
  review_comment?: string | null;
  reviewed_at?: string | null;
  created_at?: string | null;
};

type PublishRequestTarget = {
  document_id: string;
  file_name: string;
};

type MyPublishRequest = {
  request_id: string;
  document_id: string;
  document_name?: string | null;
  target_category: string;
  allowed_job_categories: string;
  publish_reason: string;
  business_purpose: string;
  status: 'pending' | 'approved' | 'rejected';
  review_comment?: string | null;
  reviewed_at?: string | null;
  created_at?: string | null;
};

type TaskItem = {
  task_id: string;
  task_type: string;
  related_document_id?: string | null;
  status: string;
  stage?: string | null;
  progress_current?: number;
  progress_total?: number;
  detail?: string | null;
  retry_count: number;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type ManualKnowledgeDraft = {
  title: string;
  knowledge_category: string;
  allowed_job_categories: string;
  business_purpose: string;
  tags: string;
  content: string;
};

type KnowledgeFilterOptions = {
  knowledge_categories: string[];
  tags: string[];
  knowledge_spaces: string[];
  file_types: string[];
  allowed_job_categories: string[];
};

type SearchFilters = {
  knowledgeCategories: string[];
  tags: string[];
  knowledgeSpaces: string[];
  fileTypes: string[];
  allowedJobCategories: string[];
};

const EMPTY_SEARCH_FILTERS: SearchFilters = {
  knowledgeCategories: [],
  tags: [],
  knowledgeSpaces: [],
  fileTypes: [],
  allowedJobCategories: [],
};

const FILE_HINTS: Record<string, string> = {
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

const PUBLISH_CATEGORY_OPTIONS = ['VPN相关', 'IT流程', '制度规范', '研发知识', '业务操作', '数据处理', '外观设计', '其他'];
const JOB_CATEGORY_OPTIONS = ['全公司', '研发工程师', '信息技术部', '数据处理部门', '外观设计类', '行政人事', '财务人员', '部门内部'];

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

async function fetchDocuments() {
  const res = await authedFetch(`${API_BASE}/api/v1/documents?limit=50&offset=0`);
  if (!res.ok) throw new Error('加载文档列表失败');
  const json = await res.json();
  return (json.data ?? []) as DocumentItem[];
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

async function createManualKnowledge(draft: ManualKnowledgeDraft) {
  const res = await authedFetch(`${API_BASE}/api/v1/documents/manual`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(draft),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '保存手动知识失败');
  }
  return res.json();
}

async function fetchKnowledgeFilterOptions() {
  const res = await authedFetch(`${API_BASE}/api/v1/knowledge/filter-options`);
  if (!res.ok) throw new Error('加载筛选项失败');
  const json = await res.json();
  return (json.data ?? {
    knowledge_categories: [],
    tags: [],
    knowledge_spaces: [],
    file_types: [],
    allowed_job_categories: [],
  }) as KnowledgeFilterOptions;
}

async function searchKnowledge(query: string, searchFilters: SearchFilters) {
  const res = await authedFetch(`${API_BASE}/api/v1/knowledge/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      user_id: getCurrentUserId() || 'anonymous',
      top_k: 8,
      knowledge_categories: searchFilters.knowledgeCategories,
      tags: searchFilters.tags,
      knowledge_spaces: searchFilters.knowledgeSpaces,
      file_types: searchFilters.fileTypes,
      allowed_job_categories: searchFilters.allowedJobCategories,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '检索失败');
  }
  const json = await res.json();
  return (json.data?.results ?? []) as SearchItem[];
}

async function submitAccessRequest(target: AccessRequestTarget, reason: string, businessPurpose: string, expectedDuration: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/access-requests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_id: target.document_id,
      reason,
      business_purpose: businessPurpose,
      expected_duration: expectedDuration || null,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '提交访问申请失败');
  }
  return res.json();
}

async function fetchMyAccessRequests() {
  const res = await authedFetch(`${API_BASE}/api/v1/access-requests/my`);
  if (!res.ok) throw new Error('加载我的申请失败');
  const json = await res.json();
  return (json.data ?? []) as MyAccessRequest[];
}

async function submitPublishRequest(target: PublishRequestTarget, targetCategory: string, allowedJobCategories: string, publishReason: string, businessPurpose: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/knowledge/publish-requests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_id: target.document_id,
      target_category: targetCategory,
      allowed_job_categories: allowedJobCategories,
      publish_reason: publishReason,
      business_purpose: businessPurpose,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '提交发布申请失败');
  }
  return res.json();
}

async function fetchMyPublishRequests() {
  const res = await authedFetch(`${API_BASE}/api/v1/knowledge/publish-requests/my`);
  if (!res.ok) throw new Error('加载我的发布申请失败');
  const json = await res.json();
  return (json.data ?? []) as MyPublishRequest[];
}

async function fetchDocumentTasks(documentId: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/tasks?related_document_id=${encodeURIComponent(documentId)}`);
  if (!res.ok) throw new Error('加载文档解析任务失败');
  const json = await res.json();
  return (json.data ?? []) as TaskItem[];
}

async function retryDocumentParsing(documentId: string) {
  const res = await authedFetch(`${API_BASE}/api/v1/documents/${documentId}/parse/retry`, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '重新提交解析任务失败');
  }
  return res.json();
}

function formatSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function isAccessible(item: { can_access?: boolean }) {
  return item.can_access !== false;
}

function effectiveKnowledgeSpace(doc: DocumentItem) {
  return doc.effective_knowledge_space || doc.knowledge_space || 'public';
}

function accessStatusLabel(status: string) {
  if (status === 'approved') return '已通过';
  if (status === 'rejected') return '已拒绝';
  return '待审核';
}

function accessStatusClass(status: string) {
  if (status === 'approved') return 'bg-emerald-50 text-emerald-700 hover:bg-emerald-50';
  if (status === 'rejected') return 'bg-red-50 text-red-700 hover:bg-red-50';
  return 'bg-amber-50 text-amber-700 hover:bg-amber-50';
}

export default function DocumentsPage() {
  const router = useRouter();
  const currentUserId = getCurrentUserId();
  const currentUserRoles = getCurrentUserRoles();
  const isAdminUser = currentUserRoles.includes('admin') || currentUserRoles.includes('reviewer');

  function canDeleteDocument(document: DocumentItem) {
    if (document.owner_user_id && document.owner_user_id === currentUserId) return true;
    if (document.knowledge_space === 'personal' && document.owner_user_id) return false;
    return isAdminUser;
  }
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [manualDraft, setManualDraft] = useState<ManualKnowledgeDraft>({
    title: '',
    knowledge_category: '经验总结',
    allowed_job_categories: '全公司',
    business_purpose: '',
    tags: '',
    content: '',
  });
  const [manualSaving, setManualSaving] = useState(false);
  const [query, setQuery] = useState('');
  const [spaceFilter, setSpaceFilter] = useState('all');
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchItem[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [filterOptions, setFilterOptions] = useState<KnowledgeFilterOptions>({
    knowledge_categories: [],
    tags: [],
    knowledge_spaces: [],
    file_types: [],
    allowed_job_categories: [],
  });
  const [searchFilters, setSearchFilters] = useState<SearchFilters>(EMPTY_SEARCH_FILTERS);
  const [requestTarget, setRequestTarget] = useState<AccessRequestTarget | null>(null);
  const [requestReason, setRequestReason] = useState('');
  const [businessPurpose, setBusinessPurpose] = useState('');
  const [expectedDuration, setExpectedDuration] = useState('7天');
  const [requestSubmitting, setRequestSubmitting] = useState(false);
  const [myRequests, setMyRequests] = useState<MyAccessRequest[]>([]);
  const [myRequestsLoading, setMyRequestsLoading] = useState(false);
  const [publishTarget, setPublishTarget] = useState<PublishRequestTarget | null>(null);
  const [targetCategory, setTargetCategory] = useState('');
  const [allowedJobCategories, setAllowedJobCategories] = useState('全公司');
  const [publishReason, setPublishReason] = useState('');
  const [publishBusinessPurpose, setPublishBusinessPurpose] = useState('');
  const [publishSubmitting, setPublishSubmitting] = useState(false);
  const [myPublishRequests, setMyPublishRequests] = useState<MyPublishRequest[]>([]);
  const [myPublishLoading, setMyPublishLoading] = useState(false);
  const [documentTasks, setDocumentTasks] = useState<TaskItem[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [retryingParse, setRetryingParse] = useState(false);

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

  const loadMyRequests = async () => {
    setMyRequestsLoading(true);
    try {
      setMyRequests(await fetchMyAccessRequests());
    } catch (error) {
      console.warn(error);
    } finally {
      setMyRequestsLoading(false);
    }
  };

  const loadMyPublishRequests = async () => {
    setMyPublishLoading(true);
    try {
      setMyPublishRequests(await fetchMyPublishRequests());
    } catch (error) {
      console.warn(error);
    } finally {
      setMyPublishLoading(false);
    }
  };

  useEffect(() => {
    void load();
    void fetchKnowledgeFilterOptions()
      .then(setFilterOptions)
      .catch((error) => console.warn(error));
    if (!isAdminUser) {
      void loadMyRequests();
      void loadMyPublishRequests();
    }
  }, []);

  const loadDocumentTasks = async (documentId: string) => {
    setTasksLoading(true);
    try {
      setDocumentTasks(await fetchDocumentTasks(documentId));
    } catch (error) {
      console.warn(error);
    } finally {
      setTasksLoading(false);
    }
  };

  const filteredDocuments = useMemo(() => {
    const q = query.trim().toLowerCase();
    return documents.filter((doc) => {
      const space = effectiveKnowledgeSpace(doc);
      const spaceOk = spaceFilter === 'all' || space === spaceFilter;
      if (!spaceOk) return false;
      if (!q) return true;
      return [
        doc.file_name,
        doc.file_type,
        doc.parse_status,
        parseStatusLabel(doc.parse_status),
        doc.visibility,
        visibilityLabel(doc.visibility_type || doc.visibility),
        doc.knowledge_space,
        doc.effective_knowledge_space,
        knowledgeSpaceLabel(doc.knowledge_space),
        knowledgeSpaceLabel(doc.effective_knowledge_space),
        doc.public_ref_category,
        doc.publish_status,
        publishStatusLabel(doc.publish_status),
        doc.access_reason,
      ].some((v) => v?.toLowerCase().includes(q));
    });
  }, [documents, query, spaceFilter]);

  const selectedDocument = filteredDocuments.find((doc) => doc.document_id === selectedDocId) ?? filteredDocuments[0] ?? null;
  const selectedParseTask = useMemo(
    () => documentTasks.find((task) => task.task_type === 'parse_document' && task.related_document_id === selectedDocument?.document_id) ?? null,
    [documentTasks, selectedDocument?.document_id],
  );

  useEffect(() => {
    if (!selectedDocument?.document_id) {
      setDocumentTasks([]);
      return;
    }
    void loadDocumentTasks(selectedDocument.document_id);
  }, [selectedDocument?.document_id]);

  useEffect(() => {
    if (!selectedDocument?.document_id) return;
    const active = selectedDocument.parse_status === 'queued' || selectedDocument.parse_status === 'processing' || ['queued', 'pending', 'running'].includes(selectedParseTask?.status || '');
    if (!active) return;
    const timer = window.setInterval(() => {
      void load();
      void loadDocumentTasks(selectedDocument.document_id);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [selectedDocument?.document_id, selectedDocument?.parse_status, selectedParseTask?.status]);

  const groupedSearchResults = useMemo(() => {
    const map = new Map<string, SearchItem[]>();
    searchResults.forEach((item) => {
      const list = map.get(item.document_id) ?? [];
      list.push(item);
      map.set(item.document_id, list);
    });
    return Array.from(map.entries()).map(([documentId, items]) => {
      const first = items[0];
      const canAccess = items.some((item) => isAccessible(item));
      return {
        documentId,
        fileName: first?.source_file_name ?? 'unknown',
        fileType: first?.file_type ?? 'unknown',
        updatedAt: first?.updated_at ?? '-',
        items,
        canAccess,
        needApply: items.some((item) => item.need_apply),
        accessReason: first?.access_reason,
        bestScore: first?.score ?? 0,
        summary: canAccess ? items.find((item) => item.content)?.content?.slice(0, 220) ?? '' : '',
      };
    });
  }, [searchResults]);

  const openRequestDialog = (target: AccessRequestTarget) => {
    setRequestTarget(target);
    setRequestReason(target.reason || '需要查阅该文档以完成当前工作。');
    setBusinessPurpose('');
    setExpectedDuration('7天');
  };

  const openPublishDialog = (target: PublishRequestTarget) => {
    setPublishTarget(target);
    setTargetCategory(PUBLISH_CATEGORY_OPTIONS[0]);
    setAllowedJobCategories('全公司');
    setPublishReason('该个人知识已经整理完成，希望发布到公有知识库供团队复用。');
    setPublishBusinessPurpose('');
  };

  const resetManualDraft = () => {
    setManualDraft({
      title: '',
      knowledge_category: '经验总结',
      allowed_job_categories: '全公司',
      business_purpose: '',
      tags: '',
      content: '',
    });
  };

  const toggleSearchFilter = (key: keyof SearchFilters, value: string) => {
    setSearchFilters((current) => {
      const values = current[key];
      const nextValues = values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
      return { ...current, [key]: nextValues };
    });
  };

  const hasActiveSearchFilters =
    searchFilters.knowledgeCategories.length > 0 ||
    searchFilters.tags.length > 0 ||
    searchFilters.knowledgeSpaces.length > 0 ||
    searchFilters.fileTypes.length > 0 ||
    searchFilters.allowedJobCategories.length > 0;

  const canPublishDocument = (doc: DocumentItem | null) =>
    Boolean(
      doc &&
        isAccessible(doc) &&
        doc.owner_user_id === currentUserId &&
        effectiveKnowledgeSpace(doc) === 'personal' &&
        doc.publish_status !== 'pending' &&
        doc.publish_status !== 'approved',
    );

  return (
    <div className="space-y-6">
      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader className="border-b border-slate-100 pb-4">
          <CardTitle className="flex items-center gap-2 text-base text-slate-950"><Sparkles size={16} /> 知识检索</CardTitle>
          <CardDescription className="text-slate-700">先检索再定位文档内容。无权限的命中文档会展示来源，但不会泄露正文。</CardDescription>
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
                    const items = await searchKnowledge(searchQuery, searchFilters);
                    setSearchResults(items);
                  } catch (error) {
                    alert(error instanceof Error ? error.message : '检索失败');
                  } finally {
                    setSearchLoading(false);
                  }
                }}
                disabled={!searchQuery.trim() || searchLoading}
              >
                {searchLoading ? '检索中...' : '开始检索'}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults([]);
                  setSearchFilters(EMPTY_SEARCH_FILTERS);
                }}
              >
                清空结果
              </Button>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-medium text-slate-900">标签筛选</div>
              {hasActiveSearchFilters && (
                <Button size="sm" variant="ghost" onClick={() => setSearchFilters(EMPTY_SEARCH_FILTERS)}>
                  清空筛选
                </Button>
              )}
            </div>
            <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
              <label className="space-y-1 text-xs font-medium text-slate-700">
                知识类别
                <select className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-normal text-slate-900" value="" onChange={(event) => event.target.value && toggleSearchFilter('knowledgeCategories', event.target.value)}>
                  <option value="">选择类别</option>
                  {filterOptions.knowledge_categories.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1 text-xs font-medium text-slate-700">
                标签
                <select className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-normal text-slate-900" value="" onChange={(event) => event.target.value && toggleSearchFilter('tags', event.target.value)}>
                  <option value="">选择标签</option>
                  {filterOptions.tags.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1 text-xs font-medium text-slate-700">
                知识空间
                <select className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-normal text-slate-900" value="" onChange={(event) => event.target.value && toggleSearchFilter('knowledgeSpaces', event.target.value)}>
                  <option value="">选择空间</option>
                  {filterOptions.knowledge_spaces.map((item) => <option key={item} value={item}>{knowledgeSpaceLabel(item)}</option>)}
                </select>
              </label>
              <label className="space-y-1 text-xs font-medium text-slate-700">
                文件类型
                <select className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-normal text-slate-900" value="" onChange={(event) => event.target.value && toggleSearchFilter('fileTypes', event.target.value)}>
                  <option value="">选择类型</option>
                  {filterOptions.file_types.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1 text-xs font-medium text-slate-700">
                可访问人员
                <select className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-normal text-slate-900" value="" onChange={(event) => event.target.value && toggleSearchFilter('allowedJobCategories', event.target.value)}>
                  <option value="">选择人员范围</option>
                  {filterOptions.allowed_job_categories.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
            </div>
            {hasActiveSearchFilters && (
              <div className="mt-3 flex flex-wrap gap-2">
                {searchFilters.knowledgeCategories.map((item) => <Badge key={`category-${item}`} onClick={() => toggleSearchFilter('knowledgeCategories', item)} className="cursor-pointer bg-blue-50 text-blue-700 hover:bg-blue-100">类别：{item}</Badge>)}
                {searchFilters.tags.map((item) => <Badge key={`tag-${item}`} onClick={() => toggleSearchFilter('tags', item)} className="cursor-pointer bg-emerald-50 text-emerald-700 hover:bg-emerald-100">标签：{item}</Badge>)}
                {searchFilters.knowledgeSpaces.map((item) => <Badge key={`space-${item}`} onClick={() => toggleSearchFilter('knowledgeSpaces', item)} className="cursor-pointer bg-violet-50 text-violet-700 hover:bg-violet-100">空间：{knowledgeSpaceLabel(item)}</Badge>)}
                {searchFilters.fileTypes.map((item) => <Badge key={`file-${item}`} onClick={() => toggleSearchFilter('fileTypes', item)} className="cursor-pointer bg-slate-100 text-slate-700 hover:bg-slate-200">类型：{item}</Badge>)}
                {searchFilters.allowedJobCategories.map((item) => <Badge key={`job-${item}`} onClick={() => toggleSearchFilter('allowedJobCategories', item)} className="cursor-pointer bg-amber-50 text-amber-700 hover:bg-amber-100">人员：{item}</Badge>)}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">Vector Search</Badge>
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">Keyword Search</Badge>
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">Rerank</Badge>
            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">ACL Filter</Badge>
          </div>

          {groupedSearchResults.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">还没有检索结果。</div>
          ) : (
            <div className="space-y-3">
              {groupedSearchResults.map((group) => (
                <div key={group.documentId} className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-3">
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2 text-sm font-medium text-slate-950">
                        {group.canAccess ? <FileText size={16} className="text-slate-700" /> : <LockKeyhole size={16} className="text-amber-600" />}
                        <span className="truncate">{group.fileName}</span>
                        {group.canAccess ? (
                          <Badge className="bg-emerald-50 text-emerald-700 hover:bg-emerald-50">可阅读</Badge>
                        ) : (
                          <Badge className="bg-amber-50 text-amber-700 hover:bg-amber-50">需申请</Badge>
                        )}
                      </div>
                      <div className="text-xs text-slate-600">类型：{group.fileType} · 更新：{group.updatedAt} · 命中 {group.items.length} 条</div>
                      {!group.canAccess && <div className="text-xs text-amber-700">{group.accessReason || '该文档受权限保护'}</div>}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">Score {group.bestScore.toFixed(4)}</Badge>
                      {group.canAccess ? (
                        <Button asChild variant="outline" className="rounded-full bg-white">
                          <Link href={`/documents/${group.documentId}?highlight=${encodeURIComponent(searchQuery.trim())}`}>查看详情 <ArrowRight size={14} /></Link>
                        </Button>
                      ) : (
                        <Button variant="outline" className="rounded-full bg-white" onClick={() => openRequestDialog({ document_id: group.documentId, file_name: group.fileName, reason: group.accessReason })}>
                          申请访问 <Send size={14} />
                        </Button>
                      )}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <div className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">内容摘要</div>
                    {group.canAccess ? (
                      <p className="mt-2 text-sm leading-7 text-slate-900">{group.summary || '暂无可展示摘要'}</p>
                    ) : (
                      <p className="mt-2 text-sm leading-7 text-slate-700">该命中文档受权限保护。你可以提交访问申请，审核通过后再查看正文和原文。</p>
                    )}
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
                <CardDescription className="text-slate-700">点击文档空白处更新右侧摘要；点击文档名或箭头进入详情，受限文档只能申请访问。</CardDescription>
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
            <div className="flex flex-wrap gap-2">
              {[
                { value: 'all', label: '全部知识' },
                { value: 'personal', label: '个人知识' },
                { value: 'public', label: '公有知识' },
                { value: 'department', label: '部门知识' },
              ].map((item) => (
                <Button key={item.value} size="sm" variant={spaceFilter === item.value ? 'default' : 'outline'} onClick={() => setSpaceFilter(item.value)}>
                  {item.label}
                </Button>
              ))}
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {filteredDocuments.length === 0 ? (
              <div className="p-6">
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-sm text-slate-500">
                  {documents.length === 0 ? '还没有文档。先上传一个文件开始使用。' : '当前筛选条件下暂无文档。'}
                </div>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {filteredDocuments.map((doc) => {
                  const active = selectedDocument?.document_id === doc.document_id;
                  const canAccess = isAccessible(doc);
                  return (
                    <div
                      key={doc.document_id}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedDocId(doc.document_id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          setSelectedDocId(doc.document_id);
                        }
                      }}
                      className={`w-full cursor-pointer px-6 py-4 text-left transition ${active ? 'bg-slate-50' : 'hover:bg-slate-50'}`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            {canAccess ? <ShieldCheck size={15} className="text-emerald-600" /> : <LockKeyhole size={15} className="text-amber-600" />}
                            {canAccess ? (
                              <Link
                                href={`/documents/${doc.document_id}`}
                                onClick={(event) => event.stopPropagation()}
                                className="truncate text-sm font-medium text-slate-950 hover:text-blue-700"
                              >
                                {doc.file_name}
                              </Link>
                            ) : (
                              <span className="truncate text-sm font-medium text-slate-950">{doc.file_name}</span>
                            )}
                            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{parseStatusLabel(doc.parse_status)}</Badge>
                            {canAccess ? (
                              <Badge className="bg-emerald-50 text-emerald-700 hover:bg-emerald-50">可阅读</Badge>
                            ) : (
                              <Badge className="bg-amber-50 text-amber-700 hover:bg-amber-50">需申请</Badge>
                            )}
                          </div>
                          <div className="mt-1 text-xs text-slate-600">{doc.document_id}</div>
                          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                            <span>类型：{doc.file_type}</span>
                            <span>大小：{formatSize(doc.file_size)}</span>
                            <span>可见性：{visibilityLabel(doc.visibility_type || doc.visibility)}</span>
                            <span>空间：{knowledgeSpaceLabel(effectiveKnowledgeSpace(doc))}</span>
                            {doc.public_ref_id && doc.knowledge_space === 'personal' && <span>原始：{knowledgeSpaceLabel(doc.knowledge_space)}</span>}
                            <span>发布：{publishStatusLabel(doc.publish_status || 'none')}</span>
                            <span>等级：L{doc.min_permission_level ?? 1}</span>
                            <span>更新：{doc.updated_at ?? '-'}</span>
                          </div>
                          {!canAccess && <div className="mt-2 text-xs text-amber-700">{doc.access_reason || '该文档受权限保护'}</div>}
                        </div>
                        {canAccess ? (
                          <Link
                            href={`/documents/${doc.document_id}`}
                            onClick={(event) => event.stopPropagation()}
                            aria-label={`查看 ${doc.file_name} 详情`}
                            className="mt-1 shrink-0 rounded-full p-2 text-slate-400 transition hover:bg-blue-50 hover:text-blue-700"
                          >
                            <ArrowRight size={16} />
                          </Link>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            className="mt-1 shrink-0"
                            onClick={(event) => {
                              event.stopPropagation();
                              openRequestDialog({ document_id: doc.document_id, file_name: doc.file_name, reason: doc.access_reason });
                            }}
                          >
                            申请
                          </Button>
                        )}
                        {canPublishDocument(doc) && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="mt-1 shrink-0"
                            onClick={(event) => {
                              event.stopPropagation();
                              openPublishDialog({ document_id: doc.document_id, file_name: doc.file_name });
                            }}
                          >
                            发布审核
                          </Button>
                        )}
                      </div>
                    </div>
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
              <CardDescription className="text-slate-700">选择文件后上传，系统会自动解析并进入知识库。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input type="file" accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.csv,.xlsx,.xls" onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)} />
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{selectedFile ? FILE_HINTS[selectedFile.name.split('.').pop()?.toLowerCase() || ''] || '未知类型' : '尚未选择文件'}</Badge>
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
              <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600">图片和表格会尝试进行基础 OCR / 结构化抽取。上传文档默认进入个人知识空间，只有创建者可直接阅读。</div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base text-slate-950"><PenLine size={16} /> 手动记录知识</CardTitle>
              <CardDescription className="text-slate-700">把经验、流程、排障结论直接写成 Markdown 知识，默认保存到个人知识空间。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                value={manualDraft.title}
                onChange={(event) => setManualDraft((draft) => ({ ...draft, title: event.target.value }))}
                placeholder="标题，例如：VPN 申请经验"
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  value={manualDraft.knowledge_category}
                  onChange={(event) => setManualDraft((draft) => ({ ...draft, knowledge_category: event.target.value }))}
                  placeholder="知识类别，例如：IT 流程"
                />
                <Input
                  value={manualDraft.allowed_job_categories}
                  onChange={(event) => setManualDraft((draft) => ({ ...draft, allowed_job_categories: event.target.value }))}
                  placeholder="适用人员，例如：全公司"
                />
              </div>
              <Input
                value={manualDraft.business_purpose}
                onChange={(event) => setManualDraft((draft) => ({ ...draft, business_purpose: event.target.value }))}
                placeholder="业务用途，例如：减少 VPN 申请咨询成本"
              />
              <Input
                value={manualDraft.tags}
                onChange={(event) => setManualDraft((draft) => ({ ...draft, tags: event.target.value }))}
                placeholder="标签，用逗号分隔，例如：VPN,权限申请,远程办公"
              />
              <Textarea
                value={manualDraft.content}
                onChange={(event) => setManualDraft((draft) => ({ ...draft, content: event.target.value }))}
                placeholder={'用 Markdown 写正文，例如：\n## 适用场景\n员工需要远程访问内网系统。\n\n## 操作步骤\n1. 在 IT 服务台提交申请。\n2. 等待审批通过。'}
                className="min-h-48 bg-white text-slate-900 placeholder:text-slate-400"
              />
              <div className="flex flex-wrap justify-end gap-2">
                <Button variant="outline" onClick={resetManualDraft} disabled={manualSaving}>
                  清空
                </Button>
                <Button
                  disabled={manualSaving || !manualDraft.title.trim() || !manualDraft.knowledge_category.trim() || !manualDraft.content.trim()}
                  onClick={async () => {
                    try {
                      setManualSaving(true);
                      const result = await createManualKnowledge({
                        title: manualDraft.title.trim(),
                        knowledge_category: manualDraft.knowledge_category.trim(),
                        allowed_job_categories: manualDraft.allowed_job_categories.trim(),
                        business_purpose: manualDraft.business_purpose.trim(),
                        tags: manualDraft.tags.trim(),
                        content: manualDraft.content.trim(),
                      });
                      await load();
                      resetManualDraft();
                      const documentId = result?.data?.document_id;
                      if (documentId) router.push(`/documents/${documentId}`);
                    } catch (error) {
                      alert(error instanceof Error ? error.message : '保存手动知识失败');
                    } finally {
                      setManualSaving(false);
                    }
                  }}
                >
                  {manualSaving ? '保存中...' : '保存为个人知识'}
                </Button>
              </div>
              <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">保存后可以在左侧文档列表中找到它，也可以像上传文档一样提交“公有发布审核”。</div>
            </CardContent>
          </Card>

          {!isAdminUser && (
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base text-slate-950"><Clock3 size={16} /> 我的申请</CardTitle>
              <CardDescription className="text-slate-700">查看文档访问申请的审核状态和管理员意见。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-end">
                <Button variant="outline" size="sm" onClick={() => void loadMyRequests()} disabled={myRequestsLoading}>
                  <RefreshCw size={14} className={myRequestsLoading ? 'animate-spin' : ''} /> 刷新
                </Button>
              </div>
              {myRequests.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">暂时没有访问申请。</div>
              ) : (
                <div className="space-y-3">
                  {myRequests.slice(0, 5).map((item) => (
                    <div key={item.request_id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="min-w-0 truncate text-sm font-medium text-slate-950">{item.document_name || item.document_id}</div>
                        <Badge className={accessStatusClass(item.status)}>{accessStatusLabel(item.status)}</Badge>
                      </div>
                      <div className="mt-2 text-xs text-slate-600">申请时间：{item.created_at || '-'}</div>
                      <div className="mt-2 text-sm leading-6 text-slate-700">用途：{item.business_purpose}</div>
                      {item.ai_suggestion && (
                        <div className="mt-2 text-xs text-slate-600">AI 建议：{item.ai_suggestion} · 风险：{item.ai_risk_level || '-'}</div>
                      )}
                      {item.review_comment && (
                        <div className="mt-2 rounded-lg bg-white p-3 text-sm text-slate-700">审核意见：{item.review_comment}</div>
                      )}
                      {item.status === 'approved' && (
                        <Button asChild size="sm" variant="outline" className="mt-3">
                          <Link href={`/documents/${item.document_id}`}>查看文档 <ArrowRight size={14} /></Link>
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
          )}

          {!isAdminUser && (
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base text-slate-950"><UploadCloud size={16} /> 我的发布申请</CardTitle>
              <CardDescription className="text-slate-700">个人知识提交到公有知识库后，需要管理员审核通过才会进入公共检索。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-end">
                <Button variant="outline" size="sm" onClick={() => void loadMyPublishRequests()} disabled={myPublishLoading}>
                  <RefreshCw size={14} className={myPublishLoading ? 'animate-spin' : ''} /> 刷新
                </Button>
              </div>
              {myPublishRequests.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">暂时没有发布申请。</div>
              ) : (
                <div className="space-y-3">
                  {myPublishRequests.slice(0, 5).map((item) => (
                    <div key={item.request_id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="min-w-0 truncate text-sm font-medium text-slate-950">{item.document_name || item.document_id}</div>
                        <Badge className={accessStatusClass(item.status)}>{accessStatusLabel(item.status)}</Badge>
                      </div>
                      <div className="mt-2 text-xs text-slate-600">类别：{item.target_category} · 可访问：{item.allowed_job_categories}</div>
                      <div className="mt-2 text-sm leading-6 text-slate-700">用途：{item.business_purpose}</div>
                      {item.review_comment && <div className="mt-2 rounded-lg bg-white p-3 text-sm text-slate-700">审核意见：{item.review_comment}</div>}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
          )}

          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base text-slate-950"><FileUp size={16} /> 文档摘要</CardTitle>
              <CardDescription className="text-slate-700">快速查看当前选中文档的信息。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedDocument ? (
                <>
                  <div>
                    <div className="flex items-center gap-2 text-base font-medium text-slate-950">
                      {isAccessible(selectedDocument) ? <ShieldCheck size={16} className="text-emerald-600" /> : <LockKeyhole size={16} className="text-amber-600" />}
                      {selectedDocument.file_name}
                    </div>
                    <div className="mt-1 text-xs text-slate-600">{selectedDocument.document_id}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm text-slate-700">
                    <div className="rounded-xl bg-slate-50 p-3">类型：{selectedDocument.file_type}</div>
                    <div className="rounded-xl bg-slate-50 p-3">状态：{parseStatusLabel(selectedDocument.parse_status)}</div>
                    <div className="rounded-xl bg-slate-50 p-3">大小：{formatSize(selectedDocument.file_size)}</div>
                    <div className="rounded-xl bg-slate-50 p-3">权限：{isAccessible(selectedDocument) ? '可阅读' : '需申请'}</div>
                    <div className="rounded-xl bg-slate-50 p-3">空间：{knowledgeSpaceLabel(effectiveKnowledgeSpace(selectedDocument))}</div>
                    {selectedDocument.public_ref_id && selectedDocument.knowledge_space === 'personal' && (
                      <div className="rounded-xl bg-slate-50 p-3">原始：{knowledgeSpaceLabel(selectedDocument.knowledge_space)}</div>
                    )}
                    <div className="rounded-xl bg-slate-50 p-3">发布：{publishStatusLabel(selectedDocument.publish_status || 'none')}</div>
                  </div>
                  {selectedParseTask && (
                    <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="font-medium">解析进度</div>
                        <Badge className="bg-white text-blue-700 hover:bg-white">{parseStatusLabel(selectedParseTask.status)}</Badge>
                      </div>
                      <div className="mt-2 text-blue-800">
                        阶段：{parseStatusLabel(selectedParseTask.stage || selectedParseTask.status)}
                        {selectedParseTask.progress_total ? ` · ${selectedParseTask.progress_current || 0}/${selectedParseTask.progress_total}` : ''}
                      </div>
                      {(selectedParseTask.detail || selectedParseTask.error_message) && (
                        <div className="mt-2 rounded-lg bg-white/80 p-3 text-blue-900">
                          {selectedParseTask.error_message || (selectedParseTask.status === 'succeeded' ? '解析完成' : selectedParseTask.detail)}
                        </div>
                      )}
                      {tasksLoading && <div className="mt-2 text-xs text-blue-700">正在刷新解析状态...</div>}
                      {['failed', 'stalled'].includes(selectedParseTask.status) && (
                        <Button
                          className="mt-3"
                          size="sm"
                          variant="outline"
                          disabled={retryingParse}
                          onClick={async () => {
                            try {
                              setRetryingParse(true);
                              await retryDocumentParsing(selectedDocument.document_id);
                              await load();
                              await loadDocumentTasks(selectedDocument.document_id);
                            } catch (error) {
                              alert(error instanceof Error ? error.message : '继续解析失败');
                            } finally {
                              setRetryingParse(false);
                            }
                          }}
                        >
                          <RefreshCw size={14} className={retryingParse ? 'animate-spin' : ''} /> 继续解析
                        </Button>
                      )}
                    </div>
                  )}
                  {!isAccessible(selectedDocument) && (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                      {selectedDocument.access_reason || '该文档受权限保护。提交访问申请后，管理员审核通过即可查看正文。'}
                    </div>
                  )}
                  <div className="grid gap-2 sm:grid-cols-2">
                    {isAccessible(selectedDocument) ? (
                      <Button asChild className="w-full" variant="outline">
                        <Link href={`/documents/${selectedDocument.document_id}`}>查看详情 <ArrowRight size={14} /></Link>
                      </Button>
                    ) : (
                      <Button className="w-full" variant="outline" onClick={() => openRequestDialog({ document_id: selectedDocument.document_id, file_name: selectedDocument.file_name, reason: selectedDocument.access_reason })}>
                        申请访问 <Send size={14} />
                      </Button>
                    )}
                    {canPublishDocument(selectedDocument) && (
                      <Button className="w-full" variant="outline" onClick={() => openPublishDialog({ document_id: selectedDocument.document_id, file_name: selectedDocument.file_name })}>
                        提交公有审核 <Send size={14} />
                      </Button>
                    )}
                    {canDeleteDocument(selectedDocument) && (
                      <Button
                        variant="destructive"
                        className="w-full"
                        onClick={async () => {
                          const ok = confirm(`确定删除文档“${selectedDocument.file_name}”吗？此操作不可恢复。`);
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
                    )}
                  </div>
                </>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">请选择左侧一条文档查看摘要。</div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {requestTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
          <div className="w-full max-w-xl rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-lg font-semibold text-slate-950">申请访问文档</div>
                <div className="mt-1 text-sm text-slate-600">{requestTarget.file_name}</div>
              </div>
              <Button variant="ghost" onClick={() => setRequestTarget(null)}>关闭</Button>
            </div>
            <div className="mt-5 space-y-4">
              <div>
                <div className="mb-2 text-sm font-medium text-slate-800">申请原因</div>
                <Textarea value={requestReason} onChange={(event) => setRequestReason(event.target.value)} className="bg-white text-slate-900 placeholder:text-slate-400" />
              </div>
              <div>
                <div className="mb-2 text-sm font-medium text-slate-800">业务用途</div>
                <Textarea value={businessPurpose} onChange={(event) => setBusinessPurpose(event.target.value)} placeholder="例如：处理 VPN 申请咨询、完善部门知识库、排查员工问题等" className="bg-white text-slate-900 placeholder:text-slate-400" />
              </div>
              <div>
                <div className="mb-2 text-sm font-medium text-slate-800">预计使用时长</div>
                <Input value={expectedDuration} onChange={(event) => setExpectedDuration(event.target.value)} placeholder="例如：7天、30天、长期" />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setRequestTarget(null)}>取消</Button>
                <Button
                  disabled={requestSubmitting || !requestReason.trim() || !businessPurpose.trim()}
                  onClick={async () => {
                    if (!requestTarget) return;
                    try {
                      setRequestSubmitting(true);
                      await submitAccessRequest(requestTarget, requestReason.trim(), businessPurpose.trim(), expectedDuration.trim());
                      await loadMyRequests();
                      alert('访问申请已提交，等待管理员审核。');
                      setRequestTarget(null);
                    } catch (error) {
                      alert(error instanceof Error ? error.message : '提交访问申请失败');
                    } finally {
                      setRequestSubmitting(false);
                    }
                  }}
                >
                  {requestSubmitting ? '提交中...' : '提交申请'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {publishTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
          <div className="w-full max-w-xl rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-lg font-semibold text-slate-950">提交到公有知识库</div>
                <div className="mt-1 text-sm text-slate-600">{publishTarget.file_name}</div>
              </div>
              <Button variant="ghost" onClick={() => setPublishTarget(null)}>关闭</Button>
            </div>
            <div className="mt-5 space-y-4">
              <div>
                <div className="mb-2 text-sm font-medium text-slate-800">希望划分的知识类别</div>
                <select
                  value={targetCategory}
                  onChange={(event) => setTargetCategory(event.target.value)}
                  className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                >
                  {PUBLISH_CATEGORY_OPTIONS.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>
              <div>
                <div className="mb-2 text-sm font-medium text-slate-800">可访问人员工作类别</div>
                <select
                  value={allowedJobCategories}
                  onChange={(event) => setAllowedJobCategories(event.target.value)}
                  className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                >
                  {JOB_CATEGORY_OPTIONS.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>
              <div>
                <div className="mb-2 text-sm font-medium text-slate-800">发布理由</div>
                <Textarea value={publishReason} onChange={(event) => setPublishReason(event.target.value)} className="bg-white text-slate-900 placeholder:text-slate-400" />
              </div>
              <div>
                <div className="mb-2 text-sm font-medium text-slate-800">业务用途</div>
                <Textarea value={publishBusinessPurpose} onChange={(event) => setPublishBusinessPurpose(event.target.value)} placeholder="说明这份知识发布后能服务哪些业务场景" className="bg-white text-slate-900 placeholder:text-slate-400" />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setPublishTarget(null)}>取消</Button>
                <Button
                  disabled={publishSubmitting || !targetCategory.trim() || !allowedJobCategories.trim() || !publishReason.trim() || !publishBusinessPurpose.trim()}
                  onClick={async () => {
                    if (!publishTarget) return;
                    try {
                      setPublishSubmitting(true);
                      await submitPublishRequest(publishTarget, targetCategory.trim(), allowedJobCategories.trim(), publishReason.trim(), publishBusinessPurpose.trim());
                      await load();
                      await loadMyPublishRequests();
                      alert('发布申请已提交，等待管理员审核。');
                      setPublishTarget(null);
                    } catch (error) {
                      alert(error instanceof Error ? error.message : '提交发布申请失败');
                    } finally {
                      setPublishSubmitting(false);
                    }
                  }}
                >
                  {publishSubmitting ? '提交中...' : '提交发布申请'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
