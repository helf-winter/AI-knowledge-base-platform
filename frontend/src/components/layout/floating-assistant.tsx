'use client';

import { useEffect, useRef, useState } from 'react';
import { Bot, X, SendHorizonal, Sparkles, GripVertical, RefreshCw, WandSparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

type StreamState = {
  answer: string;
  traceId: string;
  refs: string[];
  recommendedAgentId?: string | null;
  recommendedAgentName?: string | null;
  recommendedReason?: string | null;
};

async function fetchAgents() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('kb_token') : null;
  const res = await fetch(`${API_BASE}/api/v1/admin/expert-agents`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) return [];
  const json = await res.json();
  return (json.data ?? []) as Array<{ agent_id: string; name: string; knowledge_domain: string; skills_json?: string | null }>;
}

function skillLabel(skillId: string) {
  const map: Record<string, string> = {
    knowledge_search: '知识检索',
    knowledge_extract: '知识抽取',
    knowledge_compare: '知识对比',
    document_summarize: '文档总结',
  };
  return map[skillId] ?? skillId;
}

function parseSkills(skillsJson?: string | null) {
  if (!skillsJson) return ['knowledge_search'];
  try {
    const parsed = JSON.parse(skillsJson);
    return Array.isArray(parsed) ? parsed : ['knowledge_search'];
  } catch {
    return ['knowledge_search'];
  }
}

async function streamAnswer(query: string, onUpdate: (state: StreamState) => void, agentId?: string) {
  const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, user_id: 'demo-user', session_id: 'floating-session', agent_id: agentId }),
  });
  if (!res.ok || !res.body) throw new Error('问答失败');

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let answer = '';
  let traceId = '';
  let refs: string[] = [];
  let recommendedAgentId: string | null = null;
  let recommendedAgentName: string | null = null;
  let recommendedReason: string | null = null;
  const emit = () => onUpdate({ answer, traceId, refs, recommendedAgentId, recommendedAgentName, recommendedReason });

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
      if (payload.startsWith('[TRACE_ID]')) { traceId = payload.replace('[TRACE_ID]', '').trim(); emit(); continue; }
      if (payload.startsWith('[REFS]')) { refs = payload.replace('[REFS]', '').split('|').map((s) => s.trim()).filter(Boolean); emit(); continue; }
      try {
        const meta = JSON.parse(payload) as { trace_id?: string };
        if (meta?.trace_id) {
          traceId = meta.trace_id;
          recommendedAgentId = meta.recommended_agent_id ?? recommendedAgentId;
          recommendedAgentName = meta.recommended_agent_name ?? recommendedAgentName;
          recommendedReason = meta.recommended_reason ?? recommendedReason;
          emit();
          continue;
        }
      } catch {}
      answer += payload;
      emit();
    }
  }
}

export function FloatingAssistant() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [traceId, setTraceId] = useState('');
  const [refs, setRefs] = useState<string[]>([]);
  const [recommendedAgentId, setRecommendedAgentId] = useState<string | null>(null);
  const [recommendedAgentName, setRecommendedAgentName] = useState<string | null>(null);
  const [recommendedReason, setRecommendedReason] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<Array<{ agent_id: string; name: string; knowledge_domain: string; skills_json?: string | null }>>([]);
  const [agentId, setAgentId] = useState('');
  const [launcherPosition, setLauncherPosition] = useState({ x: 0, y: 0 });
  const [panelPosition, setPanelPosition] = useState({ x: 0, y: 0 });
  const [draggingLauncher, setDraggingLauncher] = useState(false);
  const [draggingPanel, setDraggingPanel] = useState(false);
  const launcherDragState = useRef<{ startX: number; startY: number; baseX: number; baseY: number } | null>(null);
  const panelDragState = useRef<{ startX: number; startY: number; baseX: number; baseY: number } | null>(null);

  useEffect(() => {
    const startX = Math.max(24, window.innerWidth - 112);
    const startY = Math.max(24, window.innerHeight - 90);
    setLauncherPosition({ x: startX, y: startY });
    setPanelPosition({ x: Math.max(24, window.innerWidth - 460), y: Math.max(24, window.innerHeight - 560) });
    void fetchAgents().then(setAgents).catch(() => setAgents([]));
  }, []);

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
        const nextX = Math.max(12, launcherDragState.current.baseX + (event.clientX - launcherDragState.current.startX));
        const nextY = Math.max(12, launcherDragState.current.baseY + (event.clientY - launcherDragState.current.startY));
        setLauncherPosition({ x: nextX, y: nextY });
      }
      if (panelDragState.current) {
        const nextX = Math.max(12, panelDragState.current.baseX + (event.clientX - panelDragState.current.startX));
        const nextY = Math.max(12, panelDragState.current.baseY + (event.clientY - panelDragState.current.startY));
        setPanelPosition({ x: nextX, y: nextY });
      }
    };
    const onUp = () => {
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
  }, []);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        onPointerDown={(event) => {
          event.preventDefault();
          setDraggingLauncher(true);
          launcherDragState.current = {
            startX: event.clientX,
            startY: event.clientY,
            baseX: launcherPosition.x,
            baseY: launcherPosition.y,
          };
        }}
        className="fixed z-50 inline-flex items-center gap-2 rounded-full bg-blue-600 px-4 py-3 text-sm font-medium text-white shadow-[0_16px_40px_rgba(37,99,235,0.35)] transition hover:bg-blue-700"
        style={{ left: launcherPosition.x, top: launcherPosition.y, cursor: draggingLauncher ? 'grabbing' : 'grab' }}
      >
        <Bot size={16} /> AI 问答助手
      </button>

      {open ? (
        <div className="fixed z-[60] w-[min(92vw,420px)]" style={{ left: panelPosition.x, top: panelPosition.y }}>
          <Card className="border-slate-200 bg-white shadow-[0_20px_60px_rgba(15,23,42,0.18)]">
            <CardHeader
              className="cursor-grab border-b border-slate-100 pb-3 select-none"
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
                  <CardDescription className="text-slate-600">拖动标题栏可以移动这个浮窗。</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <GripVertical size={16} className={draggingPanel ? 'text-blue-600' : 'text-slate-400'} />
                  <button type="button" onClick={() => setOpen(false)} className="rounded-full border border-slate-200 bg-white p-2 text-slate-500 hover:text-slate-950">
                    <X size={16} />
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-medium text-slate-600">当前助手</div>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-600 transition hover:border-blue-300 hover:text-blue-700"
                    onClick={async () => {
                      setAgents(await fetchAgents());
                    }}
                  >
                    <RefreshCw size={12} /> 刷新
                  </button>
                </div>
                <select
                  value={agentId}
                  onChange={(e) => setAgentId(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500"
                >
                  <option value="">通用问答</option>
                  {agents.map((agent) => (
                    <option key={agent.agent_id} value={agent.agent_id}>
                      {agent.name} · {agent.knowledge_domain}
                    </option>
                  ))}
                </select>
              </div>
              <Textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="例如：公司 VPN 怎么申请？"
                className="min-h-24 border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
              />
              <div className="flex gap-2">
                <Button
                  onClick={async () => {
                    try {
                      setLoading(true);
                      setAnswer('');
                      setTraceId('');
                      setRefs([]);
                      setRecommendedAgentId(null);
                      setRecommendedAgentName(null);
                      setRecommendedReason(null);
                      await streamAnswer(query, (state) => {
                        setAnswer(state.answer);
                        setTraceId(state.traceId);
                        setRefs(state.refs);
                        setRecommendedAgentId(state.recommendedAgentId ?? null);
                        setRecommendedAgentName(state.recommendedAgentName ?? null);
                        setRecommendedReason(state.recommendedReason ?? null);
                      }, agentId || undefined);
                    } catch (error) {
                      alert(error instanceof Error ? error.message : '问答失败');
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={!query || loading}
                  className="flex-1"
                >
                  <SendHorizonal size={16} /> {loading ? '回答中...' : '发送'}
                </Button>
                <Button variant="outline" onClick={() => { setQuery(''); setAnswer(''); setTraceId(''); setRefs([]); }}>
                  清空
                </Button>
              </div>
              <div className="space-y-2 rounded-2xl bg-slate-50 p-3 text-xs text-slate-600">
                <div>Trace ID：{traceId || '-'}</div>
                <div className="flex flex-wrap gap-2">{refs.length ? refs.map((ref) => <span key={ref} className="rounded-full bg-white px-2 py-1 text-slate-700">{ref}</span>) : '暂无引用'}</div>
              </div>
              {!agentId ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-3 text-xs text-slate-500">
                  通用问答会先帮你处理常规问题。如果更适合业务场景，我们会推荐合适的助手。
                </div>
              ) : null}
              {!agentId && recommendedAgentName ? (
                <div className="rounded-2xl border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
                  <div className="font-medium">建议你试试：{recommendedAgentName}</div>
                  <div className="mt-1 leading-5">{recommendedReason}</div>
                  <button
                    type="button"
                    className="mt-3 inline-flex items-center rounded-full bg-blue-600 px-3 py-1 text-white transition hover:bg-blue-700"
                    onClick={() => setAgentId(recommendedAgentId ?? '')}
                  >
                    切换到该助手
                  </button>
                </div>
              ) : null}
              {agentId ? (
                <div className="space-y-2 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                  <div>当前已选择专家助手，回答会尽量按该助手的知识域与能力来处理。</div>
                  <div className="flex flex-wrap gap-2">
                    {parseSkills(agents.find((agent) => agent.agent_id === agentId)?.skills_json).map((skillId: string) => (
                      <span key={skillId} className="rounded-full bg-white px-2 py-1 text-slate-700">{skillLabel(skillId)}</span>
                    ))}
                  </div>
                </div>
              ) : null}
              <div className="max-h-40 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-900">
                {answer || '回答会显示在这里。'}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </>
  );
}
