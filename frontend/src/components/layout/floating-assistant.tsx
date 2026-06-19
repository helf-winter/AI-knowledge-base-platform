'use client';

import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Bot, CheckCircle2, GripVertical, SendHorizonal, Sparkles, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type StreamState = {
  answer: string;
  traceId: string;
  sources: SourceDocument[];
  error?: string | null;
  mode?: string | null;
  canExpand?: boolean;
  expansionQuestion?: string | null;
  activeAgentId?: string | null;
  activeAgentName?: string | null;
  activeAgentReason?: string | null;
  activeAgentSkills?: string[];
};

type SourceDocument = {
  source_number?: number;
  document_id: string;
  file_name: string;
};

type ExpandResult = {
  document_id: string;
  knowledge_id?: string | null;
  action: string;
  title: string;
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  query?: string;
  answer?: string;
  traceId?: string;
  sources?: SourceDocument[];
  mode?: string | null;
  canExpand?: boolean;
  expansionQuestion?: string | null;
  activeAgentId?: string | null;
  activeAgentName?: string | null;
  activeAgentReason?: string | null;
  activeAgentSkills?: string[];
  expandDismissed?: boolean;
  expandResult?: ExpandResult | null;
  error?: string | null;
};

type ExpertAgentOption = {
  agent_id: string;
  name: string;
  knowledge_domain: string;
  status: string;
};

const STORAGE_KEY_PREFIX = 'kb_floating_assistant_messages';
const SESSION_KEY_PREFIX = 'kb_floating_assistant_session';

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

function getAssistantSessionId(userId: string) {
  const key = `${SESSION_KEY_PREFIX}:${userId}`;
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const next = crypto.randomUUID();
  localStorage.setItem(key, next);
  return next;
}

function getAssistantMessagesKey(userId: string) {
  return `${STORAGE_KEY_PREFIX}:${userId}`;
}

async function streamAnswer(query: string, agentId: string | null, sessionId: string, onUpdate: (state: StreamState) => void) {
  const token = getToken();
  const userId = getCurrentUserId() || 'anonymous';
  const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ query, user_id: userId, session_id: sessionId, agent_id: agentId || undefined }),
  });
  if (!res.ok || !res.body) throw new Error('问答失败');

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let answer = '';
  let traceId = '';
  let sources: SourceDocument[] = [];
  let error: string | null = null;
  let mode: string | null = null;
  let canExpand = false;
  let expansionQuestion: string | null = null;
  let activeAgentId: string | null = null;
  let activeAgentName: string | null = null;
  let activeAgentReason: string | null = null;
  let activeAgentSkills: string[] = [];
  const emit = () => onUpdate({ answer, traceId, sources, error, mode, canExpand, expansionQuestion, activeAgentId, activeAgentName, activeAgentReason, activeAgentSkills });

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith('data:')) continue;
      const payload = line.replace(/^data:\s*/, '');
      if (payload.startsWith('[TRACE_ID]')) {
        traceId = payload.replace('[TRACE_ID]', '').trim();
        emit();
        continue;
      }
      try {
        const meta = JSON.parse(payload) as {
          delta?: string;
          trace_id?: string;
          error?: string;
          mode?: string;
          can_expand?: boolean;
          expansion_question?: string | null;
          sources?: SourceDocument[];
          active_agent_id?: string | null;
          active_agent_name?: string | null;
          active_agent_reason?: string | null;
          active_agent_skills?: string[];
          recommended_agent_id?: string | null;
          recommended_agent_name?: string | null;
          recommended_reason?: string | null;
        };
        if (typeof meta.delta === 'string') {
          answer += meta.delta;
          emit();
          continue;
        }
        if (Array.isArray(meta.sources)) {
          sources = meta.sources;
          emit();
          if (!meta.trace_id) continue;
        }
        if (meta?.trace_id) {
          traceId = meta.trace_id;
          error = meta.error ?? error;
          mode = meta.mode ?? mode;
          canExpand = Boolean(meta.can_expand);
          expansionQuestion = meta.expansion_question ?? expansionQuestion;
          if (Array.isArray(meta.sources)) sources = meta.sources;
          activeAgentId = meta.active_agent_id ?? meta.recommended_agent_id ?? activeAgentId;
          activeAgentName = meta.active_agent_name ?? meta.recommended_agent_name ?? activeAgentName;
          activeAgentReason = meta.active_agent_reason ?? meta.recommended_reason ?? activeAgentReason;
          activeAgentSkills = Array.isArray(meta.active_agent_skills) ? meta.active_agent_skills : activeAgentSkills;
          emit();
          continue;
        }
      } catch {}
      answer += payload;
      emit();
    }
  }
}

async function fetchExpertAgents() {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/v1/admin/expert-agents`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) return [];
  const json = await res.json();
  return (json.data ?? []) as ExpertAgentOption[];
}

async function expandKnowledge(query: string, answer: string, traceId: string, targetDocumentId?: string) {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/v1/knowledge/expand`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ query, answer, trace_id: traceId || undefined, target_document_id: targetDocumentId }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || '扩充知识失败');
  }
  const json = await res.json();
  return json.data as ExpandResult;
}

function modeLabel(mode?: string | null) {
  if (mode === 'knowledge') return '知识库回答';
  if (mode === 'auto_general') return '已自动切换通用回答';
  return '自动问答';
}

function inlineMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index} className="font-semibold text-slate-950">{part.slice(2, -2)}</strong>;
    }
    return <span key={index}>{part}</span>;
  });
}

function renderMarkdown(text: string) {
  const lines = text.split('\n');
  const nodes: ReactNode[] = [];
  let listItems: ReactNode[] = [];

  const flushList = () => {
    if (listItems.length) {
      nodes.push(<ul key={`ul-${nodes.length}`} className="my-2 list-disc space-y-1 pl-5">{listItems}</ul>);
      listItems = [];
    }
  };

  lines.forEach((raw, index) => {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flushList();
      nodes.push(<div key={`br-${index}`} className="h-2" />);
      return;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushList();
      const size = heading[1].length === 1 ? 'text-base' : 'text-sm';
      nodes.push(<div key={`h-${index}`} className={`${size} mt-2 font-semibold text-slate-950`}>{inlineMarkdown(heading[2])}</div>);
      return;
    }
    const bullet = line.match(/^[-*]\s+(.+)$/);
    const ordered = line.match(/^\d+[.)]\s+(.+)$/);
    if (bullet || ordered) {
      listItems.push(<li key={`li-${index}`}>{inlineMarkdown((bullet || ordered)?.[1] || line)}</li>);
      return;
    }
    flushList();
    nodes.push(<p key={`p-${index}`} className="my-1">{inlineMarkdown(line)}</p>);
  });
  flushList();
  return nodes;
}

export function FloatingAssistant() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [expanding, setExpanding] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [agents, setAgents] = useState<ExpertAgentOption[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [launcherPosition, setLauncherPosition] = useState({ x: 0, y: 0 });
  const [panelPosition, setPanelPosition] = useState({ x: 0, y: 0 });
  const [panelSize, setPanelSize] = useState({ width: 420, height: 640 });
  const [draggingLauncher, setDraggingLauncher] = useState(false);
  const [draggingPanel, setDraggingPanel] = useState(false);
  const openRef = useRef(open);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const suppressLauncherClick = useRef(false);
  const launcherDragState = useRef<{ startX: number; startY: number; baseX: number; baseY: number; moved: boolean } | null>(null);
  const panelDragState = useRef<{ startX: number; startY: number; baseX: number; baseY: number } | null>(null);

  useEffect(() => {
    openRef.current = open;
  }, [open]);

  useEffect(() => {
    setLauncherPosition({ x: Math.max(16, window.innerWidth - 140), y: Math.max(16, window.innerHeight - 92) });
    setPanelPosition({ x: Math.max(16, window.innerWidth - 452), y: 24 });
    try {
      const raw = localStorage.getItem(getAssistantMessagesKey(getCurrentUserId() || 'anonymous'));
      if (raw) setMessages(JSON.parse(raw) as ChatMessage[]);
    } catch {}
    void fetchExpertAgents().then((items) => setAgents(items.filter((item) => item.status === 'active'))).catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(getAssistantMessagesKey(getCurrentUserId() || 'anonymous'), JSON.stringify(messages.slice(-20)));
    } catch {}
  }, [messages]);

  useEffect(() => {
    const onResize = () => {
      setLauncherPosition((current) => ({
        x: Math.min(Math.max(16, current.x), Math.max(16, window.innerWidth - 140)),
        y: Math.min(Math.max(16, current.y), Math.max(16, window.innerHeight - 92)),
      }));
      setPanelPosition((current) => ({
        x: Math.min(Math.max(16, current.x), Math.max(16, window.innerWidth - panelSize.width - 16)),
        y: Math.min(Math.max(16, current.y), Math.max(16, window.innerHeight - panelSize.height - 16)),
      }));
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [panelSize.height, panelSize.width]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    const onMove = (event: PointerEvent) => {
      if (launcherDragState.current) {
        const deltaX = event.clientX - launcherDragState.current.startX;
        const deltaY = event.clientY - launcherDragState.current.startY;
        if (Math.hypot(deltaX, deltaY) > 5) launcherDragState.current.moved = true;
        const nextX = Math.min(Math.max(12, launcherDragState.current.baseX + deltaX), Math.max(12, window.innerWidth - 120));
        const nextY = Math.min(Math.max(12, launcherDragState.current.baseY + deltaY), Math.max(12, window.innerHeight - 72));
        setLauncherPosition({ x: nextX, y: nextY });
      }
      if (panelDragState.current) {
        const nextX = Math.min(Math.max(12, panelDragState.current.baseX + (event.clientX - panelDragState.current.startX)), Math.max(12, window.innerWidth - panelSize.width - 16));
        const nextY = Math.min(Math.max(12, panelDragState.current.baseY + (event.clientY - panelDragState.current.startY)), Math.max(12, window.innerHeight - panelSize.height - 16));
        setPanelPosition({ x: nextX, y: nextY });
      }
    };
    const onUp = () => {
      if (launcherDragState.current?.moved) {
        suppressLauncherClick.current = true;
        window.setTimeout(() => {
          suppressLauncherClick.current = false;
        }, 160);
      }
      launcherDragState.current = null;
      panelDragState.current = null;
      setDraggingLauncher(false);
      setDraggingPanel(false);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [panelSize.height, panelSize.width]);

  useEffect(() => {
    if (!open || !panelRef.current) return;
    const observer = new ResizeObserver(([entry]) => {
      const rect = entry.contentRect;
      setPanelSize({
        width: Math.min(Math.max(360, Math.round(rect.width)), Math.max(360, window.innerWidth - 24)),
        height: Math.min(Math.max(480, Math.round(rect.height)), Math.max(480, window.innerHeight - 24)),
      });
    });
    observer.observe(panelRef.current);
    return () => observer.disconnect();
  }, [open]);

  const updateMessage = (id: string, patch: Partial<ChatMessage>) => {
    setMessages((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)).slice(-20));
  };

  const notifyDone = () => {
    if (openRef.current) return;
    setNotice('AI 回答完成，点击查看');
    window.setTimeout(() => setNotice(null), 4200);
  };

  const handleSend = async () => {
    try {
      setLoading(true);
      const cleanQuery = query.trim();
      const sessionId = getAssistantSessionId(getCurrentUserId() || 'anonymous');
      const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', query: cleanQuery };
      const assistantId = crypto.randomUUID();
      const assistantMessage: ChatMessage = { id: assistantId, role: 'assistant', query: cleanQuery, answer: '', sources: [] };
      setMessages((current) => [...current, userMessage, assistantMessage].slice(-20));
      setQuery('');
      await streamAnswer(cleanQuery, selectedAgentId || null, sessionId, (state) => {
        updateMessage(assistantId, {
          answer: state.answer,
          error: state.error ?? '',
          traceId: state.traceId,
          sources: state.sources,
          mode: state.mode ?? null,
          activeAgentId: state.activeAgentId ?? null,
          activeAgentName: state.activeAgentName ?? null,
          activeAgentReason: state.activeAgentReason ?? null,
          activeAgentSkills: state.activeAgentSkills ?? [],
          canExpand: Boolean(state.canExpand),
          expansionQuestion: state.expansionQuestion ?? null,
        });
      });
      notifyDone();
    } catch (error) {
      alert(error instanceof Error ? error.message : '问答失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => {
          if (suppressLauncherClick.current) return;
          setOpen(true);
          setNotice(null);
        }}
        onPointerDown={(event) => {
          event.preventDefault();
          setDraggingLauncher(true);
          launcherDragState.current = {
            startX: event.clientX,
            startY: event.clientY,
            baseX: launcherPosition.x,
            baseY: launcherPosition.y,
            moved: false,
          };
        }}
        className="fixed z-50 inline-flex items-center gap-2 rounded-full bg-blue-600 px-4 py-3 text-sm font-medium text-white shadow-[0_16px_40px_rgba(37,99,235,0.35)] transition hover:bg-blue-700"
        style={{ left: launcherPosition.x, top: launcherPosition.y, cursor: draggingLauncher ? 'grabbing' : 'grab' }}
      >
        <Bot size={16} /> AI 问答助手
      </button>

      {open ? (
        <div
          ref={panelRef}
          className="fixed z-[60] resize overflow-hidden rounded-2xl"
          style={{
            left: panelPosition.x,
            top: panelPosition.y,
            width: `min(${panelSize.width}px, calc(100vw - 24px))`,
            height: `min(${panelSize.height}px, calc(100vh - 24px))`,
            minWidth: 360,
            minHeight: 480,
            maxWidth: 'calc(100vw - 24px)',
            maxHeight: 'calc(100vh - 24px)',
          }}
        >
          <Card className="flex h-full flex-col overflow-hidden border-slate-200 bg-white shadow-[0_20px_60px_rgba(15,23,42,0.18)]">
            <CardHeader
              className="cursor-grab select-none border-b border-slate-100 pb-3"
              onPointerDown={(event) => {
                event.preventDefault();
                setDraggingPanel(true);
                panelDragState.current = {
                  startX: event.clientX,
                  startY: event.clientY,
                  baseX: panelPosition.x,
                  baseY: panelPosition.y,
                };
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2 text-base text-slate-950"><Sparkles size={16} /> AI 问答助手</CardTitle>
                  <CardDescription className="text-slate-600">自动优先查知识库，答不上时切换通用回答。</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <GripVertical size={16} className={draggingPanel ? 'text-blue-600' : 'text-slate-400'} />
                  <button type="button" onPointerDown={(event) => event.stopPropagation()} onClick={() => setOpen(false)} className="rounded-full border border-slate-200 bg-white p-2 text-slate-500 hover:text-slate-950">
                    <X size={16} />
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="min-h-0 flex-1 space-y-4 overflow-y-auto pt-4">
              <div className="rounded-2xl border border-blue-100 bg-blue-50 p-3 text-xs leading-5 text-blue-900">
                当前为自动问答：系统会先尝试知识库专家回答；如果知识不足，会自动切换为通用回答，并允许你一键扩充知识库。
              </div>

              <div className="max-h-[min(22rem,45vh)] space-y-3 overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                {messages.length === 0 ? (
                  <div className="text-sm text-slate-500">还没有会话。发送一个问题后，历史问答会像聊天一样保留在这里。</div>
                ) : (
                  messages.map((message) => (
                    <div key={message.id} className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                      {message.role === 'user' ? (
                        <div className="max-w-[85%] rounded-2xl bg-blue-600 px-3 py-2 text-sm leading-6 text-white">
                          {message.query}
                        </div>
                      ) : (
                        <div className="max-w-[95%] space-y-2 rounded-2xl border border-slate-200 bg-white p-3 text-sm leading-6 text-slate-900">
                          <div className="space-y-1">{message.answer ? renderMarkdown(message.answer) : '回答中...'}</div>
                          {message.error ? <div className="rounded-xl border border-red-200 bg-red-50 p-2 text-xs text-red-700">{message.error}</div> : null}
                          <div className="space-y-2 rounded-xl bg-slate-50 p-2 text-xs text-slate-600">
                            <div>Trace ID：{message.traceId || '-'}</div>
                            <div>回答模式：{modeLabel(message.mode)}</div>
                            <div>使用专家：{message.activeAgentName || (selectedAgentId ? '指定专家匹配失败' : '自动路由')}</div>
                            {message.activeAgentReason ? <div>选择原因：{message.activeAgentReason}</div> : null}
                            {message.activeAgentSkills?.length ? <div>启用能力：{message.activeAgentSkills.join('、')}</div> : null}
                            <div className="flex flex-wrap gap-2">
                              {message.sources?.length ? message.sources.map((source) => (
                                <a
                                  key={source.document_id}
                                  href={`/documents/${source.document_id}?highlight=${encodeURIComponent(message.query || query.trim())}`}
                                  className="rounded-full bg-white px-2 py-1 text-blue-700 transition hover:bg-blue-50 hover:text-blue-800"
                                >
                                  {source.source_number ? `[${source.source_number}] ` : ''}{source.file_name}
                                </a>
                              )) : '暂无来源文档'}
                            </div>
                          </div>

                          {message.canExpand && message.answer && !message.expandDismissed && !message.expandResult ? (
                            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-950">
                              <div className="font-medium">{message.expansionQuestion || '是否扩充该知识内容？'}</div>
                              <div className="mt-1 text-amber-800">扩充后会整理为知识片段，优先追加到最相近知识库；没有相近内容时创建新的知识库文档。</div>
                              <div className="mt-3 flex gap-2">
                                <Button size="sm" variant="outline" onClick={() => updateMessage(message.id, { expandDismissed: true })}>暂不</Button>
                                <Button
                                  size="sm"
                                  disabled={expanding}
                                  onClick={async () => {
                                    try {
                                      setExpanding(true);
                                      const result = await expandKnowledge(message.query || '', message.answer || '', message.traceId || '', message.sources?.[0]?.document_id);
                                      updateMessage(message.id, { expandResult: result });
                                    } catch (error) {
                                      alert(error instanceof Error ? error.message : '扩充失败');
                                    } finally {
                                      setExpanding(false);
                                    }
                                  }}
                                >
                                  {expanding ? '扩充中...' : '扩充'}
                                </Button>
                              </div>
                            </div>
                          ) : null}

                          {message.expandResult ? (
                            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs leading-5 text-emerald-800">
                              <div className="flex items-center gap-2 font-medium text-emerald-900"><CheckCircle2 size={14} /> 知识已扩充</div>
                              <div className="mt-1">处理方式：{message.expandResult.action === 'append' ? '追加到相近知识库' : '创建新知识库'}</div>
                              <div>知识库：{message.expandResult.title}</div>
                              <div>文档 ID：{message.expandResult.document_id}</div>
                            </div>
                          ) : null}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              <div className="grid gap-2 md:grid-cols-[1fr_auto]">
                <select
                  value={selectedAgentId}
                  onChange={(event) => setSelectedAgentId(event.target.value)}
                  className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-blue-300"
                >
                  <option value="">自动选择专家</option>
                  {agents.map((agent) => (
                    <option key={agent.agent_id} value={agent.agent_id}>{agent.name}（{agent.knowledge_domain}）</option>
                  ))}
                </select>
                <Button type="button" variant="outline" onClick={() => void fetchExpertAgents().then((items) => setAgents(items.filter((item) => item.status === 'active')))}>
                  刷新专家
                </Button>
              </div>

              <Textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="例如：公司 VPN 怎么申请？"
                className="min-h-24 border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
              />
              <div className="flex gap-2">
                <Button
                  onClick={handleSend}
                  disabled={!query || loading}
                  className="flex-1"
                >
                  <SendHorizonal size={16} /> {loading ? '回答中...' : '发送'}
                </Button>
                <Button variant="outline" onClick={() => { setQuery(''); setMessages([]); localStorage.removeItem(getAssistantMessagesKey(getCurrentUserId() || 'anonymous')); }}>
                  清空会话
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {notice ? (
        <button
          type="button"
          onClick={() => {
            setOpen(true);
            setNotice(null);
          }}
          className="fixed bottom-6 right-6 z-[70] rounded-2xl border border-blue-200 bg-white px-4 py-3 text-sm font-medium text-slate-900 shadow-[0_16px_40px_rgba(15,23,42,0.18)] transition hover:border-blue-300 hover:bg-blue-50"
        >
          {notice}
        </button>
      ) : null}
    </>
  );
}
