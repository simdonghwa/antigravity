'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  Bot, User, Send, Zap, CheckCircle,
  Code, FileText, Settings, Activity, ChevronRight,
  ThumbsUp, ThumbsDown, RotateCcw, Terminal, AlertCircle,
  Download, History, Plus, X,
} from 'lucide-react';
import styles from './ax.module.css';

// Mermaid는 브라우저 전용이므로 dynamic import (SSR 비활성화)
const MermaidChart = dynamic(() => import('@/components/common/MermaidChart'), { ssr: false });

// ── 상수 ────────────────────────────────────────────────────
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const WS_BASE  = API_BASE.replace(/^http/, 'ws');

const PIPELINE_STAGES = [
  { id: 'interview',     label: '인터뷰',   icon: '💬' },
  { id: 'decompose',     label: '분해',      icon: '🔬' },
  { id: 'ax_review',    label: 'AX 분석',  icon: '📊' },
  { id: 'architect',    label: '설계',      icon: '🏗️' },
  { id: 'tool_map',     label: '도구',      icon: '🔧' },
  { id: 'code_gen',     label: '코드',      icon: '💻' },
  { id: 'verify',       label: '검증',      icon: '✅' },
  { id: 'human_approve', label: '승인',     icon: '👤' },
  { id: 'complete',     label: '완료',      icon: '🎉' },
];

type Role = 'user' | 'agent' | 'system';

interface ChatMessage {
  id: string;
  role: Role;
  agent_name: string;
  content: string;
  metadata?: Record<string, unknown>;
  timestamp: string;
}

interface StreamEvent {
  event_type: string;
  agent_name: string;
  stage: string;
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

interface Artifact {
  id: string;
  artifact_type: string;
  name: string;
  content: Record<string, unknown>;
  version: number;
}

interface SessionInfo {
  projectId: string;
  sessionId: string;
}

interface SessionListItem {
  id: string;
  project_id: string;
  current_stage: string;
  created_at: string;
  updated_at: string;
}

// ── 유틸 ────────────────────────────────────────────────────

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function genId() {
  return Math.random().toString(36).slice(2);
}

function getStageIndex(stage: string) {
  return PIPELINE_STAGES.findIndex(s => s.id === stage);
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────

export default function AxPage() {
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [initError, setInitError] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [events,   setEvents]   = useState<StreamEvent[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);

  const [currentStage, setCurrentStage] = useState('interview');
  const [inputText, setInputText]  = useState('');
  const [isSending, setIsSending]  = useState(false);
  const [activeArtifact, setActiveArtifact] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'chat' | 'events'>('chat');
  const [showHistory, setShowHistory] = useState(false);
  const [sessionList, setSessionList] = useState<SessionListItem[]>([]);

  const wsRef      = useRef<WebSocket | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const eventEndRef = useRef<HTMLDivElement | null>(null);

  // 스크롤 자동 내리기
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => { eventEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [events]);

  // ── 세션 목록 로드 ───────────────────────────────────────
  const loadSessionList = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions?limit=20`);
      if (res.ok) setSessionList(await res.json());
    } catch { /* 무시 */ }
  }, []);

  // ── 세션 재개 ────────────────────────────────────────────
  const resumeSession = useCallback((item: SessionListItem) => {
    wsRef.current?.close();
    setMessages([]);
    setEvents([]);
    setArtifacts([]);
    setCurrentStage(item.current_stage ?? 'interview');
    setSession({ projectId: item.project_id, sessionId: item.id });
    setShowHistory(false);
  }, []);

  // ── 새 세션 시작 ─────────────────────────────────────────
  const startNewSession = useCallback(async () => {
    setShowHistory(false);
    wsRef.current?.close();
    setMessages([]);
    setEvents([]);
    setArtifacts([]);
    setSession(null);
    setInitError(null);
    try {
      const projRes = await fetch(`${API_BASE}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: `AX Session ${new Date().toLocaleString('ko-KR')}`, description: '' }),
      });
      if (!projRes.ok) throw new Error(`Project create failed: ${projRes.status}`);
      const proj = await projRes.json();
      const sessRes = await fetch(`${API_BASE}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: proj.id }),
      });
      if (!sessRes.ok) throw new Error(`Session create failed: ${sessRes.status}`);
      const sess = await sessRes.json();
      setSession({ projectId: proj.id, sessionId: sess.id });
    } catch (e: unknown) {
      setInitError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  // ── 세션 초기화 ─────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        // 1. 프로젝트 생성
        const projRes = await fetch(`${API_BASE}/api/projects`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: `AX Session ${new Date().toLocaleString('ko-KR')}`, description: '' }),
        });
        if (!projRes.ok) throw new Error(`Project create failed: ${projRes.status}`);
        const proj = await projRes.json();

        // 2. 세션 생성
        const sessRes = await fetch(`${API_BASE}/api/sessions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_id: proj.id }),
        });
        if (!sessRes.ok) throw new Error(`Session create failed: ${sessRes.status}`);
        const sess = await sessRes.json();

        setSession({ projectId: proj.id, sessionId: sess.id });
      } catch (e: unknown) {
        setInitError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, []);

  // ── WebSocket 연결 ──────────────────────────────────────
  useEffect(() => {
    if (!session) return;
    const { sessionId } = session;

    setWsStatus('connecting');
    const ws = new WebSocket(`${WS_BASE}/api/ws/${sessionId}`);
    wsRef.current = ws;

    // 핑 인터벌
    const pingTimer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping', session_id: sessionId, content: '' }));
      }
    }, 20000);

    ws.onopen = () => setWsStatus('connected');

    ws.onmessage = (ev) => {
      let data: StreamEvent;
      try { data = JSON.parse(ev.data); } catch { return; }

      const { event_type, content, metadata } = data;

      if (event_type === 'pong' || event_type === 'connected') {
        if (event_type === 'connected') {
          // 서버에서 현재 stage 정보 반영
          const stage = (data as StreamEvent & { stage: string }).stage;
          if (stage) setCurrentStage(stage);
        }
        return;
      }

      // 스트림 이벤트 로그
      setEvents(prev => [...prev.slice(-199), data]);

      // 에이전트 출력 → 채팅 메시지
      if (event_type === 'agent_output' || event_type === 'user_input_required') {
        const msg: ChatMessage = {
          id: genId(),
          role: 'agent',
          agent_name: data.agent_name,
          content: typeof content === 'string' ? content : JSON.stringify(content),
          metadata: metadata ?? {},
          timestamp: data.timestamp ?? new Date().toISOString(),
        };
        setMessages(prev => [...prev, msg]);
      }

      // 파이프라인 스테이지 변경
      if (event_type === 'pipeline_advance' || event_type === 'agent_start') {
        if (data.stage) setCurrentStage(data.stage);
      }

      if (event_type === 'pipeline_complete') {
        setCurrentStage('complete');
        // 아티팩트 갱신
        fetchArtifacts(sessionId);
      }
    };

    ws.onerror = () => setWsStatus('disconnected');
    ws.onclose = () => {
      setWsStatus('disconnected');
      clearInterval(pingTimer);
    };

    return () => {
      clearInterval(pingTimer);
      ws.close();
    };
  }, [session]);

  // ── 아티팩트 로드 ───────────────────────────────────────
  const fetchArtifacts = useCallback(async (sessionId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/artifacts`);
      if (res.ok) {
        const data = await res.json();
        setArtifacts(data);
        if (data.length > 0 && !activeArtifact) {
          setActiveArtifact(data[0].artifact_type);
        }
      }
    } catch { /* silent */ }
  }, [activeArtifact]);

  // 주기적 아티팩트 갱신
  useEffect(() => {
    if (!session) return;
    const timer = setInterval(() => fetchArtifacts(session.sessionId), 8000);
    return () => clearInterval(timer);
  }, [session, fetchArtifacts]);

  // ── 메시지 전송 ─────────────────────────────────────────
  const sendMessage = useCallback((content: string, selectedOption?: string) => {
    if (!session || !content.trim() || wsStatus !== 'connected') return;

    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    const userMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      agent_name: 'User',
      content: selectedOption ?? content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    setIsSending(true);
    ws.send(JSON.stringify({
      type: 'chat',
      session_id: session.sessionId,
      content: selectedOption ?? content,
      selected_option: selectedOption ?? null,
    }));
    setInputText('');

    // 전송 후 로딩 표시 (응답 오면 자동 해제)
    setTimeout(() => setIsSending(false), 500);
  }, [session, wsStatus]);

  const handleSendApproval = useCallback((approved: boolean, feedback = '') => {
    if (!session || wsStatus !== 'connected') return;
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(JSON.stringify({
      type: 'approval',
      session_id: session.sessionId,
      content: approved ? '승인' : '거절',
      approved,
      feedback,
    }));

    const sysMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      agent_name: 'User',
      content: approved ? '✅ 승인합니다' : '❌ 거절합니다',
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, sysMsg]);
  }, [session, wsStatus]);

  // ── 마지막 메시지의 options 추출 ─────────────────────────
  const lastAgentMsg = [...messages].reverse().find(m => m.role === 'agent');
  const options: string[] = (lastAgentMsg?.metadata?.options as string[]) ?? [];
  const requiresApproval = !!(lastAgentMsg?.metadata?.requires_approval);
  const completionPct = (lastAgentMsg?.metadata?.completion_pct as number) ?? 0;

  // ── 이벤트 타입 색상 ─────────────────────────────────────
  function eventColor(type: string) {
    if (type.includes('error')) return styles.eventError;
    if (type.includes('complete')) return styles.eventComplete;
    if (type.includes('start')) return styles.eventStart;
    if (type.includes('advance')) return styles.eventAdvance;
    return styles.eventDefault;
  }

  const stageIdx     = getStageIndex(currentStage);
  const selectedArt  = artifacts.find(a => a.artifact_type === activeArtifact);

  // ── 초기화 오류 화면 ─────────────────────────────────────
  if (initError) {
    return (
      <div className={styles.errorScreen}>
        <AlertCircle size={48} color="var(--color-accent-alert)" />
        <h2>서버 연결 실패</h2>
        <p>{initError}</p>
        <p className={styles.errorHint}>백엔드 서버가 실행 중인지 확인하세요:<br />
          <code>PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe run.py</code>
        </p>
        <button className={styles.retryBtn} onClick={() => window.location.reload()}>
          <RotateCcw size={16} /> 다시 시도
        </button>
      </div>
    );
  }

  // ── 로딩 화면 ───────────────────────────────────────────
  if (!session) {
    return (
      <div className={styles.loadingScreen}>
        <div className={styles.loadingSpinner} />
        <p>세션 초기화 중...</p>
      </div>
    );
  }

  // ── 메인 UI ─────────────────────────────────────────────
  return (
    <div className={styles.container}>
      {/* ── 헤더 ── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <Zap size={22} className={styles.logoIcon} />
          <span className={styles.logoText}>SMALL AX AGENT</span>
          <span className={styles.sessionBadge}>#{session.sessionId.slice(0, 8)}</span>
        </div>
        <div className={styles.headerCenter}>
          <PipelineBar stages={PIPELINE_STAGES} currentIdx={stageIdx} />
        </div>
        <div className={styles.headerRight}>
          <button
            className={styles.historyBtn}
            onClick={() => { setShowHistory(h => !h); loadSessionList(); }}
            title="세션 기록"
          >
            <History size={16} />
          </button>
          <button className={styles.newSessionBtn} onClick={startNewSession} title="새 세션">
            <Plus size={16} />
          </button>
          <span className={`${styles.wsBadge} ${wsStatus === 'connected' ? styles.wsConnected : styles.wsDisconnected}`}>
            <span className={styles.wsDot} />
            {wsStatus === 'connected' ? 'LIVE' : wsStatus === 'connecting' ? '연결 중' : '오프라인'}
          </span>
        </div>
      </header>

      {/* ── 세션 히스토리 패널 ── */}
      {showHistory && (
        <div className={styles.historyOverlay} onClick={() => setShowHistory(false)}>
          <div className={styles.historyPanel} onClick={e => e.stopPropagation()}>
            <div className={styles.historyHeader}>
              <span>최근 세션</span>
              <button className={styles.historyClose} onClick={() => setShowHistory(false)}><X size={16} /></button>
            </div>
            <div className={styles.historyList}>
              {sessionList.length === 0 && (
                <div className={styles.historyEmpty}>세션 기록이 없습니다</div>
              )}
              {sessionList.map(item => (
                <button
                  key={item.id}
                  className={`${styles.historyItem} ${item.id === session.sessionId ? styles.historyItemActive : ''}`}
                  onClick={() => resumeSession(item)}
                >
                  <div className={styles.historyItemId}>#{item.id.slice(0, 8)}</div>
                  <div className={styles.historyItemMeta}>
                    <span className={styles.historyStage}>{item.current_stage}</span>
                    <span className={styles.historyDate}>
                      {new Date(item.created_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── 인터뷰 진행률 (인터뷰 단계만) ── */}
      {currentStage === 'interview' && completionPct > 0 && (
        <div className={styles.interviewProgress}>
          <div className={styles.interviewBar}>
            <div className={styles.interviewFill} style={{ width: `${completionPct}%` }} />
          </div>
          <span className={styles.interviewLabel}>인터뷰 {completionPct}% 완료</span>
        </div>
      )}

      {/* ── 본문 ── */}
      <div className={styles.body}>
        {/* 채팅 패널 */}
        <section className={styles.chatPanel}>
          <div className={styles.panelHeader}>
            <Bot size={16} />
            <span>AI 에이전트 채팅</span>
          </div>

          <div className={styles.messages}>
            {messages.length === 0 && (
              <div className={styles.emptyChat}>
                <Bot size={36} opacity={0.3} />
                <p>인터뷰 에이전트가 곧 질문을 시작합니다...</p>
                <p className={styles.emptyChatHint}>메시지를 입력하거나 버튼을 선택하여 시작하세요</p>
              </div>
            )}

            {messages.map(msg => (
              <ChatBubble key={msg.id} msg={msg} />
            ))}

            {/* 로딩 버블 */}
            {isSending && (
              <div className={`${styles.bubble} ${styles.agentBubble}`}>
                <div className={styles.bubbleAvatar}><Bot size={14} /></div>
                <div className={styles.bubbleContent}>
                  <div className={styles.typing}>
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* 옵션 버튼 */}
          {options.length > 0 && !requiresApproval && (
            <div className={styles.optionButtons}>
              {options.map((opt, i) => (
                <button
                  key={i}
                  className={styles.optionBtn}
                  onClick={() => sendMessage(opt, opt)}
                  disabled={wsStatus !== 'connected'}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}

          {/* 승인 버튼 */}
          {requiresApproval && (
            <div className={styles.approvalButtons}>
              <button
                className={`${styles.approvalBtn} ${styles.approveBtn}`}
                onClick={() => handleSendApproval(true)}
                disabled={wsStatus !== 'connected'}
              >
                <ThumbsUp size={16} /> 승인
              </button>
              <button
                className={`${styles.approvalBtn} ${styles.rejectBtn}`}
                onClick={() => handleSendApproval(false)}
                disabled={wsStatus !== 'connected'}
              >
                <ThumbsDown size={16} /> 거절 (수정 요청)
              </button>
            </div>
          )}

          {/* 입력창 */}
          <form
            className={styles.inputRow}
            onSubmit={e => { e.preventDefault(); sendMessage(inputText); }}
          >
            <input
              className={styles.chatInput}
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              placeholder={
                wsStatus !== 'connected'     ? '연결 중...' :
                requiresApproval             ? '위의 버튼으로 승인/거절하세요' :
                currentStage === 'complete'  ? '파이프라인 완료' :
                '메시지 입력...'
              }
              disabled={wsStatus !== 'connected' || requiresApproval || currentStage === 'complete'}
            />
            <button
              type="submit"
              className={styles.sendBtn}
              disabled={!inputText.trim() || wsStatus !== 'connected' || requiresApproval || currentStage === 'complete'}
            >
              <Send size={18} />
            </button>
          </form>
        </section>

        {/* 오른쪽 패널 */}
        <section className={styles.rightPanel}>
          {/* 탭 헤더 */}
          <div className={styles.tabBar}>
            <button
              className={`${styles.tabBtn} ${activeTab === 'chat' ? styles.tabActive : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              <Activity size={14} /> 에이전트 활동
            </button>
            <button
              className={`${styles.tabBtn} ${activeTab === 'events' ? styles.tabActive : ''}`}
              onClick={() => setActiveTab('events')}
            >
              <Terminal size={14} /> 이벤트 로그
            </button>
          </div>

          {/* 에이전트 활동 */}
          {activeTab === 'chat' && (
            <div className={styles.activityPanel}>
              {/* 단계별 요약 카드 */}
              <StageCards stages={PIPELINE_STAGES} currentIdx={stageIdx} />

              {/* 최신 이벤트 */}
              <div className={styles.recentEvents}>
                <div className={styles.recentTitle}>최근 활동</div>
                {events.slice(-8).reverse().map((ev, i) => (
                  <div key={i} className={`${styles.recentEvent} ${eventColor(ev.event_type)}`}>
                    <span className={styles.recentAgent}>{ev.agent_name}</span>
                    <span className={styles.recentContent}>
                      {typeof ev.content === 'string' ? ev.content.slice(0, 120) : ''}
                    </span>
                    <span className={styles.recentTime}>{formatTime(ev.timestamp)}</span>
                  </div>
                ))}
                {events.length === 0 && (
                  <div className={styles.noEvents}>에이전트 활동 대기 중...</div>
                )}
              </div>

              {/* 아티팩트 뷰어 */}
              {artifacts.length > 0 && (
                <div className={styles.artifactSection}>
                  <div className={styles.artifactHeader}>
                    <FileText size={14} /> 생성된 아티팩트
                  </div>
                  <div className={styles.artifactTabs}>
                    {artifacts.map(art => (
                      <button
                        key={art.artifact_type}
                        className={`${styles.artifactTab} ${activeArtifact === art.artifact_type ? styles.artifactTabActive : ''}`}
                        onClick={() => setActiveArtifact(art.artifact_type)}
                      >
                        {ARTIFACT_ICONS[art.artifact_type] ?? '📄'} {art.name}
                      </button>
                    ))}
                  </div>
                  {selectedArt && (
                    <ArtifactViewer artifact={selectedArt} />
                  )}
                </div>
              )}

              {/* 다운로드 패널 (설계 아티팩트 있을 때) */}
              {artifacts.some(a => a.artifact_type === 'design') && session && (
                <ExportPanel sessionId={session.sessionId} />
              )}
            </div>
          )}

          {/* 이벤트 로그 */}
          {activeTab === 'events' && (
            <div className={styles.eventLog}>
              {events.length === 0 && (
                <div className={styles.noEvents}>이벤트 없음</div>
              )}
              {events.map((ev, i) => (
                <div key={i} className={`${styles.logEntry} ${eventColor(ev.event_type)}`}>
                  <span className={styles.logTime}>{formatTime(ev.timestamp)}</span>
                  <span className={styles.logType}>{ev.event_type}</span>
                  <span className={styles.logAgent}>[{ev.agent_name}]</span>
                  <span className={styles.logContent}>
                    {typeof ev.content === 'string' ? ev.content.slice(0, 200) : JSON.stringify(ev.content).slice(0, 200)}
                  </span>
                </div>
              ))}
              <div ref={eventEndRef} />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

// ── 서브 컴포넌트들 ──────────────────────────────────────────

const ARTIFACT_ICONS: Record<string, string> = {
  workflow: '🔬',
  design:   '🏗️',
  tools:    '🔧',
  code:     '💻',
  verify:   '✅',
};

function ChatBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.agentBubble}`}>
      {!isUser && (
        <div className={styles.bubbleAvatar} title={msg.agent_name}>
          <Bot size={14} />
        </div>
      )}
      <div className={styles.bubbleContent}>
        {!isUser && (
          <div className={styles.bubbleMeta}>
            <span className={styles.agentName}>{msg.agent_name}</span>
            <span className={styles.msgTime}>{formatTime(msg.timestamp)}</span>
          </div>
        )}
        <div className={`${styles.bubbleText} ${isUser ? styles.userText : styles.agentText}`}>
          {/* Markdown-like: **bold** and newlines */}
          {renderContent(msg.content)}
        </div>
        {isUser && (
          <div className={styles.userMeta}>
            <span className={styles.msgTime}>{formatTime(msg.timestamp)}</span>
          </div>
        )}
      </div>
      {isUser && (
        <div className={`${styles.bubbleAvatar} ${styles.userAvatar}`}>
          <User size={14} />
        </div>
      )}
    </div>
  );
}

function renderContent(text: string) {
  return text.split('\n').map((line, i) => {
    // **bold** 처리
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return (
      <span key={i}>
        {parts.map((part, j) =>
          part.startsWith('**') && part.endsWith('**')
            ? <strong key={j}>{part.slice(2, -2)}</strong>
            : part
        )}
        {i < text.split('\n').length - 1 && <br />}
      </span>
    );
  });
}

function PipelineBar({ stages, currentIdx }: { stages: typeof PIPELINE_STAGES; currentIdx: number }) {
  return (
    <div className={styles.pipelineBar}>
      {stages.map((s, i) => (
        <div key={s.id} className={styles.pipelineStep}>
          <div className={`${styles.pipelineDot}
            ${i < currentIdx  ? styles.dotDone :
              i === currentIdx ? styles.dotActive :
                                  styles.dotPending}`}
          >
            {i < currentIdx ? <CheckCircle size={10} /> : <span>{s.icon}</span>}
          </div>
          <span className={`${styles.pipelineLabel}
            ${i === currentIdx ? styles.labelActive : ''}`}>
            {s.label}
          </span>
          {i < stages.length - 1 && (
            <ChevronRight size={10} className={`${styles.pipelineArrow} ${i < currentIdx ? styles.arrowDone : ''}`} />
          )}
        </div>
      ))}
    </div>
  );
}

function StageCards({ stages, currentIdx }: { stages: typeof PIPELINE_STAGES; currentIdx: number }) {
  return (
    <div className={styles.stageCards}>
      {stages.map((s, i) => (
        <div key={s.id} className={`${styles.stageCard}
          ${i < currentIdx  ? styles.cardDone :
            i === currentIdx ? styles.cardActive :
                                styles.cardPending}`}
        >
          <span className={styles.cardIcon}>{s.icon}</span>
          <span className={styles.cardLabel}>{s.label}</span>
          {i < currentIdx && <CheckCircle size={12} className={styles.cardCheck} />}
          {i === currentIdx && <div className={styles.cardPulse} />}
        </div>
      ))}
    </div>
  );
}

function ArtifactViewer({ artifact }: { artifact: Artifact }) {
  const content = artifact.content;

  if (artifact.artifact_type === 'code') {
    const code = (content as { code?: string }).code ?? JSON.stringify(content, null, 2);
    return (
      <div className={styles.artifactViewer}>
        <div className={styles.artifactMeta}>
          <Code size={12} /> v{artifact.version} · {(content as { file_name?: string }).file_name ?? 'automation.py'}
        </div>
        <pre className={styles.codeBlock}><code>{code.slice(0, 3000)}{code.length > 3000 ? '\n\n... (truncated)' : ''}</code></pre>
      </div>
    );
  }

  if (artifact.artifact_type === 'design') {
    const mermaid = (content as { mermaid_diagram?: string }).mermaid_diagram;
    return (
      <div className={styles.artifactViewer}>
        <div className={styles.artifactMeta}><Settings size={12} /> v{artifact.version}</div>
        {mermaid && (
          <MermaidChart chart={mermaid} />
        )}
        <pre className={styles.jsonBlock}>{JSON.stringify(content, null, 2).slice(0, 2000)}</pre>
      </div>
    );
  }

  // 기타 아티팩트 — JSON 뷰
  return (
    <div className={styles.artifactViewer}>
      <div className={styles.artifactMeta}><FileText size={12} /> v{artifact.version}</div>
      <pre className={styles.jsonBlock}>{JSON.stringify(content, null, 2).slice(0, 2000)}</pre>
    </div>
  );
}

function ExportPanel({ sessionId }: { sessionId: string }) {
  const base = `${API_BASE}/api/export/${sessionId}`;

  const downloads = [
    { label: 'n8n 워크플로우', href: `${base}/n8n`, ext: 'json', desc: 'n8n에서 직접 import' },
    { label: 'Make 시나리오', href: `${base}/make`, ext: 'json', desc: 'Make > Import scenario' },
    { label: 'Python 코드',   href: `${base}/python`, ext: 'py',   desc: '자동화 스크립트 다운로드' },
    { label: '전체 요약',     href: `${base}/summary`, ext: null,  desc: '브라우저에서 JSON 확인' },
  ];

  return (
    <div className={styles.exportPanel}>
      <div className={styles.exportTitle}><Download size={13} /> 내보내기</div>
      <div className={styles.exportBtns}>
        {downloads.map(d => (
          <a
            key={d.label}
            href={d.href}
            target={d.ext ? '_self' : '_blank'}
            download={d.ext ? `export.${d.ext}` : undefined}
            className={styles.exportBtn}
            rel="noreferrer"
          >
            <span className={styles.exportBtnLabel}>{d.label}</span>
            <span className={styles.exportBtnDesc}>{d.desc}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
