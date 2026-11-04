import { useVoiceAgent } from './hooks/useVoiceAgent';
import { Navbar } from './components/Navbar';
import { VoiceAssistantView } from './components/VoiceAssistantView';
import { AudioPermissionAlert } from './components/AudioPermissionAlert';
import { ShieldCheck, Cpu, Volume2, Sprout } from 'lucide-react';

export function App() {
  const voiceAgent = useVoiceAgent('hi-IN');

  const {
    lastError,
    capabilities,
    micPermission,
    language,
    setLanguage,
    llmProvider,
    gnaniConfigured,
    selectedVoice,
    stopOrCancel,
    activeZoneId,
    setActiveZoneId,
    repeatLastResponse,
    clearTranscript,
    transcript,
    gyaniAudioStatus,
  } = voiceAgent;

  return (
    <div className="min-h-screen bg-[#0B1015] text-[#E2E8F0] flex flex-col font-sans selection:bg-emerald-500/30 selection:text-white">
      {/* Standalone AI Agronomist Navigation Bar */}
      <Navbar
        currentLanguage={language}
        onLanguageChange={setLanguage}
        llmProvider={llmProvider}
        gnaniConfigured={gnaniConfigured}
        selectedVoice={selectedVoice}
        activeZoneId={activeZoneId}
        onZoneChange={setActiveZoneId}
        onRepeatResponse={repeatLastResponse}
        onClearTranscript={clearTranscript}
        hasMessages={transcript.length > 0}
        gyaniAudioStatus={gyaniAudioStatus}
      />

      {/* Main AI Agronomist Interface */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-5 pb-8 space-y-5">
        {/* Safety & Demonstration Provenance Banner */}
        <div className="bg-gradient-to-r from-emerald-950/70 via-slate-900/90 to-blue-950/70 border border-emerald-500/30 rounded-2xl p-3 sm:p-4 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-bold text-white text-sm">FertoBot AI Agronomist (कृषि मित्र)</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 uppercase tracking-wide">
                  Standalone Ready
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-wide">
                  Actuation Locked (Demo)
                </span>
              </div>
              <p className="text-slate-400 text-[11px] mt-0.5">
                Autonomous agricultural advisory powered by Google Gemini Multi-Agent Orchestration & Gnani AI Indic Voice. Sensor readings reflect 7-in-1 in-situ simulated telemetry. Physical pump actuation remains safely isolated.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 text-[11px]">
            <span className="px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300 font-mono text-[10px]">
              FertoBot Platform Integration Module
            </span>
          </div>
        </div>

        {/* Audio Alerts & Microphone Permission Feedback */}
        <AudioPermissionAlert
          error={lastError}
          permission={micPermission}
          capabilities={capabilities}
          onDismissError={stopOrCancel}
        />

        {/* Standalone Voice & Chat Agronomist View */}
        <VoiceAssistantView voiceAgent={voiceAgent} />
      </main>

      {/* Standalone Product Footer */}
      <footer className="bg-[#090D12] border-t border-slate-800/80 py-4 px-4 sm:px-6 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <div className="flex items-center gap-2">
            <Sprout className="w-4 h-4 text-emerald-400" />
            <span className="font-semibold text-slate-300">FertoBot AI Agronomist</span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400">Integration-Ready Standalone Product</span>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono">
            <span className="flex items-center gap-1 text-emerald-400">
              <Cpu className="w-3 h-3" />
              4 Specialist Agents
            </span>
            <span>•</span>
            <span className="flex items-center gap-1 text-purple-400">
              <Volume2 className="w-3 h-3" />
              GNANI Prisma STT + Timbre TTS
            </span>
            <span>•</span>
            <span className="text-amber-400">simulation_mode=true</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
export default App;
