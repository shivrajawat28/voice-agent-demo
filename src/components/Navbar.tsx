import React, { useState } from 'react';
import {
  Sprout,
  LayoutDashboard,
  Droplets,
  Radio,
  Camera,
  Bot,
  FileSpreadsheet,
  Sparkles,
  Settings,
  CloudSun,
  Activity,
  Flame,
  CloudRain,
  RotateCcw,
  ShieldAlert,
  Menu,
  X,
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  healthScore?: number;
  weatherLocation?: string;
  weatherTemp?: string;
  onSimulateRain?: () => void;
  onSimulateDepletion?: () => void;
  onSimulateIntrusion?: () => void;
  onResetSim?: () => void;
  currentLanguage?: string;
  onLanguageChange?: (lang: string) => void;
  llmProvider?: string;
  gnaniConfigured?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  healthScore = 88,
  weatherLocation = 'Jaipur, Rajasthan',
  weatherTemp = '25°C',
  onSimulateRain,
  onSimulateDepletion,
  onSimulateIntrusion,
  onResetSim,
  currentLanguage = 'hi-IN',
  onLanguageChange,
  llmProvider = 'gemini',
  gnaniConfigured = true,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'irrigation', label: 'Irrigation', icon: Droplets },
    { id: 'probes', label: 'Probes', icon: Radio },
    { id: 'security', label: 'Security', icon: Camera },
    { id: 'voice', label: 'Agronomist', icon: Bot, badge: 'AI' },
    { id: 'reports', label: 'Reports', icon: FileSpreadsheet },
    { id: 'features', label: 'Feature Studio', icon: Sparkles, badge: 'Type' },
    { id: 'profile', label: 'Farm Settings', icon: Settings },
  ];

  const handleTabClick = (id: string) => {
    setActiveTab(id);
    setMobileMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-40 bg-[#0E141B] border-b border-slate-800">
      {/* Top Status & Simulation Strip */}
      <div className="px-4 sm:px-6 py-1.5 bg-[#0A0E13] border-b border-slate-800/80 text-[11px] flex flex-wrap items-center justify-between text-slate-400 gap-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span>SIMULATED NODES (DEMO MODE)</span>
          </div>

          <span className="text-slate-700 hidden sm:inline">•</span>
          <div className="hidden sm:flex items-center gap-1 text-slate-300">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>
              Health: <strong className="text-white font-mono">{healthScore}%</strong>
            </span>
          </div>

          <span className="text-slate-700 hidden md:inline">•</span>
          <div className="hidden md:flex items-center gap-1 text-slate-400">
            <CloudSun className="w-3.5 h-3.5 text-slate-400" />
            <span>
              {weatherLocation} • {weatherTemp}
            </span>
          </div>

          <span className="text-slate-700 hidden lg:inline">•</span>
          <div className="hidden lg:flex items-center gap-1.5 text-[10px] font-mono">
            <span className="text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              {llmProvider.toUpperCase()} AI
            </span>
            <span className="text-slate-600">/</span>
            <span className="text-purple-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
              GNANI AI {gnaniConfigured ? '(Live)' : '(Demo)'}
            </span>
          </div>
        </div>

        {/* Simulation Action Controls Strip */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-slate-500 font-mono hidden lg:inline mr-1">SIM:</span>
          <button
            onClick={onSimulateRain}
            title="Simulate Rain Shower (+Moisture)"
            className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-blue-300 text-[10px] flex items-center gap-1 transition-colors cursor-pointer"
          >
            <CloudRain className="w-3 h-3 text-blue-400" />
            <span>+ Rain</span>
          </button>
          <button
            onClick={onSimulateDepletion}
            title="Simulate Nutrient Drop (-NPK)"
            className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-amber-300 text-[10px] flex items-center gap-1 transition-colors cursor-pointer"
          >
            <Flame className="w-3 h-3 text-amber-400" />
            <span>- NPK</span>
          </button>
          <button
            onClick={onSimulateIntrusion}
            title="Simulate CCTV Motion Intrusion"
            className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-rose-300 text-[10px] flex items-center gap-1 transition-colors cursor-pointer"
          >
            <ShieldAlert className="w-3 h-3 text-rose-400" />
            <span>! Intruder</span>
          </button>
          <button
            onClick={onResetSim}
            title="Reset Simulation to Initial Benchmarks"
            className="p-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleTabClick('dashboard')}
            className="flex items-center gap-2.5 text-left cursor-pointer"
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold shadow-md shadow-emerald-900/30">
              <Sprout className="w-4.5 h-4.5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-1 tracking-tight">
                Ferto<span className="text-emerald-400">Bot</span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono hidden sm:block">
                Prince AgriTech Hub
              </div>
            </div>
          </button>
        </div>

        {/* Desktop Navigation Tabs */}
        <nav className="hidden lg:flex items-center gap-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-emerald-600/20 text-emerald-400 font-semibold border border-emerald-500/30 shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <Icon
                  className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`}
                />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`text-[9px] font-bold px-1 py-0.2 rounded ${
                      isActive
                        ? 'bg-emerald-500 text-slate-950 font-mono'
                        : 'bg-slate-800 text-emerald-400 border border-slate-700'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right Controls */}
        <div className="flex items-center gap-2.5">
          {/* Language Selector */}
          <select
            value={currentLanguage}
            onChange={(e) => onLanguageChange && onLanguageChange(e.target.value)}
            className="bg-[#0D131A] border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-emerald-500 cursor-pointer"
          >
            <option value="hi-IN">हिन्दी (Hindi)</option>
            <option value="en-US">English (US)</option>
            <option value="en-IN">English (India)</option>
            <option value="hi-Latn">Hinglish</option>
          </select>

          {/* User Profile Pill */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
            <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-xs">
              👨‍🌾
            </div>
            <div className="hidden sm:block text-left text-xs">
              <div className="font-semibold text-white truncate max-w-[110px]">Prince</div>
              <div className="text-[10px] text-slate-400 font-mono">Farm Lead</div>
            </div>
          </div>

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-1.5 rounded-lg text-slate-300 hover:bg-slate-800"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-[#0A0E13] border-t border-slate-800 p-3 grid grid-cols-2 sm:grid-cols-4 gap-1.5 animate-fadeIn">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id)}
                className={`p-2 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors ${
                  isActive
                    ? 'bg-emerald-600/20 text-emerald-400 font-bold border border-emerald-500/30'
                    : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <Icon className="w-4 h-4 text-emerald-400" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </header>
  );
};
