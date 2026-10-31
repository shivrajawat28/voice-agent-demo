import React from 'react';
import { Sparkles, Layers, Sprout } from 'lucide-react';

interface ScenarioToolbarProps {
  onSelectScenario: (text: string) => void;
  disabled?: boolean;
}

interface ScenarioOption {
  label: string;
  query: string;
  icon?: string;
  badge?: string;
}

export const ScenarioToolbar: React.FC<ScenarioToolbarProps> = ({
  onSelectScenario,
  disabled = false,
}) => {
  const phase14AgronomicScenarios: ScenarioOption[] = [
    { label: 'Crop Suitability', query: 'Is soil mein aur kya uga sakte hain?', icon: '🌾', badge: 'Suitability' },
    { label: 'Best Crop Choice', query: 'Mere farm ke liye best crop kaunsi ho sakti hai?', icon: '🌱', badge: 'Reasoning' },
    { label: 'Soil pH 6.8 Meaning', query: 'Soil pH 6.8 ka kya matlab hai?', icon: '⚗️', badge: 'Chemistry' },
    { label: 'N vs P Difference', query: 'Nitrogen aur phosphorus mein kya difference hai?', icon: '🧪', badge: 'Nutrients' },
    { label: 'Cotton Irrigation', query: 'Cotton ki irrigation kaise manage karni chahiye?', icon: '💧', badge: 'Advisory' },
    { label: 'Soil Fertility', query: 'Soil fertility improve kaise kar sakte hain?', icon: '🌿', badge: 'Best Practice' },
    { label: 'Crop Rotation', query: 'Crop rotation kya hota hai?', icon: '🔄', badge: 'Agronomy' },
    { label: 'Wheat Soil Needs', query: 'Wheat grow karne ke liye kaunsi soil conditions chahiye?', icon: '🌾', badge: 'Conditions' },
    { label: 'Tomato Yellow Leaves', query: 'Tomato mein leaves yellow ho rahe hain, possible reasons kya ho sakte hain?', icon: '🍅', badge: 'Diagnosis' },
    { label: 'Over-Irrigation Risks', query: 'Over-irrigation ke kya disadvantages hain?', icon: '⚠️', badge: 'Precautions' },
    { label: 'Electrical Conductivity', query: 'Electrical conductivity ka soil par kya effect hota hai?', icon: '⚡', badge: 'Salinity' },
    { label: 'Soil Health Assessment', query: 'Mere zone ki current readings ke basis par soil health samjhao.', icon: '📊', badge: 'Grounded' },
    { label: 'Organic Principles', query: 'Mujhe organic farming ke basic principles batao.', icon: '🌱', badge: 'Organic' },
    { label: 'Monsoon Precautions', query: 'Monsoon ke time farming mein kya precautions lene chahiye?', icon: '🌧️', badge: 'Monsoon' },
    { label: 'Soil Testing Need', query: 'Kya mujhe soil testing karwani chahiye?', icon: '🔬', badge: 'Testing' },
  ];

  const telemetryScenarios: ScenarioOption[] = [
    { label: 'Soil Moisture', query: 'मेरे खेत में अभी मिट्टी की नमी कितनी है?', icon: '💧', badge: 'Telemetry' },
    { label: 'NPK Nutrients', query: 'मेरी मिट्टी में NPK कितना है?', icon: '🧪', badge: 'NPK' },
    { label: 'Compare 3 Zones', query: 'मेरे तीनों zones में किसकी soil condition सबसे अच्छी है?', icon: '📊', badge: 'Comparison' },
    { label: 'Device & Battery', query: 'मेरा FertoBot device online है? Battery kitni hai?', icon: '🔋', badge: 'Hardware' },
    { label: 'Water Tank Level', query: 'मेरे water tank mein kitna paani hai?', icon: '🚰', badge: 'Reservoir' },
    { label: '7-Day Trend', query: 'Pichhle 7 din mein moisture kaise change hui?', icon: '📈', badge: 'Trend' },
    { label: 'Active Alerts', query: 'Aaj mere farm mein kaun se alerts aaye?', icon: '⚠️', badge: 'Alerts' },
  ];

  const quickScenarios: ScenarioOption[] = [
    { label: 'Greeting', query: 'Hello!', icon: '👋' },
    { label: 'Hindi Greeting', query: 'नमस्ते, आप कैसे हैं?', icon: '🙏', badge: 'Hindi' },
    { label: 'Introduction', query: 'Who are you?', icon: '🤖' },
    { label: 'Capabilities', query: 'What can you do?', icon: '❓' },
    { label: 'Farm Status', query: 'Farm status', icon: '🌾' },
    { label: 'Goodbye', query: 'Goodbye!', icon: '🚪' },
  ];

  return (
    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-3.5 space-y-3">
      {/* Phase 14 Open-Domain Agronomic Intelligence Scenarios */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Sprout className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-300">
            Phase 14: Open-Domain Agricultural Intelligence & Dynamic Reasoning
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {phase14AgronomicScenarios.map((s, idx) => (
            <button
              key={idx}
              onClick={() => onSelectScenario(s.query)}
              disabled={disabled}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-200 border border-emerald-800/60 hover:border-emerald-500/60 transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed group"
            >
              <span>{s.icon}</span>
              <span>{s.label}</span>
              {s.badge && (
                <span className="ml-1 text-[9px] uppercase px-1.5 py-0.2 rounded bg-emerald-900/80 text-emerald-300 border border-emerald-700/60">
                  {s.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Simulated Telemetry Scenarios */}
      <div className="pt-2 border-t border-slate-800/60">
        <div className="flex items-center gap-2 mb-2">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-cyan-300">
            Live Telemetry Fast-Paths (&lt; 1ms Grounded Lookup)
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {telemetryScenarios.map((s, idx) => (
            <button
              key={idx}
              onClick={() => onSelectScenario(s.query)}
              disabled={disabled}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700/80 hover:border-cyan-500/50 transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span>{s.icon}</span>
              <span>{s.label}</span>
              {s.badge && (
                <span className="ml-1 text-[9px] uppercase px-1 py-0.2 rounded bg-slate-700 text-slate-300">
                  {s.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Quick Conversational Scenarios */}
      <div className="pt-2 border-t border-slate-800/60">
        <div className="flex items-center gap-2 mb-1.5">
          <Sparkles className="w-3 h-3 text-amber-400" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Conversational Controls
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {quickScenarios.map((s, idx) => (
            <button
              key={idx}
              onClick={() => onSelectScenario(s.query)}
              disabled={disabled}
              className="flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md bg-slate-800/50 hover:bg-slate-800 text-slate-300 border border-slate-700/50 hover:border-slate-600 transition-colors disabled:opacity-40"
            >
              <span>{s.icon}</span>
              <span>{s.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
