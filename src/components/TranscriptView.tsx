import React, { useEffect, useRef, useState } from 'react';
import { ChatMessage, StreamingPlaybackState } from '../types/voiceAgent';
import { PumpApprovalCard } from './PumpApprovalCard';
import {
  Bot,
  Volume2,
  Trash2,
  ChevronDown,
  ChevronRight,
  BookOpen,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Radio,
  Square,
  Copy,
  Check,
} from 'lucide-react';

interface TranscriptViewProps {
  transcript: ChatMessage[];
  onRepeatResponse?: () => void;
  onClearTranscript?: () => void;
  currentSpeakingMsgId?: string | null;
  currentSpeakingSentenceIndex?: number | null;
  playbackState?: StreamingPlaybackState;
  revealedSentenceCount?: Record<string, number>;
  onReplayMessage?: (msgId: string) => void;
  onStopSpeaking?: () => void;
  onApprovePump?: (actionId: string) => Promise<void>;
  onRejectPump?: (actionId: string) => Promise<void>;
}

export const TranscriptView: React.FC<TranscriptViewProps> = ({
  transcript,
  onRepeatResponse,
  onClearTranscript,
  currentSpeakingMsgId = null,
  currentSpeakingSentenceIndex = null,
  playbackState = 'IDLE',
  revealedSentenceCount = {},
  onReplayMessage,
  onStopSpeaking,
  onApprovePump,
  onRejectPump,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [expandedTraceIds, setExpandedTraceIds] = useState<Record<string, boolean>>({});
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, currentSpeakingSentenceIndex, revealedSentenceCount]);

  const toggleTrace = (id: string) => {
    setExpandedTraceIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(id);
    setTimeout(() => setCopiedMsgId(null), 1500);
  };

  const getPlaybackBadgeColor = (st: StreamingPlaybackState) => {
    switch (st) {
      case 'THINKING':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'STREAMING TEXT':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
      case 'GENERATING AUDIO':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
      case 'SPEAKING':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 animate-pulse';
      case 'COMPLETED':
        return 'bg-slate-800 text-slate-400 border-slate-700';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="flex flex-col h-[460px] bg-slate-900/40 rounded-2xl border border-slate-800 p-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Conversation Transcript & Multi-Agent Trace
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400">
            {transcript.length} {transcript.length === 1 ? 'turn' : 'turns'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {playbackState === 'SPEAKING' && onStopSpeaking && (
            <button
              onClick={onStopSpeaking}
              className="flex items-center gap-1 px-2.5 py-1 text-xs text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-md transition-colors"
              title="Stop voice playback"
            >
              <Square className="w-3 h-3 fill-current" />
              Stop Audio
            </button>
          )}

          {transcript.length > 0 && onRepeatResponse && (
            <button
              onClick={onRepeatResponse}
              className="flex items-center gap-1 px-2.5 py-1 text-xs text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-md transition-colors"
              title="Repeat last response"
            >
              <Volume2 className="w-3.5 h-3.5" />
              Repeat Last
            </button>
          )}

          {transcript.length > 0 && onClearTranscript && (
            <button
              onClick={onClearTranscript}
              className="p-1 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded transition-colors"
              title="Clear transcript"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto space-y-3.5 pr-2 scrollbar-thin scrollbar-thumb-slate-700">
        {transcript.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
            <Bot className="w-10 h-10 mb-2 opacity-30 text-emerald-400" />
            <p className="text-sm font-medium text-slate-400">No dialogue recorded yet.</p>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">
              Click the microphone button to speak, click quick suggestion chips above, or type an agricultural question below.
            </p>
          </div>
        ) : (
          transcript.map((msg, mIdx) => {
            const isUser = msg.role === 'user';
            const formattedTime = new Date(msg.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            });
            const hasTrace =
              (msg.agentResults && msg.agentResults.length > 0) ||
              (msg.executionTrace && msg.executionTrace.length > 0);
            const isExpanded = !!expandedTraceIds[msg.id];
            const isLastAgentMsg = !isUser && mIdx === transcript.length - 1;
            const isCurrentlySpeakingThisMsg = !isUser && msg.id === currentSpeakingMsgId;

            // Progressive disclosure sentence count
            const totalSentences = msg.sentences?.length ?? 1;
            const revealedCount =
              revealedSentenceCount[msg.id] !== undefined
                ? revealedSentenceCount[msg.id]
                : isCurrentlySpeakingThisMsg
                ? 0
                : totalSentences;

            return (
              <div
                key={msg.id}
                className={`flex gap-3 text-sm ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/30">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-xl px-4 py-2.5 shadow-sm transition-all duration-200 ${
                    isUser
                      ? 'bg-emerald-600 text-slate-50 rounded-br-none'
                      : isCurrentlySpeakingThisMsg
                      ? 'bg-slate-800/95 text-slate-100 border border-emerald-500/60 rounded-bl-none shadow-emerald-500/10'
                      : 'bg-slate-800/90 text-slate-200 border border-slate-700/80 rounded-bl-none'
                  }`}
                >
                  <div className="flex items-center justify-between gap-4 mb-1.5 text-[10px] opacity-80">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold uppercase tracking-wider">
                        {isUser ? 'User Voice / Text' : 'FertoBot Intelligence'}
                      </span>
                      {!isUser && (isCurrentlySpeakingThisMsg || (isLastAgentMsg && playbackState !== 'IDLE')) && (
                        <span
                          className={`px-1.5 py-0.2 rounded font-mono text-[9px] uppercase border ${getPlaybackBadgeColor(
                            playbackState
                          )}`}
                        >
                          {playbackState}
                        </span>
                      )}
                    </div>
                    <span>{formattedTime}</span>
                  </div>

                  {/* Clean natural spoken text with progressive sentence synchronization */}
                  {!isUser && msg.sentences && msg.sentences.length > 0 ? (
                    revealedCount === 0 && (isCurrentlySpeakingThisMsg || (isLastAgentMsg && playbackState !== 'IDLE')) ? (
                      <div className="flex items-center gap-2 text-slate-400 py-1.5 text-xs">
                        <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                        <span className="italic">आवाज़ तैयार हो रही है (Generating neural audio)...</span>
                      </div>
                    ) : (
                      <div className="space-y-1.5 leading-relaxed">
                        {msg.sentences.slice(0, revealedCount).map((sentence, sIdx) => {
                          const isSpeakingSentence =
                            isCurrentlySpeakingThisMsg && currentSpeakingSentenceIndex === sIdx;
                          const isPastSentence =
                            isCurrentlySpeakingThisMsg &&
                            currentSpeakingSentenceIndex !== null &&
                            sIdx < currentSpeakingSentenceIndex;

                          return (
                            <p
                              key={sIdx}
                              className={`transition-all duration-200 rounded px-1.5 py-0.5 ${
                                isSpeakingSentence
                                  ? 'bg-emerald-500/20 text-emerald-200 border-l-2 border-emerald-400 pl-2 font-medium shadow-sm ring-1 ring-emerald-500/40'
                                  : isPastSentence
                                  ? 'text-slate-300 opacity-90'
                                  : 'text-slate-200'
                              }`}
                            >
                              {isSpeakingSentence && (
                                <Radio className="inline-block w-3 h-3 text-emerald-400 mr-1.5 -mt-0.5 animate-pulse" />
                              )}
                              {sentence}
                            </p>
                          );
                        })}
                      </div>
                    )
                  ) : (
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                  )}

                  {/* Clarification alert only if explicit context needed and provided */}
                  {msg.needsClarification && msg.clarificationPrompt && (
                    <div className="mt-2.5 flex items-center gap-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
                      <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                      <span>{msg.clarificationPrompt}</span>
                    </div>
                  )}

                  {/* Phase 18: Farmer-Controlled Safe Pump Approval Card */}
                  {msg.pendingAction && onApprovePump && onRejectPump && (
                    <PumpApprovalCard
                      action={msg.pendingAction}
                      onApprove={onApprovePump}
                      onReject={onRejectPump}
                    />
                  )}

                  {/* Actions & Badges */}
                  <div className="mt-2.5 pt-2 border-t border-slate-700/50 flex flex-wrap items-center justify-between gap-2 text-[10px]">
                    <div className="flex flex-wrap items-center gap-1.5 font-mono">
                      {msg.intent && (
                        <span className="bg-emerald-950/80 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-800">
                          {msg.intent}
                        </span>
                      )}
                      {msg.providerStatus && (
                        <span className="bg-slate-700/80 text-slate-300 px-1.5 py-0.5 rounded border border-slate-600 flex items-center gap-1">
                          <Cpu className="w-3 h-3 text-cyan-400" />
                          {msg.providerStatus}
                        </span>
                      )}
                      {msg.agentResults &&
                        msg.agentResults.map((ag) => (
                          <span
                            key={ag.agent_id}
                            className="bg-sky-950/80 text-sky-300 px-1.5 py-0.5 rounded border border-sky-800 flex items-center gap-1"
                          >
                            <CheckCircle2 className="w-2.5 h-2.5 text-sky-400" />
                            {ag.name}
                          </span>
                        ))}
                    </div>

                    <div className="flex items-center gap-2">
                      {!isUser && (
                        <>
                          <button
                            onClick={() =>
                              onReplayMessage ? onReplayMessage(msg.id) : onRepeatResponse?.()
                            }
                            className="hover:text-emerald-400 text-slate-400 flex items-center gap-1 transition-colors px-1.5 py-0.5 rounded hover:bg-slate-800"
                            title="Listen to this response again (GNANI AI Neural Voice)"
                          >
                            <Volume2 className="w-3 h-3 text-emerald-400" />
                            <span>सुनें</span>
                          </button>
                          <button
                            onClick={() => handleCopy(msg.id, msg.text)}
                            className="hover:text-emerald-400 text-slate-400 flex items-center gap-1 transition-colors px-1.5 py-0.5 rounded hover:bg-slate-800"
                            title="Copy response text"
                          >
                            {copiedMsgId === msg.id ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-400" />
                                <span className="text-emerald-400">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                        </>
                      )}

                      {hasTrace && (
                        <button
                          onClick={() => toggleTrace(msg.id)}
                          className="flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 font-sans transition-colors cursor-pointer"
                          title="Toggle Multi-Agent Reasoning Trace"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                          <span>{isExpanded ? 'Hide Trace' : 'Trace'}</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Expanded Trace & Evidence Drawer */}
                  {hasTrace && isExpanded && (
                    <div className="mt-3 p-3 rounded-lg bg-slate-900/90 border border-slate-700/70 text-xs space-y-2.5">
                      {/* Specialist Agent Findings */}
                      {msg.agentResults && msg.agentResults.length > 0 && (
                        <div>
                          <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px] block mb-1">
                            Specialist Agent Findings:
                          </span>
                          <div className="space-y-1.5">
                            {msg.agentResults.map((ar) => (
                              <div
                                key={ar.agent_id}
                                className="p-2 rounded bg-slate-800/70 border border-slate-700/60"
                              >
                                <div className="flex items-center justify-between text-[11px] text-sky-300 font-medium mb-0.5">
                                  <span>{ar.name}</span>
                                  <span className="text-[10px] text-emerald-400 uppercase font-mono">
                                    {ar.status}
                                  </span>
                                </div>
                                <p className="text-slate-300 text-[11px] leading-relaxed">
                                  {ar.summary}
                                </p>
                                {ar.evidence && ar.evidence.length > 0 && (
                                  <div className="mt-1 pt-1 border-t border-slate-700/40 text-[10px] text-slate-400 space-y-0.5">
                                    <span className="font-semibold text-slate-300">Evidence:</span>
                                    <ul className="list-disc list-inside space-y-0.5">
                                      {ar.evidence.map((ev, idx) => (
                                        <li key={idx}>{ev}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Attributed Sources */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div>
                          <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px] flex items-center gap-1 mb-1">
                            <BookOpen className="w-3 h-3 text-emerald-400" />
                            Attributed Sources & Tools:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.sources.map((src, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/80 text-[10px]"
                              >
                                {src}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Diagnostic Warnings */}
                      {msg.warnings && msg.warnings.length > 0 && (
                        <div>
                          <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px] flex items-center gap-1 mb-1">
                            <AlertTriangle className="w-3 h-3 text-amber-400" />
                            Limitations & Data Disclosures:
                          </span>
                          <div className="space-y-1">
                            {msg.warnings.map((w, idx) => (
                              <div
                                key={idx}
                                className="p-1.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px]"
                              >
                                {w}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
