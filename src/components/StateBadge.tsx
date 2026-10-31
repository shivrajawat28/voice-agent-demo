import { AgentState } from '../types/voiceAgent';
import { Mic, Radio, Loader2, Volume2, AlertCircle } from 'lucide-react';

interface StateBadgeProps {
  state: AgentState;
}

export const StateBadge: React.FC<StateBadgeProps> = ({ state }) => {
  switch (state) {
    case 'listening':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">
          <Mic className="w-3.5 h-3.5" />
          LISTENING
        </span>
      );
    case 'processing':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          PROCESSING
        </span>
      );
    case 'speaking':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <Volume2 className="w-3.5 h-3.5 animate-bounce" />
          SPEAKING
        </span>
      );
    case 'error':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/30">
          <AlertCircle className="w-3.5 h-3.5" />
          ERROR
        </span>
      );
    case 'idle':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
          <Radio className="w-3.5 h-3.5 text-slate-500" />
          IDLE
        </span>
      );
  }
};
