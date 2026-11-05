import React, { useState } from 'react';
import {
  Sprout,
  LayoutDashboard,
  MapPin,
  Droplets,
  Radio,
  Camera,
  Bot,
  FileSpreadsheet,
  Sparkles,
  Settings,
  LogOut,
  CloudSun,
  Activity,
  Flame,
  CloudRain,
  RotateCcw,
  ShieldAlert,
  Menu,
  X,
} from 'lucide-react';

export interface NavbarProps {
  currentLanguage?: string;
  onLanguageChange?: (lang: string) => void;
  llmProvider?: string;
  gnaniConfigured?: boolean;
  selectedVoice?: string;
  activeZoneId?: string;
  onZoneChange?: (zone: string) => void;
  onRepeatResponse?: () => void;
  onClearTranscript?: () => void;
  hasMessages?: boolean;
  gyaniAudioStatus?: string;
  onSimulateRain?: () => void;
  onSimulateDepletion?: () => void;
  onSimulateIntrusion?: () => void;
  onResetSim?: () => void;
  farmName?: string;
  weatherLocation?: string;
  weatherTemp?: string;
  healthScore?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentLanguage = 'hi-IN',
  onLanguageChange,
  activeZoneId = 'DEMO-ZONE-001',
  onSimulateRain,
  onSimulateDepletion,
  onSimulateIntrusion,
  onResetSim,
  farmName = 'Prince AgriTech Hub',
  weatherLocation = 'Varanasi, Uttar Pradesh',
  weatherTemp = '25°C',
  healthScore = 88,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('agronomist');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Original FertoBot navigation tabs, verified from git history and visual reference
  const navTabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'plots', label: 'Plots', icon: MapPin },
    { id: 'irrigation', label: 'Irrigation', icon: Droplets },
    { id: 'probes', label: 'Probes', icon: Radio },
    { id: 'security', label: 'Security', icon: Camera },
    { id: 'agronomist', label: 'Agronomist', icon: Bot, isAgent: true },
    { id: 'reports', label: 'Reports', icon: FileSpreadsheet },
    { id: 'features', label: 'Feature Studio', icon: Sparkles, badge: 'Type' },
    { id: 'profile', label: 'Farm Settings', icon: Settings },
  ];

  const handleTabClick = (tabId: string, tabLabel: string) => {
    if (tabId === 'agronomist') {
      setActiveTab('agronomist');
      setToastMessage(null);
    } else {
      // In standalone AI Agronomist showcase, keep the agronomist interface active
      // and provide polite context that this module connects in full farm deployment.
      setToastMessage(`${tabLabel} is connected in the full FertoBot deployment. Currently viewing the AI Agronomist showcase.`);
      setTimeout(() => {
        setToastMessage(null);
      }, 3500);
    }
    setMobileMenuOpen(false);
  };

  // Safe simulation triggers
  const triggerSimRain = () => {
    if (onSimulateRain) {
      onSimulateRain();
    } else {
      fetch('/api/farm/telemetry/simulate-condition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone_id: activeZoneId, condition_type: 'rain_shower' }),
      }).catch(() => {});
    }
    setToastMessage('Simulated rain shower triggered (+ Soil Moisture).');
    setTimeout(() => setToastMessage(null), 3000);
  };

  const triggerSimDepletion = () => {
    if (onSimulateDepletion) {
      onSimulateDepletion();
    } else {
      fetch('/api/farm/telemetry/simulate-condition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone_id: activeZoneId, condition_type: 'nitrogen_critical_depletion' }),
      }).catch(() => {});
    }
    setToastMessage('Simulated nutrient depletion triggered (- NPK Levels).');
    setTimeout(() => setToastMessage(null), 3000);
  };

  const triggerSimIntrusion = () => {
    if (onSimulateIntrusion) {
      onSimulateIntrusion();
    }
    setToastMessage('CCTV motion alert simulated in Sector B-3.');
    setTimeout(() => setToastMessage(null), 3000);
  };

  const triggerResetSim = () => {
    if (onResetSim) {
      onResetSim();
    } else {
      fetch('/api/farm/telemetry/simulate-condition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone_id: activeZoneId, condition_type: 'optimal_loam' }),
      }).catch(() => {});
    }
    setToastMessage('Telemetry simulation reset to standard baseline.');
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Map language codes to select options matching original FertoBot (EN, हिन्दी, etc.)
  const languageOptions = [
    { code: 'en-IN', label: 'EN' },
    { code: 'hi-IN', label: 'हिन्दी' },
    { code: 'hi-Latn', label: 'Hinglish' },
    { code: 'en-US', label: 'EN (US)' },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#0E141B] border-b border-slate-800 shadow-md">
      {/* Top Status & Simulation Bar (Original FertoBot Top Bar) */}
      <div className="px-4 sm:px-6 py-1.5 bg-[#0A0E13] border-b border-slate-800/80 text-[11px] flex flex-wrap items-center justify-between text-slate-400 gap-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-emerald-400 font-mono" title="Simulated IoT telemetry nodes (demo mode)">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>5 NODES ONLINE (DEMO)</span>
          </div>

          <span className="text-slate-700 hidden sm:inline">•</span>
          <div className="hidden sm:flex items-center gap-1 text-slate-300" title="Simulated station health score">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>
              Health: <strong className="text-white font-mono">{healthScore}%</strong>
            </span>
          </div>

          <span className="text-slate-700 hidden md:inline">•</span>
          <div className="hidden md:flex items-center gap-1 text-slate-400" title="Simulated agro-climatic context">
            <CloudSun className="w-3.5 h-3.5 text-slate-400" />
            <span>
              {weatherLocation} • {weatherTemp}
            </span>
          </div>
        </div>

        {/* Top Simulation Controls Strip */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-slate-500 font-mono hidden lg:inline mr-1">SIM:</span>
          <button
            onClick={triggerSimRain}
            title="Simulate Rain Shower"
            className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-blue-300 text-[10px] flex items-center gap-1 transition-colors cursor-pointer"
          >
            <CloudRain className="w-3 h-3 text-blue-400" />
            <span>+ Rain</span>
          </button>
          <button
            onClick={triggerSimDepletion}
            title="Simulate Nutrient Drop"
            className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-amber-300 text-[10px] flex items-center gap-1 transition-colors cursor-pointer"
          >
            <Flame className="w-3 h-3 text-amber-400" />
            <span>- NPK</span>
          </button>
          <button
            onClick={triggerSimIntrusion}
            title="Simulate CCTV Motion"
            className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-rose-300 text-[10px] flex items-center gap-1 transition-colors cursor-pointer"
          >
            <ShieldAlert className="w-3 h-3 text-rose-400" />
            <span>! Intruder</span>
          </button>
          <button
            onClick={triggerResetSim}
            title="Reset Simulation"
            className="p-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Main Original Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-2.5 text-left">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold shadow-md shadow-emerald-900/30">
              <Sprout className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-1 tracking-tight">
                Ferto <span className="text-emerald-400">Bot</span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono hidden sm:block">
                {farmName}
              </div>
            </div>
          </div>
        </div>

        {/* Desktop Navigation Tabs */}
        <nav className="hidden lg:flex items-center gap-1">
          {navTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = tab.id === activeTab;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id, tab.label)}
                title={isActive ? `${tab.label} (Active Experience)` : `${tab.label} (FertoBot Platform)`}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'bg-emerald-600/15 text-emerald-400 font-semibold border border-emerald-500/30 shadow-sm shadow-emerald-950/40'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span className="text-[9px] font-bold px-1 py-0.2 rounded bg-slate-800 text-emerald-400 border border-slate-700">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right Controls */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* Language selector */}
          <select
            value={currentLanguage}
            onChange={(e) => onLanguageChange && onLanguageChange(e.target.value)}
            className="bg-[#0D131A] border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-emerald-500 cursor-pointer"
          >
            {languageOptions.map((opt) => (
              <option key={opt.code} value={opt.code}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* User Profile Pill */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
            <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-xs">
              👨‍🌾
            </div>
            <div className="hidden sm:block text-left text-xs">
              <div className="font-semibold text-white truncate max-w-[100px]">Prince</div>
            </div>

            <button
              title="Sign Out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
            className="lg:hidden p-1.5 rounded-lg text-slate-300 hover:bg-slate-800 cursor-pointer"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Standalone Context / Info Toast */}
      {toastMessage && (
        <div className="bg-emerald-950/80 border-t border-b border-emerald-500/40 px-4 py-1.5 text-xs text-emerald-200 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>{toastMessage}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="text-emerald-400 hover:text-white text-[11px] font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-[#0A0E13] border-t border-slate-800 p-3 grid grid-cols-2 sm:grid-cols-4 gap-1.5 animate-fadeIn">
          {navTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = tab.id === activeTab;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id, tab.label)}
                className={`p-2 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-emerald-600/20 text-emerald-400 font-bold border border-emerald-500/30'
                    : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span className="text-[9px] font-bold px-1 rounded bg-slate-800 text-emerald-400 border border-slate-700 ml-auto">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </header>
  );
};
