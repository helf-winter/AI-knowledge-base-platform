'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { RefreshCw, Puzzle, Sparkles, Search, ArrowRight, Settings2, UserRoundCog, BookMarked } from 'lucide-react';
import { knowledgeTypeLabel, metadataStatusLabel, sourceTypeLabel, taskTypeLabel } from '@/lib/display-labels';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type Skill = {
  skill_id: string;
  name: string;
  version: string;
  description: string;
  capabilities: string[];
};

type ExpertAgent = {
  agent_id: string;
  name: string;
  description?: string | null;
  knowledge_domain: string;
  knowledge_scope_json?: string | null;
  skills_json?: string | null;
  model_name: string;
  prompt_version: string;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
};

const SKILL_LABELS: Record<string, string> = {
  knowledge_search: '知识检索',
  knowledge_extract: '知识抽取',
  knowledge_compare: '知识对比',
  document_summarize: '文档总结',
};

function parseSkills(skillsJson?: string | null) {
  if (!skillsJson) return ['knowledge_search'];
  try {
    const parsed = JSON.parse(skillsJson);
    return Array.isArray(parsed) ? parsed : ['knowledge_search'];
  } catch {
    return ['knowledge_search'];
  }
}

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

function getToken() {
  return typeof window !== 'undefined' ? localStorage.getItem('kb_token') : null;
}

async function authedFetch(url: string, init?: RequestInit) {
  const token = getToken();
  const headers = new Headers(init?.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...init, headers });
}

async function fetchSkills() {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/skills`);
  if (!res.ok) throw new Error('加载能力中心失败');
  const json = await res.json();
  return json.data as Skill[];
}

async function fetchAgents() {
  const res = await authedFetch(`${API_BASE}/api/v1/admin/expert-agents`);
  if (!res.ok) throw new Error('加载专家助手失败');
  const json = await res.json();
  return json.data as ExpertAgent[];
}

async function fetchMetadata() {
  const res = await authedFetch(`${API_BASE}/api/v1/knowledge/metadata`);
  if (!res.ok) throw new Error('加载知识条目失败');
  const json = await res.json();
  return json.data as KnowledgeMetadata[];
}

async function createAgent(payload: { name: string; description?: string; knowledge_domain: string; knowledge_scope_json?: string; skills_json?: string; model_name: string; prompt_version: string; status: string }) {
  const res = await fetch(`${API_BASE}/api/v1/admin/expert-agents`, {
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

export default function SkillsPage() {
  const router = useRouter();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [agents, setAgents] = useState<ExpertAgent[]>([]);
  const [metadata, setMetadata] = useState<KnowledgeMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('');
  const [desc, setDesc] = useState('');
  const [scope, setScope] = useState('');
  const [query, setQuery] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const [skillItems, agentItems, metadataItems] = await Promise.all([fetchSkills(), fetchAgents(), fetchMetadata()]);
      setSkills(skillItems);
      setAgents(agentItems);
      setMetadata(metadataItems);
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const filteredSkills = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return skills;
    return skills.filter((skill) => [skill.name, taskTypeLabel(skill.name), skill.description, skill.capabilities.join(' '), skill.capabilities.map((capability) => taskTypeLabel(capability)).join(' '), skill.version].some((v) => v.toLowerCase().includes(q)));
  }, [skills, query]);

  const filteredAgents = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return agents;
    return agents.filter((agent) => [agent.name, agent.knowledge_domain, agent.description ?? '', agent.status, metadataStatusLabel(agent.status)].some((v) => v.toLowerCase().includes(q)));
  }, [agents, query]);

  const filteredMetadata = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return metadata;
    return metadata.filter((item) => [item.title, item.document_id, item.knowledge_type, knowledgeTypeLabel(item.knowledge_type), item.status, metadataStatusLabel(item.status), item.source_type, sourceTypeLabel(item.source_type)].some((v) => v.toLowerCase().includes(q)));
  }, [metadata, query]);

  const scopeOptions = useMemo(() => metadata.slice(0, 6), [metadata]);

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
          <CardHeader className="border-b border-[color:var(--border)] pb-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base text-[color:var(--text)]"><Puzzle size={16} /> 可用能力</CardTitle>
                <CardDescription className="text-[color:var(--muted)]">这些能力可以被组合成一个更贴合业务的助手。</CardDescription>
              </div>
              <div className="relative">
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索能力、助手或知识条目" className="w-[260px] pl-9" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {filteredSkills.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                还没有可用能力。
              </div>
            ) : (
              filteredSkills.map((skill) => (
                <div key={skill.skill_id} className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium text-[color:var(--text)]">{taskTypeLabel(skill.name)}</div>
                      <div className="mt-1 text-xs text-[color:var(--muted)]">{skill.description}</div>
                    </div>
                    <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{skill.version}</Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {skill.capabilities.map((cap) => (
                      <Badge key={cap} className="bg-white text-slate-700 hover:bg-white">{taskTypeLabel(cap)}</Badge>
                    ))}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
          <CardHeader className="border-b border-[color:var(--border)] pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-[color:var(--text)]"><ArrowRight size={16} /> 一键创建专家助手</CardTitle>
            <CardDescription className="text-[color:var(--muted)]">把某个知识域快速整理成一个可以直接问答的助手。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="grid gap-3">
              <Input placeholder="助手名称" value={name} onChange={(e) => setName(e.target.value)} />
              <Input placeholder="知识域" value={domain} onChange={(e) => setDomain(e.target.value)} />
              <Input placeholder="一句话说明" value={desc} onChange={(e) => setDesc(e.target.value)} />
              <Input placeholder="知识范围 JSON" value={scope} onChange={(e) => setScope(e.target.value)} />
            </div>
            <div className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4 text-xs text-[color:var(--muted)]">
              可直接从下方知识条目里挑选一个文档作为知识域的起点，或手动填写 JSON。
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {scopeOptions.map((item) => (
                <button
                  key={item.knowledge_id}
                  type="button"
                  className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-3 text-left text-xs text-[color:var(--muted)] transition hover:border-blue-300 hover:bg-blue-50/70"
                  onClick={() => {
                    setDomain(item.knowledge_type || item.title);
                    setScope(JSON.stringify({ document_id: item.document_id, knowledge_id: item.knowledge_id, title: item.title }, null, 2));
                  }}
                >
                  <div className="font-medium text-[color:var(--text)]">{item.title}</div>
                  <div className="mt-1">{item.document_id}</div>
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={async () => {
                  try {
                    const created = await createAgent({
                      name,
                      description: desc || undefined,
                      knowledge_domain: domain,
                      knowledge_scope_json: scope || undefined,
                      skills_json: JSON.stringify(['knowledge_search', 'knowledge_extract', 'knowledge_compare']),
                      model_name: 'deepseek',
                      prompt_version: 'v1',
                      status: 'active',
                    });
                    await load();
                    const agentId = created?.data?.agent_id;
                    if (agentId) {
                      router.push(`/chat?agent_id=${encodeURIComponent(agentId)}&query=${encodeURIComponent(domain || name)}`);
                    }
                    alert('创建成功');
                  } catch (error) {
                    alert(error instanceof Error ? error.message : '创建失败');
                  }
                }}
                disabled={!name || !domain}
              >
                创建助手
              </Button>
              <Button variant="outline" onClick={() => void load()} disabled={loading}>
                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 刷新
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
          <CardHeader className="border-b border-[color:var(--border)] pb-4">
            <CardTitle className="text-base text-[color:var(--text)]">专家助手列表</CardTitle>
            <CardDescription className="text-[color:var(--muted)]">已经创建好的助手会出现在这里。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {filteredAgents.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[color:var(--border)] bg-white/70 p-6 text-sm text-[color:var(--muted)]">
                还没有专家助手。
              </div>
            ) : (
              filteredAgents.map((agent) => (
                <div key={agent.agent_id} className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium text-[color:var(--text)]">{agent.name}</div>
                      <div className="mt-1 text-xs text-slate-600">{agent.knowledge_domain}</div>
                    </div>
                    <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{metadataStatusLabel(agent.status)}</Badge>
                  </div>
                  <div className="mt-2 text-xs text-slate-600">{agent.description || '没有补充说明'}</div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                    <Badge className="bg-blue-50 text-blue-700 hover:bg-blue-50">Model {agent.model_name}</Badge>
                    <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">Prompt {agent.prompt_version}</Badge>
                  </div>
                  <div className="mt-3 rounded-2xl border border-[color:var(--border)] bg-white p-3 text-xs text-slate-600">
                    {agent.knowledge_scope_json || '暂无知识范围配置'}
                  </div>
                  <div className="mt-3 rounded-2xl border border-[color:var(--border)] bg-slate-50 p-3 text-xs text-slate-600">
                    <div className="mb-2 font-medium text-slate-900">Skills</div>
                    <div className="flex flex-wrap gap-2">
                      {parseSkills(agent.skills_json).map((skillId) => (
                        <Badge key={skillId} className="bg-white text-slate-700 hover:bg-white">{taskTypeLabel(skillId)}</Badge>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
          <CardHeader className="border-b border-[color:var(--border)] pb-4">
            <CardTitle className="text-base text-[color:var(--text)]">知识条目概览</CardTitle>
            <CardDescription className="text-[color:var(--muted)]">帮助你知道这个助手背后挂了哪些知识资产。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4 text-sm text-[color:var(--muted)]">
            {filteredMetadata.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[color:var(--border)] bg-white/70 p-6 text-sm text-[color:var(--muted)]">暂无相关知识条目。</div>
            ) : (
              filteredMetadata.slice(0, 5).map((item) => (
                <div key={item.knowledge_id} className="rounded-2xl border border-[color:var(--border)] bg-white/70 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-medium text-[color:var(--text)]">{item.title}</div>
                    <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{metadataStatusLabel(item.status)}</Badge>
                  </div>
                  <div className="mt-2 grid gap-2 text-xs md:grid-cols-2">
                    <div>类型：{knowledgeTypeLabel(item.knowledge_type)}</div>
                    <div>来源：{sourceTypeLabel(item.source_type)}</div>
                    <div>文档：{item.document_id}</div>
                    <div>作者：{item.author || '-'}</div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
