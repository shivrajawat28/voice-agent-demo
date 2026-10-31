import React, { useState } from 'react';
import {
  Droplets,
  Thermometer,
  Activity,
  Flame,
  Zap,
  CheckCircle2,
  TrendingUp,
  ChevronRight,
  Sparkles,
  ArrowUpRight,
  Sprout,
  Check,
  AlertTriangle,
} from 'lucide-react';

interface DashboardViewProps {
  onNavigateTab: (tab: string) => void;
  zoneId?: string;
  onZoneChange?: (zone: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigateTab,
  zoneId = 'DEMO-ZONE-001',
}) => {
  const [selectedMetric, setSelectedMetric] = useState<'moisture' | 'nitrogen' | 'temp'>('moisture');
  const [showNutrientsModal, setShowNutrientsModal] = useState(false);
  const [appliedRecs, setAppliedRecs] = useState<Record<string, boolean>>({});

  const healthScore = 88;

  // 24-Hour Telemetry Mock Data points for SVG chart
  const telemetryHistory = [
    { time: '00:00', moisture: 54.2, nitrogen: 136, temp: 19.8 },
    { time: '04:00', moisture: 52.8, nitrogen: 137, temp: 18.5 },
    { time: '08:00', moisture: 50.4, nitrogen: 138, temp: 21.2 },
    { time: '12:00', moisture: 47.1, nitrogen: 140, temp: 26.4 },
    { time: '16:00', moisture: 46.5, nitrogen: 141, temp: 25.8 },
    { time: '20:00', moisture: 49.3, nitrogen: 139, temp: 22.5 },
    { time: 'Now', moisture: 48.2, nitrogen: 140, temp: 24.5 },
  ];

  const values = telemetryHistory.map((p) =>
    selectedMetric === 'moisture' ? p.moisture : selectedMetric === 'nitrogen' ? p.nitrogen : p.temp
  );
  const minVal = Math.min(...values) - (selectedMetric === 'nitrogen' ? 10 : 3);
  const maxVal = Math.max(...values) + (selectedMetric === 'nitrogen' ? 10 : 3);
  const height = 120;
  const width = 500;

  const pointsString = telemetryHistory
    .map((p, i) => {
      const val =
        selectedMetric === 'moisture'
          ? p.moisture
          : selectedMetric === 'nitrogen'
          ? p.nitrogen
          : p.temp;
      const x = (i / (telemetryHistory.length - 1)) * width;
      const y = height - ((val - minVal) / (maxVal - minVal || 1)) * height;
      return `${x},${y}`;
    })
    .join(' ');

  const areaString = `0,${height} ${pointsString} ${width},${height}`;

  const recommendations = [
    {
      id: 'rec-1',
      category: 'IRRIGATION ADVISORY',
      targetZone: 'Sector B-3 (Wheat)',
      priority: 'HIGH',
      action:
        'मिट्टी की नमी 48.2% है। ताज मूल (CRI) अवस्था में 45 मिनट हल्की ड्रिप सिंचाई करें ताकि जड़ विकास बाधित न हो।',
      estimatedImpact: '+12% Root Vigor',
    },
    {
      id: 'rec-2',
      category: 'NUTRIENT MANAGEMENT',
      targetZone: 'Sector B-3 (Wheat)',
      priority: 'MEDIUM',
      action:
        'नाइट्रोजन 140 ppm संतुलित है। पहली सिंचाई के बाद 25-30 kg यूरिया प्रति एकड़ टॉप-ड्रेसिंग की सिफारिश है।',
      estimatedImpact: 'Enhanced Tillering',
    },
    {
      id: 'rec-3',
      category: 'CLIMATE & DISEASE',
      targetZone: 'Sector B-3 (Wheat)',
      priority: 'NORMAL',
      action:
        'तापमान 24.5°C और आर्द्रता 68% है। मौसम साफ है, फफूंद या कीट प्रकोप का कोई तत्काल खतरा नहीं है।',
      estimatedImpact: 'Preventative Health',
    },
  ];

  const handleApply = (recId: string) => {
    setAppliedRecs((prev) => ({ ...prev, [recId]: true }));
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-fadeIn">
      {/* Farm Overview Top Banner */}
      <div className="matte-card rounded-2xl p-5 sm:p-6 flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-slate-800 text-emerald-400 text-xs font-medium">
              <Sprout className="w-3.5 h-3.5 text-emerald-400" />
              <span>Wheat (गेहूं) • Tillering (40-45 DAS)</span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-mono">
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              <span>SIMULATED BENCHMARK DATA</span>
            </div>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Field Telemetry & Soil Health Station
          </h1>
          <p className="text-xs text-slate-400 leading-relaxed">
            Displaying simulated test telemetry for Upper Gangetic Plains (Alluvial Soil Belt). Readings
            are synthetically generated for interface testing and are grounded in ICAR agricultural benchmarks.
          </p>
          <div className="text-[10px] text-slate-500 font-mono">
            Zone: <strong className="text-slate-300">{zoneId}</strong> • Reading Timestamp:{' '}
            {new Date().toLocaleTimeString()} • Source: simulated-iot-node
          </div>
        </div>

        {/* Health Score Box */}
        <div className="flex items-center gap-4 bg-[#0A0E13] p-3.5 rounded-xl border border-slate-800 shrink-0">
          <div className="relative w-16 h-16 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-slate-800"
                strokeWidth="3.5"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className="text-emerald-500"
                strokeDasharray={`${healthScore}, 100`}
                strokeWidth="3.5"
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
            <span className="absolute text-sm font-bold text-white font-mono">{healthScore}%</span>
          </div>

          <div className="text-left text-xs space-y-0.5">
            <div className="font-semibold text-white flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Normal Vigor</span>
            </div>
            <div className="text-[11px] text-slate-400">
              Tank: <strong className="text-slate-200 font-mono">78%</strong>
            </div>
            <button
              onClick={() => onNavigateTab('irrigation')}
              className="text-[11px] text-emerald-400 font-medium hover:underline flex items-center gap-0.5 pt-0.5 cursor-pointer"
            >
              <span>Manage Valves</span>
              <ArrowUpRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Primary 6 Metrics Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Soil Moisture */}
        <div className="matte-card matte-card-hover rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Moisture</span>
            <Droplets className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono mb-1">
            48.2<span className="text-xs font-normal text-slate-400">%</span>
          </div>
          <div className="text-[10px] text-emerald-400 font-medium">Optimal (45-65%)</div>
        </div>

        {/* Soil pH */}
        <div className="matte-card matte-card-hover rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Soil pH</span>
            <Activity className="w-4 h-4 text-teal-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono mb-1">6.8</div>
          <div className="text-[10px] text-teal-300 font-medium">Neutral (6.5-7.2)</div>
        </div>

        {/* Nitrogen */}
        <div className="matte-card matte-card-hover rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Nitrogen (N)</span>
            <Sprout className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono mb-1">
            140<span className="text-xs font-normal text-slate-400"> ppm</span>
          </div>
          <div className="text-[10px] text-slate-400">Target: 120-150 ppm</div>
        </div>

        {/* Phosphorus */}
        <div className="matte-card matte-card-hover rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Phosphorus (P)</span>
            <Flame className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono mb-1">
            24<span className="text-xs font-normal text-slate-400"> ppm</span>
          </div>
          <div className="text-[10px] text-amber-400 font-medium">Good Root State</div>
        </div>

        {/* Potassium */}
        <div className="matte-card matte-card-hover rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Potassium (K)</span>
            <Zap className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono mb-1">
            185<span className="text-xs font-normal text-slate-400"> ppm</span>
          </div>
          <div className="text-[10px] text-cyan-300 font-medium">High Resilience</div>
        </div>

        {/* Soil Temp */}
        <div className="matte-card matte-card-hover rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Soil Temp</span>
            <Thermometer className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono mb-1">24.5°C</div>
          <div className="text-[10px] text-slate-400">Humidity: 68%</div>
        </div>
      </div>

      {/* Secondary Nutrients Bar */}
      <div className="matte-card rounded-xl p-3 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex flex-wrap items-center gap-3 text-slate-400">
          <span className="text-emerald-400 font-mono text-[11px]">EC: 1.15 dS/m</span>
          <span className="hidden sm:inline">•</span>
          <span>
            Calcium: <strong className="text-slate-200 font-mono">280 ppm</strong>
          </span>
          <span className="hidden sm:inline">•</span>
          <span>
            Magnesium: <strong className="text-slate-200 font-mono">95 ppm</strong>
          </span>
          <span className="hidden md:inline">•</span>
          <span>
            Iron: <strong className="text-slate-200 font-mono">12 ppm</strong>
          </span>
          <span className="hidden md:inline">•</span>
          <span>
            Water Tank: <strong className="text-slate-200 font-mono">78%</strong>
          </span>
          <span className="hidden lg:inline">•</span>
          <span>
            Device Battery: <strong className="text-emerald-400 font-mono">92%</strong>
          </span>
        </div>
        <button
          onClick={() => setShowNutrientsModal(!showNutrientsModal)}
          className="text-xs font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer"
        >
          <span>{showNutrientsModal ? 'Hide Details' : 'View Trace Assay'}</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Trace Assay Dropdown */}
      {showNutrientsModal && (
        <div className="matte-card rounded-xl p-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-xs animate-fadeIn">
          <div className="p-2.5 bg-[#0D131A] rounded-lg border border-slate-800">
            <div className="text-[10px] text-slate-400">Calcium (Ca)</div>
            <div className="font-bold text-white font-mono">280 ppm</div>
          </div>
          <div className="p-2.5 bg-[#0D131A] rounded-lg border border-slate-800">
            <div className="text-[10px] text-slate-400">Magnesium (Mg)</div>
            <div className="font-bold text-white font-mono">95 ppm</div>
          </div>
          <div className="p-2.5 bg-[#0D131A] rounded-lg border border-slate-800">
            <div className="text-[10px] text-slate-400">Sulfur (S)</div>
            <div className="font-bold text-white font-mono">35 ppm</div>
          </div>
          <div className="p-2.5 bg-[#0D131A] rounded-lg border border-slate-800">
            <div className="text-[10px] text-slate-400">Iron (Fe)</div>
            <div className="font-bold text-white font-mono">12 ppm</div>
          </div>
          <div className="p-2.5 bg-[#0D131A] rounded-lg border border-slate-800">
            <div className="text-[10px] text-slate-400">Zinc (Zn)</div>
            <div className="font-bold text-white font-mono">4.2 ppm</div>
          </div>
          <div className="p-2.5 bg-[#0D131A] rounded-lg border border-slate-800">
            <div className="text-[10px] text-slate-400">Boron (B)</div>
            <div className="font-bold text-white font-mono">0.8 ppm</div>
          </div>
        </div>
      )}

      {/* Main Grid: Telemetry Trends & AI Recommendations */}
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Left Column: 24h Telemetry Chart */}
        <div className="lg:col-span-7 matte-card rounded-2xl p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <span>24-Hour Telemetry Curve</span>
              </h2>
              <p className="text-[11px] text-slate-400">Sampled via ESP32 telemetry nodes</p>
            </div>

            <div className="flex items-center gap-1 bg-[#0A0E13] p-1 rounded-lg border border-slate-800 text-xs">
              {(['moisture', 'nitrogen', 'temp'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setSelectedMetric(m)}
                  className={`px-2.5 py-1 rounded text-[11px] transition-colors capitalize cursor-pointer ${
                    selectedMetric === m
                      ? 'bg-slate-800 text-white font-semibold'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {m === 'temp' ? 'Temp (°C)' : m}
                </button>
              ))}
            </div>
          </div>

          {/* SVG Chart */}
          <div className="w-full h-36 relative bg-[#0A0E13] rounded-xl p-3 border border-slate-800/80">
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
              <polygon points={areaString} fill="rgba(16, 185, 129, 0.12)" />
              <polyline
                fill="none"
                stroke="#10B981"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={pointsString}
              />
              {telemetryHistory.map((p, i) => {
                const val =
                  selectedMetric === 'moisture'
                    ? p.moisture
                    : selectedMetric === 'nitrogen'
                    ? p.nitrogen
                    : p.temp;
                const x = (i / (telemetryHistory.length - 1)) * width;
                const y = height - ((val - minVal) / (maxVal - minVal || 1)) * height;
                return (
                  <circle
                    key={i}
                    cx={x}
                    cy={y}
                    r="3.5"
                    className="fill-emerald-400 stroke-[#0A0E13] stroke-2"
                  />
                );
              })}
            </svg>

            <div className="flex justify-between text-[10px] text-slate-500 font-mono pt-1">
              {telemetryHistory.map((p, i) => (
                <span key={i}>{p.time}</span>
              ))}
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <span>
              Probes:{' '}
              <strong className="text-white font-mono">5 / 5 Online (Simulated)</strong>
            </span>
            <button
              onClick={() => onNavigateTab('probes')}
              className="text-emerald-400 hover:underline flex items-center gap-0.5 cursor-pointer"
            >
              <span>Fleet Manager</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right Column: AI Recommendations */}
        <div className="lg:col-span-5 matte-card rounded-2xl p-5 space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>AI Agronomic Recommendations</span>
              </h2>
              <span className="text-[10px] font-mono text-slate-400">Real-Time</span>
            </div>

            <div className="space-y-2.5">
              {recommendations.map((rec) => (
                <div
                  key={rec.id}
                  className="p-3 rounded-xl bg-[#0D131A] border border-slate-800 space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wide">
                      {rec.category} • {rec.targetZone}
                    </span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
                      {rec.priority}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200">{rec.action}</p>

                  <div className="pt-1.5 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-[10px] text-slate-400">
                      Impact: <strong className="text-emerald-400">{rec.estimatedImpact}</strong>
                    </span>
                    <button
                      onClick={() => handleApply(rec.id)}
                      className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors flex items-center gap-1 cursor-pointer ${
                        appliedRecs[rec.id]
                          ? 'bg-slate-800 text-emerald-400 border border-emerald-500/40'
                          : 'bg-emerald-600 hover:bg-emerald-500 text-white'
                      }`}
                    >
                      <Check className="w-3 h-3" />
                      <span>{appliedRecs[rec.id] ? 'Applied' : 'Apply'}</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => onNavigateTab('voice')}
            className="w-full mt-3 py-2 rounded-xl bg-[#0A0E13] hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
          >
            <span>Ask Agronomist Chatbot (बोलकर या लिखकर पूछें)</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
          </button>
        </div>
      </div>
    </div>
  );
};
