import { useState } from 'react';
import { useVoiceAgent } from './hooks/useVoiceAgent';
import { Navbar } from './components/Navbar';
import { DashboardView } from './components/DashboardView';
import { VoiceAssistantView } from './components/VoiceAssistantView';
import { VoiceEvaluationPanel } from './components/VoiceEvaluationPanel';
import { FarmTelemetryDashboard } from './components/FarmTelemetryDashboard';
import { AudioPermissionAlert } from './components/AudioPermissionAlert';
import {
  Droplets,
  Radio,
  Camera,
  FileSpreadsheet,
  Sparkles,
  Settings,
  ChevronDown,
  ChevronUp,
  Cpu,
  CheckCircle2,
  ShieldCheck,
} from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'voice' | 'irrigation' | 'probes' | 'security' | 'reports' | 'features' | 'profile'>('dashboard');
  const [showDiagnostics, setShowDiagnostics] = useState(false);

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
    setSelectedVoice,
    stopOrCancel,
    activeZoneId,
    setActiveZoneId,
  } = voiceAgent;

  // Simulation triggers for top strip
  const handleSimulateRain = () => {
    fetch('/api/simulate/rain', { method: 'POST' }).catch(() => {});
  };

  const handleSimulateDepletion = () => {
    fetch('/api/simulate/depletion', { method: 'POST' }).catch(() => {});
  };

  const handleSimulateIntrusion = () => {
    fetch('/api/simulate/intrusion', { method: 'POST' }).catch(() => {});
  };

  const handleResetSim = () => {
    fetch('/api/simulate/reset', { method: 'POST' }).catch(() => {});
  };

  return (
    <div className="min-h-screen bg-[#0B1015] text-[#E2E8F0] flex flex-col font-sans selection:bg-emerald-500/30 selection:text-white">
      {/* Reference-Matched Sticky Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={(t) => setActiveTab(t as any)}
        healthScore={88}
        weatherLocation="Jaipur, Rajasthan"
        weatherTemp="25°C"
        onSimulateRain={handleSimulateRain}
        onSimulateDepletion={handleSimulateDepletion}
        onSimulateIntrusion={handleSimulateIntrusion}
        onResetSim={handleResetSim}
        currentLanguage={language}
        onLanguageChange={setLanguage}
        llmProvider={llmProvider}
        gnaniConfigured={gnaniConfigured}
      />

      {/* Main Tab Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-5 pb-8 space-y-5">
        {/* FertoBot Team Review Staging Banner */}
        <div className="bg-gradient-to-r from-emerald-950/70 via-slate-900/90 to-blue-950/70 border border-emerald-500/30 rounded-2xl p-3 sm:p-4 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-bold text-white text-sm">FertoBot Team Review — Simulated Hardware Demo</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-wide">
                  Actuation Disabled
                </span>
              </div>
              <p className="text-slate-400 text-[11px] mt-0.5">
                All seven soil sensor channels are simulated virtual Modbus registers. Pump actuation approval is simulated; physical hardware relays remain safely isolated.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 text-[11px]">
            <span className="px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300 font-mono">
              Phase 20 Staging
            </span>
          </div>
        </div>

        {/* Alerts & Permission Feedback */}
        <AudioPermissionAlert
          error={lastError}
          permission={micPermission}
          capabilities={capabilities}
          onDismissError={stopOrCancel}
        />

        {/* TAB 1: DASHBOARD VIEW (Reference Screenshot 1) */}
        {activeTab === 'dashboard' && (
          <DashboardView
            onNavigateTab={(tab) => setActiveTab(tab as any)}
            zoneId={activeZoneId}
            onZoneChange={setActiveZoneId}
          />
        )}

        {/* TAB 2: AGRONOMIST VOICE ASSISTANT VIEW (Reference Screenshots 2 & 3) */}
        {activeTab === 'voice' && <VoiceAssistantView voiceAgent={voiceAgent} />}

        {/* TAB 3: IRRIGATION MANAGEMENT VIEW */}
        {activeTab === 'irrigation' && (
          <div className="space-y-5 animate-fadeIn">
            <div className="matte-card rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
                  <Droplets className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    Irrigation & Actuation Safety Hub
                  </h2>
                  <p className="text-xs text-slate-400">
                    Valves, water tank storage, and moisture scheduling. Actuation is locked in read-only demo mode.
                  </p>
                </div>
              </div>

              <div className="grid md:grid-cols-3 gap-4 mt-5">
                <div className="p-4 rounded-xl bg-[#0D131A] border border-slate-800 space-y-2">
                  <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">
                    Sector B-3 (Wheat Zone)
                  </span>
                  <div className="text-xl font-bold text-white font-mono">48.2% Moisture</div>
                  <p className="text-xs text-slate-400">
                    Solenoid Valve 1: <strong className="text-emerald-400">Standby (Scheduled 06:00 PM)</strong>
                  </p>
                  <div className="text-[10px] text-amber-400/90 bg-amber-500/10 p-2 rounded border border-amber-500/20">
                    Safety Guard: actuation_permitted = false. Direct hardware triggers are blocked for demo safety.
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#0D131A] border border-slate-800 space-y-2">
                  <span className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
                    Sector C-1 (Cotton Zone)
                  </span>
                  <div className="text-xl font-bold text-white font-mono">38.0% Moisture</div>
                  <p className="text-xs text-slate-400">
                    Solenoid Valve 2: <strong className="text-slate-300">Ready</strong>
                  </p>
                  <div className="text-[10px] text-slate-400">
                    Recommended run time: 35 minutes drip irrigation.
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#0D131A] border border-slate-800 space-y-2">
                  <span className="text-[10px] font-semibold text-teal-400 uppercase tracking-wider">
                    Main Water Storage Tank
                  </span>
                  <div className="text-xl font-bold text-white font-mono">78% Full</div>
                  <p className="text-xs text-slate-400">
                    Capacity: <strong className="text-slate-300">12,000 / 15,000 Liters</strong>
                  </p>
                  <div className="text-[10px] text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Sufficient pressure for all 3 sectors</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: PROBES & SENSOR FLEET */}
        {activeTab === 'probes' && (
          <div className="space-y-5 animate-fadeIn">
            <div className="matte-card rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                  <Radio className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    IoT Probe Fleet Manager
                  </h2>
                  <p className="text-xs text-slate-400">
                    Real-time mesh status of simulated ESP32 LoRa / WiFi telemetry probes.
                  </p>
                </div>
              </div>

              <div className="grid md:grid-cols-3 gap-4 mt-5">
                {[
                  { id: 'PROBE-001', name: 'Wheat Canopy Probe', depth: '15 cm', bat: '92%', rssi: '-68 dBm', status: 'Online' },
                  { id: 'PROBE-002', name: 'Cotton Rootzone Probe', depth: '30 cm', bat: '88%', rssi: '-72 dBm', status: 'Online' },
                  { id: 'PROBE-003', name: 'Tomato Raised Bed Probe', depth: '15 cm', bat: '95%', rssi: '-65 dBm', status: 'Online' },
                ].map((probe) => (
                  <div key={probe.id} className="p-4 rounded-xl bg-[#0D131A] border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">{probe.name}</span>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30">
                        {probe.status}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 font-mono space-y-0.5">
                      <div>Node ID: {probe.id}</div>
                      <div>Sensor Depth: {probe.depth}</div>
                      <div>Battery: {probe.bat} | RSSI: {probe.rssi}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: SECURITY & CAMERA */}
        {activeTab === 'security' && (
          <div className="space-y-5 animate-fadeIn">
            <div className="matte-card rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
                  <Camera className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    Farm Perimeter Security & CCTV
                  </h2>
                  <p className="text-xs text-slate-400">
                    Thermal boundary detection and wildlife intrusion logs.
                  </p>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4 mt-5">
                <div className="p-4 rounded-xl bg-[#0D131A] border border-slate-800 space-y-2">
                  <span className="text-xs font-bold text-white">Camera 1 • North Gate</span>
                  <div className="h-32 bg-slate-950 rounded-lg flex items-center justify-center border border-slate-800 text-xs text-slate-500">
                    [Live Stream Simulated • No Intrusion Detected]
                  </div>
                  <div className="text-[11px] text-emerald-400 flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>PIR Motion Sensor Clear</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#0D131A] border border-slate-800 space-y-2">
                  <span className="text-xs font-bold text-white">Camera 2 • Sector B-3 Perimeter</span>
                  <div className="h-32 bg-slate-950 rounded-lg flex items-center justify-center border border-slate-800 text-xs text-slate-500">
                    [Live Stream Simulated • Cattle Deterrent Active]
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Last boundary check: 5 minutes ago.
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: REPORTS & EXPORT */}
        {activeTab === 'reports' && (
          <div className="space-y-5 animate-fadeIn">
            <div className="matte-card rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    Agronomic Soil & Harvest Reports
                  </h2>
                  <p className="text-xs text-slate-400">
                    Generate and export verified ICAR benchmark audit summaries.
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#0D131A] border border-slate-800 space-y-3 mt-4 text-xs">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="font-semibold text-white">Weekly Telemetry & Irrigation Audit (Wheat)</span>
                  <span className="text-emerald-400 font-mono">Ready (PDF)</span>
                </div>
                <p className="text-slate-400">
                  Average soil moisture was maintained at 51.4%, with nitrogen levels within optimal tillering thresholds (140 ppm).
                </p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 7: FEATURE STUDIO */}
        {activeTab === 'features' && (
          <div className="space-y-5 animate-fadeIn">
            <div className="matte-card rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    Custom Feature Studio
                  </h2>
                  <p className="text-xs text-slate-400">
                    Prototype and pin new custom agronomic workflows to your dashboard.
                  </p>
                </div>
              </div>
              <div className="p-4 rounded-xl bg-[#0D131A] border border-slate-800 text-xs text-slate-400 mt-4">
                Feature studio is active with 3 pinned dashboard widgets.
              </div>
            </div>
          </div>
        )}

        {/* TAB 8: FARM SETTINGS */}
        {activeTab === 'profile' && (
          <div className="space-y-5 animate-fadeIn">
            <div className="matte-card rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
                  <Settings className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    Farm Profile & Calibration Settings
                  </h2>
                  <p className="text-xs text-slate-400">
                    Region, crop rotation schedules, and simulated sensor calibration parameters.
                  </p>
                </div>
              </div>
              <div className="grid md:grid-cols-2 gap-4 mt-4 text-xs">
                <div className="p-3 bg-[#0D131A] rounded-xl border border-slate-800 space-y-1">
                  <div className="text-slate-400">Farm Name</div>
                  <div className="font-semibold text-white">Prince AgriTech Hub</div>
                </div>
                <div className="p-3 bg-[#0D131A] rounded-xl border border-slate-800 space-y-1">
                  <div className="text-slate-400">Agro-Ecological Region</div>
                  <div className="font-semibold text-white">Upper Gangetic Plains (Alluvial Loam)</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Diagnostic Drawer Toggle */}
        <div className="pt-2 border-t border-slate-800/80">
          <button
            onClick={() => setShowDiagnostics(!showDiagnostics)}
            className="w-full py-2 px-4 rounded-xl bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800 text-xs text-slate-400 hover:text-slate-200 transition-colors flex items-center justify-between cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <span>
                Diagnostic Suite: Speech Evaluation Samples & Raw Telemetry Controls
              </span>
            </div>
            {showDiagnostics ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </button>

          {showDiagnostics && (
            <div className="mt-3 space-y-4 animate-fadeIn">
              <VoiceEvaluationPanel
                currentVoice={selectedVoice}
                onSelectVoice={setSelectedVoice}
              />
              <FarmTelemetryDashboard
                activeZoneId={activeZoneId}
                onSelectZone={setActiveZoneId}
              />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
