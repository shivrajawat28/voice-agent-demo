import React, { useState, useEffect } from 'react';
import { FarmOverview } from '../types/voiceAgent';
import {
  Activity,
  Droplets,
  Thermometer,
  Zap,
  Battery,
  AlertTriangle,
  RefreshCw,
  RotateCcw,
  Layers,
  MapPin,
  Info,
} from 'lucide-react';

interface FarmTelemetryDashboardProps {
  activeZoneId: string;
  onSelectZone: (zoneId: string) => void;
  onAskQuestion?: (query: string) => void;
}

export const FarmTelemetryDashboard: React.FC<FarmTelemetryDashboardProps> = ({
  activeZoneId,
  onSelectZone,
  onAskQuestion,
}) => {
  const [overview, setOverview] = useState<FarmOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const fetchOverview = async () => {
    try {
      setRefreshing(true);
      const res = await fetch('/api/farm/overview');
      if (!res.ok) throw new Error('Failed to fetch simulated farm overview');
      const data: FarmOverview = await res.json();
      setOverview(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Unable to load farm data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const handleZoneChange = async (zoneId: string) => {
    onSelectZone(zoneId);
    try {
      await fetch('/api/farm/active-zone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone_id: zoneId }),
      });
      fetchOverview();
    } catch (err) {
      console.error('Failed to set active zone:', err);
    }
  };

  const handleResetData = async () => {
    try {
      setRefreshing(true);
      await fetch('/api/farm/reset', { method: 'POST' });
      await fetchOverview();
    } catch (err) {
      console.error('Failed to reset dataset:', err);
    } finally {
      setRefreshing(false);
    }
  };

  if (error && !overview) {
    return (
      <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-4 text-xs text-rose-300 flex items-center justify-between">
        <span>{error}</span>
        <button onClick={fetchOverview} className="px-2.5 py-1 rounded bg-slate-800 text-white hover:bg-slate-700">
          Retry
        </button>
      </div>
    );
  }

  if (loading && !overview) {
    return (
      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 text-center text-slate-400 text-xs animate-pulse">
        Loading simulated farm telemetry environment...
      </div>
    );
  }

  const currentZone = overview?.zones.find((z) => z.zone_id === activeZoneId) || overview?.zones[0];
  const activeAlerts = overview?.active_alerts || [];
  const zoneAlerts = activeAlerts.filter((a) => a.zone_id === currentZone?.zone_id);

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 sm:p-5 text-xs space-y-4 shadow-xl">
      {/* Top Header: Farm Identity & Simulated Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-800/80">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-sm sm:text-base text-white tracking-tight flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-emerald-400" />
              {overview?.farm_name || 'Green Valley Agro Farm'}
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1">
              <Info className="w-3 h-3 text-amber-400" />
              Simulated FertoBot Telemetry
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-400 text-[11px]">
            <MapPin className="w-3 h-3 text-slate-500" />
            <span>{overview?.location || 'Sehore, MP, India'}</span>
            <span className="text-slate-600">•</span>
            <span>Farmer: {overview?.farmer_name || 'Ramesh Patel'}</span>
          </div>
        </div>

        {/* Management Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={fetchOverview}
            disabled={refreshing}
            className="flex items-center gap-1 px-2.5 py-1 text-slate-300 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors text-[11px]"
            title="Refresh sensor values"
          >
            <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin text-emerald-400' : ''}`} />
            Refresh
          </button>
          <button
            onClick={handleResetData}
            disabled={refreshing}
            className="flex items-center gap-1 px-2.5 py-1 text-slate-300 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors text-[11px]"
            title="Reset to default values"
          >
            <RotateCcw className="w-3 h-3 text-amber-400" />
            Reset
          </button>
        </div>
      </div>

      {/* Zone Selector Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        <span className="text-slate-400 font-semibold text-[11px] whitespace-nowrap">
          Target Zone:
        </span>
        {overview?.zones.map((zone) => {
          const isSelected = zone.zone_id === activeZoneId;
          const hasWarning = zone.device_status !== 'online' || zone.missing_fields.length > 0 || zone.soil_moisture_pct < 32;
          return (
            <button
              key={zone.zone_id}
              onClick={() => handleZoneChange(zone.zone_id)}
              className={`px-3 py-1.5 rounded-xl border font-medium text-xs transition-all whitespace-nowrap flex items-center gap-1.5 ${
                isSelected
                  ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-md shadow-emerald-500/10'
                  : 'bg-slate-800/50 border-slate-700/70 text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <span>{zone.zone_name}</span>
              <span className="text-[10px] text-slate-400">({zone.crop})</span>
              {hasWarning && (
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" title="Warning/Degraded status" />
              )}
            </button>
          );
        })}
      </div>

      {/* Main Telemetry Grid for Selected Zone */}
      {currentZone && (
        <div className="space-y-3">
          {/* Metadata banner */}
          <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5 rounded-lg bg-slate-800/40 border border-slate-800 text-[11px] text-slate-300">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white">{currentZone.zone_name}</span>
              <span className="text-slate-500">|</span>
              <span className="text-emerald-400">Crop: {currentZone.crop} ({currentZone.variety || 'Standard'}, {currentZone.growth_stage})</span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-400">Soil: {currentZone.soil_type}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                currentZone.completeness_ratio?.startsWith('7/7')
                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                  : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
              }`}>
                {currentZone.completeness_ratio || '7/7 parameters available'}
              </span>
              <span className="font-mono text-slate-400">Device: {currentZone.device_id}</span>
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                currentZone.device_status === 'online'
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
              }`}>
                {currentZone.device_status}
              </span>
            </div>
          </div>

          {/* Core Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {/* Soil Moisture */}
            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-[11px]">
                <span className="flex items-center gap-1">
                  <Droplets className="w-3.5 h-3.5 text-blue-400" />
                  Soil Moisture
                </span>
                <span className="text-[10px] font-mono">%</span>
              </div>
              <div className="text-lg font-bold text-white flex items-baseline gap-1">
                {currentZone.soil_moisture_pct.toFixed(1)}%
                <span className={`text-[10px] font-semibold ${
                  currentZone.soil_moisture_pct >= 40 && currentZone.soil_moisture_pct <= 58
                    ? 'text-emerald-400'
                    : currentZone.soil_moisture_pct < 35
                    ? 'text-amber-400'
                    : 'text-cyan-400'
                }`}>
                  {currentZone.soil_moisture_pct >= 40 && currentZone.soil_moisture_pct <= 58
                    ? 'Optimal'
                    : currentZone.soil_moisture_pct < 35
                    ? 'Moisture Stress'
                    : 'High Moisture'}
                </span>
              </div>
              {/* Moisture Bar */}
              <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    currentZone.soil_moisture_pct < 35
                      ? 'bg-amber-400'
                      : currentZone.soil_moisture_pct > 60
                      ? 'bg-cyan-400'
                      : 'bg-blue-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(0, currentZone.soil_moisture_pct))}%` }}
                />
              </div>
            </div>

            {/* Soil Temperature */}
            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-[11px]">
                <span className="flex items-center gap-1">
                  <Thermometer className="w-3.5 h-3.5 text-orange-400" />
                  Soil Temp
                </span>
                <span className="text-[10px] font-mono">°C (15cm)</span>
              </div>
              <div className="text-lg font-bold text-white">
                {currentZone.soil_temperature_c.toFixed(1)}°C
              </div>
              <div className="text-[10px] text-slate-400">
                Root zone thermal condition
              </div>
            </div>

            {/* pH & EC */}
            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-[11px]">
                <span className="flex items-center gap-1">
                  <Zap className="w-3.5 h-3.5 text-yellow-400" />
                  pH & Salinity
                </span>
                <span className="text-[10px] font-mono">pH / dS/m</span>
              </div>
              <div className="text-lg font-bold text-white flex items-baseline gap-2">
                <span>{currentZone.ph.toFixed(1)} <span className="text-[10px] text-slate-400 font-normal">pH</span></span>
                <span className="text-slate-600">/</span>
                <span className={currentZone.electrical_conductivity_ds_m > 2.0 ? 'text-amber-300' : 'text-slate-200'}>
                  {currentZone.electrical_conductivity_ds_m.toFixed(1)} <span className="text-[10px] text-slate-400 font-normal">dS/m</span>
                </span>
              </div>
              <div className="text-[10px] text-slate-400">
                {currentZone.electrical_conductivity_ds_m > 2.0 ? 'Elevated salinity warning' : 'Normal conductivity'}
              </div>
            </div>

            {/* Hardware & Tank */}
            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-[11px]">
                <span className="flex items-center gap-1">
                  <Battery className="w-3.5 h-3.5 text-emerald-400" />
                  Tank & Battery
                </span>
                <span className="text-[10px] font-mono">%</span>
              </div>
              <div className="text-lg font-bold text-white flex items-baseline gap-2">
                <span>Tank: {currentZone.water_tank_level_pct.toFixed(0)}%</span>
                <span className="text-slate-600">/</span>
                <span className={currentZone.battery_level_pct < 20 ? 'text-rose-400 animate-pulse' : 'text-emerald-400'}>
                  Bat: {currentZone.battery_level_pct.toFixed(0)}%
                </span>
              </div>
              <div className="text-[10px] text-slate-400">
                {currentZone.battery_level_pct < 20 ? 'Critical battery warning!' : 'Solar harvester charging'}
              </div>
            </div>
          </div>

          {/* 7-in-1 Soil Parameters Spectrum */}
          <div className="p-3.5 rounded-xl bg-slate-800/30 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-300 text-xs flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-cyan-400" />
                Canonical 7-in-1 Soil Profile — Telemetry Spectrum
              </span>
              <span className="text-[10px] text-slate-400">
                Completeness: {currentZone.completeness_ratio || '7/7 parameters available'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
              {/* Nitrogen */}
              <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800/80">
                <span className="text-[11px] text-slate-400 block">1. Nitrogen (N)</span>
                {currentZone.nitrogen_mg_kg !== null ? (
                  <span className="text-sm font-bold text-white">
                    {currentZone.nitrogen_mg_kg.toFixed(1)} <span className="text-[10px] text-slate-400">mg/kg</span>
                  </span>
                ) : (
                  <span className="text-xs font-semibold text-amber-400 flex items-center justify-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Uncalibrated
                  </span>
                )}
                <span className="text-[10px] text-slate-500 block">
                  {currentZone.nitrogen_mg_kg !== null
                    ? currentZone.nitrogen_mg_kg < 45
                      ? 'Medium / Deficit'
                      : 'Adequate'
                    : 'Channel unavailable'}
                </span>
              </div>

              {/* Phosphorus */}
              <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800/80">
                <span className="text-[11px] text-slate-400 block">2. Phosphorus (P)</span>
                {currentZone.phosphorus_mg_kg !== null ? (
                  <span className="text-sm font-bold text-white">
                    {currentZone.phosphorus_mg_kg.toFixed(1)} <span className="text-[10px] text-slate-400">mg/kg</span>
                  </span>
                ) : (
                  <span className="text-xs font-semibold text-slate-400">N/A</span>
                )}
                <span className="text-[10px] text-slate-500 block">Root development</span>
              </div>

              {/* Potassium */}
              <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800/80">
                <span className="text-[11px] text-slate-400 block">3. Potassium (K)</span>
                {currentZone.potassium_mg_kg !== null ? (
                  <span className="text-sm font-bold text-white">
                    {currentZone.potassium_mg_kg.toFixed(1)} <span className="text-[10px] text-slate-400">mg/kg</span>
                  </span>
                ) : (
                  <span className="text-xs font-semibold text-slate-400">N/A</span>
                )}
                <span className="text-[10px] text-slate-500 block">Osmotic balance</span>
              </div>

              {/* EC raw & dS/m */}
              <div className="p-2 rounded-lg bg-slate-900/50 border border-slate-800/80">
                <span className="text-[11px] text-slate-400 block">7. Elec. Cond. (EC)</span>
                <span className="text-sm font-bold text-white">
                  {currentZone.electrical_conductivity_ds_m.toFixed(2)} <span className="text-[10px] text-slate-400">dS/m</span>
                </span>
                <span className="text-[10px] text-slate-500 block">
                  ({Math.round(currentZone.electrical_conductivity_ds_m * 1000)} µS/cm)
                </span>
              </div>
            </div>

            {/* Sodium Policy Disclaimer Note */}
            <div className="flex items-center justify-between px-2.5 py-1 rounded bg-slate-900/70 border border-slate-800 text-[10px] text-slate-400">
              <span className="flex items-center gap-1 text-slate-300">
                <Info className="w-3 h-3 text-cyan-400" />
                <strong>Sodium (Na):</strong> NOT measured by FertoBot 7-in-1 probe. EC reflects total bulk salts.
              </span>
              <span className="text-slate-500 hidden sm:inline">Wet chemistry lab test required for Na/SAR</span>
            </div>
          </div>

          {/* Active Warnings & Alerts Banner */}
          {(currentZone.warnings.length > 0 || zoneAlerts.length > 0) && (
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-amber-400">
                <AlertTriangle className="w-3.5 h-3.5" />
                Active Alerts for {currentZone.zone_name}:
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-slate-300 pl-1">
                {zoneAlerts.map((a) => (
                  <li key={a.alert_id}>
                    <strong className="text-amber-300">[{a.severity.toUpperCase()}] {a.title}:</strong> {a.message}
                  </li>
                ))}
                {currentZone.warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Quick Grounded Question Prompts */}
          {onAskQuestion && (
            <div className="flex items-center gap-1.5 flex-wrap pt-1 text-[11px]">
              <span className="text-slate-400 font-semibold">Try asking:</span>
              <button
                onClick={() => onAskQuestion('मेरे खेत की पूरी मिट्टी की रिपोर्ट बताओ')}
                className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/40 transition-colors font-medium"
              >
                पूरी मिट्टी रिपोर्ट (11-Point)
              </button>
              <button
                onClick={() => onAskQuestion('मेरी मिट्टी में सोडियम कितना है?')}
                className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700 transition-colors"
              >
                सोडियम कितना है?
              </button>
              <button
                onClick={() => onAskQuestion('मेरे खेत में अभी मिट्टी की नमी कितनी है?')}
                className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700 transition-colors"
              >
                नमी कितनी है?
              </button>
              <button
                onClick={() => onAskQuestion('मेरी मिट्टी में NPK कितना है?')}
                className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700 transition-colors"
              >
                NPK कितना है?
              </button>
              <button
                onClick={() => onAskQuestion('क्या मुझे अभी अपनी फसल में पानी देना चाहिए?')}
                className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700 transition-colors"
              >
                क्या अभी सिंचाई करें?
              </button>
              <button
                onClick={() => onAskQuestion('मेरे तीनों zones में किसकी soil condition सबसे अच्छी है?')}
                className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700 transition-colors"
              >
                तीनों zones की तुलना करो
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
