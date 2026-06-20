'use client';

import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, BookMarked, CheckCircle2, Puzzle, RefreshCw, Search, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { knowledgeTypeLabel, metadataStatusLabel, sourceTypeLabel } from '@/lib/display-labels';

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

type AgentScope = {
  document_ids?: string[];
  documents?: Array<{ document_id: string; knowledge_id: string; title: string }>;
  responsibilities?: string[];
  suitable_questions?: string[];
  answer_boundaries?: string[];
  keywords?: string[];
};

const DEFAULT_AGENT_SKILLS = ['knowledge_search', 'document_summarize', 'knowledge_extract', 'knowledge_gap_detect'];

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
  if (!res.ok) throw new Error('加载可用能力失败');
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
  const res = await authedFetch(`${API_BASE}/api/v1/admin/expert-agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '创建专家助手失败');
  }
  return res.json();
}

function parseJsonObject<T>(raw?: string | null, fallback: T = {} as T): T {
  if (!raw) return fallback;
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed as T : fallback;
  } catch {
    return fallback;
  }
}

function parseSkills(skillsJson?: string | null) {
  const parsed = parseJsonObject<unknown>(skillsJson, []);
  return Array.isArray(parsed) ? parsed.map(String) : ['knowledge_search'];
}

function createDefaultAgentScope(selected: KnowledgeMetadata[], domain: string): AgentScope {
  const titles = selected.map((item) => item.title);
  const topic = domain || selected[0]?.knowledge_type || selected[0]?.title || '企业知识';
  return {
    document_ids: selected.map((item) => item.document_id),
    documents: selected.map((item) => ({ document_id: item.document_id, knowledge_id: item.knowledge_id, title: item.title })),
    responsibilities: [
      `围绕「${topic}」回答员工问题`,
      '优先引用绑定知识中的制度依据、流程步骤和注意事项',
      '当知识不足时提示用户补充资料或发起知识扩充',
    ],
    suitable_questions: [
      `如何办理或使用${topic}相关流程？`,
      `这份知识里有哪些关键步骤和注意事项？`,
      '当前问题可以参考哪些文档依据？',
    ],
    answer_boundaries: [
      '不回答绑定知识范围之外的专业问题',
      '不编造未在知识库中出现的审批结论或权限承诺',
      '涉及高风险或权限变更时提示走正式审核流程',
    ],
    keywords: Array.from(new Set([topic, ...titles].filter(Boolean))).slice(0, 8),
  };
}

function skillLabel(skillId: string, skills: Skill[]) {
  return skills.find((item) => item.skill_id === skillId)?.name ?? skillId;
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [agents, setAgents] = useState<ExpertAgent[]>([]);
  const [metadata, setMetadata] = useState<KnowledgeMetadata[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [selectedKnowledgeIds, setSelectedKnowledgeIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
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
    return skills.filter((skill) => [skill.name, skill.description, skill.capabilities.join(' '), skill.skill_id].some((value) => value.toLowerCase().includes(q)));
  }, [skills, query]);

  const filteredAgents = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return agents;
    return agents.filter((agent) => [agent.name, agent.knowledge_domain, agent.description ?? '', agent.status, agent.knowledge_scope_json ?? ''].some((value) => value.toLowerCase().includes(q)));
  }, [agents, query]);

  const filteredMetadata = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return metadata;
    return metadata.filter((item) => [item.title, item.document_id, item.knowledge_type, knowledgeTypeLabel(item.knowledge_type), item.status, metadataStatusLabel(item.status), item.source_type, sourceTypeLabel(item.source_type)].some((value) => value.toLowerCase().includes(q)));
  }, [metadata, query]);

  const selectedKnowledge = useMemo(
    () => metadata.filter((item) => selectedKnowledgeIds.includes(item.knowledge_id)),
    [metadata, selectedKnowledgeIds],
  );

  const generatedScope = useMemo(() => createDefaultAgentScope(selectedKnowledge, domain), [selectedKnowledge, domain]);

  const generateAgentDraft = () => {
    if (selectedKnowledge.length === 0) {
      alert('请先选择至少一个知识条目');
      return;
    }
    const main = selectedKnowledge[0];
    const nextDomain = domain.trim() || main.knowledge_type || main.title;
    const nextName = name.trim() || `${nextDomain}专家助手`;
    const nextDesc = desc.trim() || `面向「${nextDomain}」的问答专家，基于已绑定知识回答制度、流程和操作问题。`;
    const nextScope = createDefaultAgentScope(selectedKnowledge, nextDomain);
    setDomain(nextDomain);
    setName(nextName);
    setDesc(nextDesc);
    setScope(JSON.stringify(nextScope, null, 2));
  };

  const toggleKnowledge = (knowledgeId: string) => {
    setSelectedKnowledgeIds((current) => current.includes(knowledgeId) ? current.filter((id) => id !== knowledgeId) : [...current, knowledgeId]);
  };

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
          <CardHeader className="border-b border-[color:var(--border)] pb-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base text-[color:var(--text)]"><Puzzle size={16} /> 可用能力</CardTitle>
                <CardDescription className="text-[color:var(--muted)]">这些是专家助手可以组合调用的业务动作，不再只是内部技术名称。</CardDescription>
              </div>
              <div className="relative">
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索能力、助手或知识条目" className="w-[260px] pl-9" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid gap-3 pt-4 md:grid-cols-2">
            {filteredSkills.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500 md:col-span-2">还没有可用能力。</div>
            ) : (
              filteredSkills.map((skill) => (
                <div key={skill.skill_id} className="rounded-2xl border border-[color:var(--border)] bg-white/80 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold text-[color:var(--text)]">{skill.name}</div>
                      <div className="mt-1 text-xs text-[color:var(--muted)]">{skill.description}</div>
                    </div>
                    <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{skill.version}</Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {skill.capabilities.map((capability) => (
                      <Badge key={capability} className="bg-blue-50 text-blue-700 hover:bg-blue-50">{capability}</Badge>
                    ))}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
          <CardHeader className="border-b border-[color:var(--border)] pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-[color:var(--text)]"><Sparkles size={16} /> 一键创建专家助手</CardTitle>
            <CardDescription className="text-[color:var(--muted)]">选择知识范围，系统自动生成专家名称、职责、适用问题和回答边界。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
              <div className="font-medium">创建流程</div>
              <div className="mt-1 text-xs leading-5">选择知识条目 → 生成专家配置 → 创建后在右下角 AI 问答助手中选择使用。</div>
            </div>
            <div className="grid gap-3">
              <Input placeholder="专家名称，例如：VPN 专家助手" value={name} onChange={(e) => setName(e.target.value)} />
              <Input placeholder="知识领域，例如：VPN 相关" value={domain} onChange={(e) => setDomain(e.target.value)} />
              <Input placeholder="专家职责摘要" value={desc} onChange={(e) => setDesc(e.target.value)} />
            </div>
            <div className="rounded-2xl border border-[color:var(--border)] bg-white/80 p-4">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-medium text-[color:var(--text)]">选择知识范围</div>
                  <div className="mt-1 text-xs text-[color:var(--muted)]">已选择 {selectedKnowledge.length} 个知识条目，创建后会写入 document_ids。</div>
                </div>
                <Button type="button" variant="outline" onClick={generateAgentDraft}>生成专家配置</Button>
              </div>
              <div className="mt-3 grid max-h-64 gap-2 overflow-auto md:grid-cols-2">
                {filteredMetadata.slice(0, 10).map((item) => {
                  const selected = selectedKnowledgeIds.includes(item.knowledge_id);
                  return (
                    <button
                      key={item.knowledge_id}
                      type="button"
                      className={`rounded-2xl border p-3 text-left text-xs transition ${selected ? 'border-blue-300 bg-blue-50 text-blue-900' : 'border-[color:var(--border)] bg-white text-[color:var(--muted)] hover:border-blue-200'}`}
                      onClick={() => toggleKnowledge(item.knowledge_id)}
                    >
                      <div className="flex items-start gap-2">
                        <span className={`mt-0.5 flex size-4 items-center justify-center rounded border ${selected ? 'border-blue-500 bg-blue-600 text-white' : 'border-slate-300'}`}>
                          {selected ? <CheckCircle2 size={12} /> : null}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-[color:var(--text)]">{item.title}</span>
                          <span className="mt-1 block truncate">{item.document_id}</span>
                          <span className="mt-2 flex flex-wrap gap-1">
                            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{knowledgeTypeLabel(item.knowledge_type)}</Badge>
                            <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{metadataStatusLabel(item.status)}</Badge>
                          </span>
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="rounded-2xl border border-[color:var(--border)] bg-slate-50 p-4">
              <div className="mb-2 text-sm font-medium text-[color:var(--text)]">配置预览</div>
              <div className="grid gap-3 text-xs md:grid-cols-3">
                <div>
                  <div className="font-medium text-slate-900">专家职责</div>
                  <ul className="mt-1 space-y-1 text-slate-600">{(parseJsonObject<AgentScope>(scope, generatedScope).responsibilities ?? []).map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
                <div>
                  <div className="font-medium text-slate-900">适合回答的问题</div>
                  <ul className="mt-1 space-y-1 text-slate-600">{(parseJsonObject<AgentScope>(scope, generatedScope).suitable_questions ?? []).map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
                <div>
                  <div className="font-medium text-slate-900">回答边界</div>
                  <ul className="mt-1 space-y-1 text-slate-600">{(parseJsonObject<AgentScope>(scope, generatedScope).answer_boundaries ?? []).map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
              </div>
              <textarea
                value={scope}
                onChange={(event) => setScope(event.target.value)}
                placeholder="点击生成专家配置后，会在这里看到知识范围 JSON"
                className="mt-4 min-h-32 w-full rounded-xl border border-slate-200 bg-white p-3 font-mono text-xs text-slate-800 outline-none transition focus:border-blue-300"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={async () => {
                  try {
                    if (!name.trim() || !domain.trim()) {
                      alert('请先填写专家名称和知识领域，或点击生成专家配置');
                      return;
                    }
                    const nextScope = scope.trim() || JSON.stringify(generatedScope, null, 2);
                    setCreating(true);
                    const created = await createAgent({
                      name: name.trim(),
                      description: desc.trim() || undefined,
                      knowledge_domain: domain.trim(),
                      knowledge_scope_json: nextScope,
                      skills_json: JSON.stringify(DEFAULT_AGENT_SKILLS),
                      model_name: 'deepseek',
                      prompt_version: 'v1',
                      status: 'active',
                    });
                    await load();
                    const agentId = created?.data?.agent_id;
                    if (agentId) {
                      setSelectedAgentId(agentId);
                      setQuery(name.trim() || domain.trim());
                    }
                    alert('创建成功。你可以在右下角 AI 问答助手中选择这个专家进行对话。');
                  } catch (error) {
                    alert(error instanceof Error ? error.message : '创建失败');
                  } finally {
                    setCreating(false);
                  }
                }}
                disabled={creating || !name.trim() || !domain.trim()}
              >
                {creating ? '创建中...' : '创建专家助手'}
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
            <CardTitle className="flex items-center gap-2 text-base text-[color:var(--text)]"><BookMarked size={16} /> 专家助手列表</CardTitle>
            <CardDescription className="text-[color:var(--muted)]">每个专家都有绑定知识、启用能力和回答边界，和普通问答助手区分开。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {filteredAgents.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[color:var(--border)] bg-white/70 p-6 text-sm text-[color:var(--muted)]">还没有专家助手。</div>
            ) : (
              filteredAgents.map((agent) => {
                const agentScope = parseJsonObject<AgentScope>(agent.knowledge_scope_json, {});
                const agentSkills = parseSkills(agent.skills_json);
                return (
                  <div key={agent.agent_id} className={`rounded-2xl border p-4 ${selectedAgentId === agent.agent_id ? 'border-blue-300 bg-blue-50/70' : 'border-[color:var(--border)] bg-white/80'}`}>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <div className="text-sm font-semibold text-[color:var(--text)]">{agent.name}</div>
                        <div className="mt-1 text-xs text-slate-600">{agent.knowledge_domain}</div>
                      </div>
                      <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{metadataStatusLabel(agent.status)}</Badge>
                    </div>
                    <div className="mt-2 text-xs text-slate-600">{agent.description || '没有补充说明'}</div>
                    <div className="mt-3 grid gap-3 text-xs md:grid-cols-3">
                      <div className="rounded-xl bg-white p-3">
                        <div className="font-medium text-slate-900">专家职责</div>
                        <div className="mt-1 text-slate-600">{agentScope.responsibilities?.[0] || '围绕绑定知识回答员工问题'}</div>
                      </div>
                      <div className="rounded-xl bg-white p-3">
                        <div className="font-medium text-slate-900">绑定知识</div>
                        <div className="mt-1 text-slate-600">{agentScope.documents?.map((item) => item.title).join('、') || agentScope.document_ids?.join('、') || '暂未限制知识范围'}</div>
                      </div>
                      <div className="rounded-xl bg-white p-3">
                        <div className="font-medium text-slate-900">启用能力</div>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {agentSkills.map((skillId) => <Badge key={skillId} className="bg-blue-50 text-blue-700 hover:bg-blue-50">{skillLabel(skillId, skills)}</Badge>)}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
                      <span className="font-medium text-slate-900">回答边界：</span>
                      {(agentScope.answer_boundaries ?? ['不回答绑定知识范围之外的问题']).join('；')}
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        <Card className="border-[color:var(--border)] bg-[color:var(--surface)] shadow-[0_12px_32px_rgba(15,23,42,0.05)]">
          <CardHeader className="border-b border-[color:var(--border)] pb-4">
            <CardTitle className="flex items-center gap-2 text-base text-[color:var(--text)]"><ArrowRight size={16} /> 知识条目概览</CardTitle>
            <CardDescription className="text-[color:var(--muted)]">选择条目后可以快速生成专家助手，绑定关系会写入专家配置。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-4 text-sm text-[color:var(--muted)]">
            {filteredMetadata.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[color:var(--border)] bg-white/70 p-6 text-sm text-[color:var(--muted)]">暂无相关知识条目。</div>
            ) : (
              filteredMetadata.slice(0, 6).map((item) => (
                <div key={item.knowledge_id} className="rounded-2xl border border-[color:var(--border)] bg-white/80 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-medium text-[color:var(--text)]">{item.title}</div>
                    <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{metadataStatusLabel(item.status)}</Badge>
                  </div>
                  <div className="mt-2 grid gap-2 text-xs md:grid-cols-2">
                    <div>类型：{knowledgeTypeLabel(item.knowledge_type)}</div>
                    <div>来源：{sourceTypeLabel(item.source_type)}</div>
                    <div className="truncate">文档：{item.document_id}</div>
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
