import React from 'react';
import {
  Sprout,
  Activity,
  RotateCcw,
  Trash2,
  ShieldCheck,
  Volume2,
  Layers,
} from 'lucide-react';

interface NavbarProps {
  currentLanguage: string;
  onLanguageChange: (lang: string) => void;
  llmProvider?: string;
  gnaniConfigured?: boolean;
  selectedVoice?: string;
  activeZoneId?: string;
  onZoneChange?: (zone: string) => void;
  onRepeatResponse?: () => void;
  onClearTranscript?: () => void;
  hasMessages?: boolean;
  gyaniAudioStatus?: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentLanguage = 'hi-IN',
  onLanguageChange,
  llmProvider = 'gemini',
  gnaniConfigured = true,
  selectedVoice = 'Nalini',
  activeZoneId = 'DEMO-ZONE-001',
  onZoneChange,
  onRepeatResponse,
  onClearTranscript,
  hasMessages = false,
  gyaniAudioStatus = 'IDLE',
}) => {
  const zoneNames: Record<string, string> = {
    'DEMO-ZONE-001': 'Zone 1: Wheat (गेहूं)',
    'DEMO-ZONE-002': 'Zone 2: Cotton (कपास)',
    'DEMO-ZONE-003': 'Zone 3: Tomato (टमाटर)',
    'DEMO-ZONE-004': 'Zone 4: Mustard (सरसों)',
  };

  return (
    <header className="sticky top-0 z-40 bg-[#0E141B] border-b border-slate-800 shadow-md">
      {/* Top Status & Safety Bar */}
      <div className="px-4 sm:px-6 py-1.5 bg-[#0A0E13] border-b border-slate-800/80 text-[11px] flex flex-wrap items-center justify-between text-slate-400 gap-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span>SIMULATED HARDWARE DEMO (ACTUATION LOCKED)</span>
          </div>

          <span className="text-slate-700 hidden sm:inline">•</span>
          <div className="hidden sm:flex items-center gap-1 text-slate-300">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>
              Soil Telemetry: <strong className="text-white font-mono">7 Channels Active</strong>
            </span>
          </div>

          <span className="text-slate-700 hidden md:inline">•</span>
          <div className="hidden md:flex items-center gap-1 text-slate-400 font-mono text-[10px]">
            <span className="text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              {llmProvider.toUpperCase()} Multi-Agent
            </span>
            <span className="text-slate-600">/</span>
            <span className="text-purple-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
              GNANI Indic Voice ({selectedVoice}) {gnaniConfigured ? 'Live' : 'Demo'}
            </span>
          </div>
        </div>

        {/* Audio state pill */}
        <div className="flex items-center gap-2">
          {gyaniAudioStatus !== 'IDLE' && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-950/60 border border-purple-800 text-purple-300 flex items-center gap-1 animate-pulse">
              <Volume2 className="w-3 h-3" />
              <span>{gyaniAudioStatus}</span>
            </span>
          )}
          <div className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-950/30 border border-emerald-800/40 px-2 py-0.5 rounded">
            <ShieldCheck className="w-3 h-3" />
            <span>Safe Autonomous Advisory</span>
          </div>
        </div>
      </div>

      {/* Main Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2.5 text-left">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold shadow-md shadow-emerald-900/30">
              <Sprout className="w-4.5 h-4.5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-1.5 tracking-tight">
                <span>Ferto<span className="text-emerald-400">Bot</span></span>
                <span className="text-slate-500 font-normal hidden sm:inline">|</span>
                <span className="text-slate-200 text-xs sm:text-sm font-semibold flex items-center gap-1">
                  AI Agronomist <span className="text-emerald-400 text-[11px] font-hindi">(कृषि मित्र)</span>
                </span>
                <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  v0.2.0
                </span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono hidden md:block">
                Autonomous Multi-Agent Indic Voice Assistant
              </div>
            </div>
          </div>
        </div>

        {/* Center Zone Quick Selector */}
        {onZoneChange && (
          <div className="hidden lg:flex items-center gap-1.5 bg-[#0D131A] px-2.5 py-1 rounded-lg border border-slate-800 text-xs text-slate-300">
            <Layers className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="text-[10px] text-slate-500 uppercase tracking-wide">Target:</span>
            <select
              value={activeZoneId}
              onChange={(e) => onZoneChange(e.target.value)}
              className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              {Object.entries(zoneNames).map(([id, name]) => (
                <option key={id} value={id} className="bg-slate-900 text-white">
                  {name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Right Action Controls */}
        <div className="flex items-center gap-2">
          {/* Repeat Last Response Button */}
          {onRepeatResponse && (
            <button
              onClick={onRepeatResponse}
              disabled={!hasMessages}
              title="Repeat last response spoken (पुनः सुनें)"
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-800 text-slate-300 hover:text-white text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
              <span className="hidden sm:inline">पुनः सुनें</span>
            </button>
          )}

          {/* Clear Chat Button */}
          {onClearTranscript && (
            <button
              onClick={onClearTranscript}
              disabled={!hasMessages}
              title="Clear conversation history (चैट साफ़ करें)"
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-800 text-slate-300 hover:text-rose-400 text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5 text-slate-400" />
              <span className="hidden sm:inline">साफ़ करें</span>
            </button>
          )}

          {/* Language Selector */}
          <select
            value={currentLanguage}
            onChange={(e) => onLanguageChange && onLanguageChange(e.target.value)}
            className="bg-[#0D131A] border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500 cursor-pointer"
          >
            <option value="hi-IN">🌐 हिन्दी (Hindi)</option>
            <option value="hi-Latn">🌐 Hinglish</option>
            <option value="en-IN">English (India)</option>
            <option value="en-US">English (US)</option>
          </select>
        </div>
      </div>
    </header>
  );
};
