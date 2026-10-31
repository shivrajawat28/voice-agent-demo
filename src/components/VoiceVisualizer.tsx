import React, { useEffect, useRef, useState } from 'react';
import { AgentState } from '../types/voiceAgent';
import { Mic, Volume2, Loader2, AlertCircle, Radio, Settings2, AlertTriangle } from 'lucide-react';
import { VoiceController } from '../services/VoiceController';

interface VoiceVisualizerProps {
  state: AgentState;
  onMicClick: () => void;
  onCancelClick: () => void;
  onDoneSpeaking?: () => void;
  audioLevel?: number; // 0.0 to 1.0
  waveformData?: Uint8Array;
  isSpeakingDetected?: boolean;
  partialTranscript?: string | null;
  selectedDeviceId?: string | null;
  onSelectDevice?: (deviceId: string) => void;
  disabled?: boolean;
}

export const VoiceVisualizer: React.FC<VoiceVisualizerProps> = ({
  state,
  onMicClick,
  onCancelClick,
  onDoneSpeaking,
  audioLevel = 0,
  waveformData,
  isSpeakingDetected = false,
  partialTranscript = null,
  selectedDeviceId = null,
  onSelectDevice,
  disabled = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [silenceDuration, setSilenceDuration] = useState<number>(0);
  const [availableDevices, setAvailableDevices] = useState<MediaDeviceInfo[]>([]);
  const [showDeviceMenu, setShowDeviceMenu] = useState<boolean>(false);

  // Enumerate audio input devices
  useEffect(() => {
    VoiceController.getAudioInputDevices().then((devices) => {
      setAvailableDevices(devices);
    });

    if (navigator.mediaDevices && navigator.mediaDevices.ondevicechange !== undefined) {
      navigator.mediaDevices.ondevicechange = () => {
        VoiceController.getAudioInputDevices().then(setAvailableDevices);
      };
    }
  }, []);

  // Timer and Silence detection while listening
  useEffect(() => {
    if (state !== 'listening') {
      setElapsedSeconds(0);
      setSilenceDuration(0);
      return;
    }

    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
      if (!isSpeakingDetected) {
        setSilenceDuration((prev) => prev + 1);
      } else {
        setSilenceDuration(0);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [state, isSpeakingDetected]);

  // Real-time Waveform Canvas rendering
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    const isListening = state === 'listening';
    const isSpeaking = state === 'speaking';

    if (isListening && waveformData && waveformData.length > 0) {
      const numBars = 32;
      const barWidth = (width / numBars) - 2;
      const step = Math.floor(waveformData.length / numBars);

      for (let i = 0; i < numBars; i++) {
        const val = waveformData[i * step] || 128;
        const normalized = Math.abs(val - 128) / 128; // 0.0 to 1.0
        const barHeight = Math.max(4, normalized * height * 1.5 + (isSpeakingDetected ? 8 : 2));

        const x = i * (barWidth + 2);
        const y = (height - barHeight) / 2;

        const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight);
        if (isSpeakingDetected) {
          gradient.addColorStop(0, '#10b981'); // Emerald
          gradient.addColorStop(1, '#059669');
        } else {
          gradient.addColorStop(0, '#f59e0b'); // Amber
          gradient.addColorStop(1, '#d97706');
        }

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();
      }
    } else if (isSpeaking) {
      // Gentle animated sine-wave pulse for speech playback
      const numBars = 32;
      const barWidth = (width / numBars) - 2;
      const now = performance.now() / 200;

      for (let i = 0; i < numBars; i++) {
        const wave = Math.sin(now + i * 0.4) * 0.5 + 0.5;
        const barHeight = Math.max(4, wave * height * 0.85);
        const x = i * (barWidth + 2);
        const y = (height - barHeight) / 2;

        const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight);
        gradient.addColorStop(0, '#38bdf8'); // Sky blue
        gradient.addColorStop(1, '#0284c7');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();
      }
    } else {
      // Idle baseline
      const numBars = 32;
      const barWidth = (width / numBars) - 2;
      for (let i = 0; i < numBars; i++) {
        const x = i * (barWidth + 2);
        const y = height / 2 - 1.5;
        ctx.fillStyle = '#334155'; // Slate-700
        ctx.fillRect(x, y, barWidth, 3);
      }
    }
  }, [state, waveformData, isSpeakingDetected]);

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getGlowStyles = () => {
    switch (state) {
      case 'listening':
        return isSpeakingDetected
          ? 'ring-4 ring-emerald-500/70 bg-emerald-500/20 text-emerald-400 scale-105 shadow-emerald-500/30'
          : 'ring-4 ring-amber-500/50 bg-amber-500/10 text-amber-400 scale-105 shadow-amber-500/20';
      case 'processing':
        return 'ring-4 ring-blue-500/50 bg-blue-500/10 text-blue-400';
      case 'speaking':
        return 'ring-4 ring-emerald-500/50 bg-emerald-500/10 text-emerald-400 scale-105';
      case 'error':
        return 'ring-4 ring-red-500/50 bg-red-500/10 text-red-400';
      case 'idle':
      default:
        return 'ring-1 ring-slate-700 bg-slate-900/80 text-slate-300 hover:ring-emerald-500/50 hover:text-emerald-400';
    }
  };

  const getStatusInstruction = () => {
    switch (state) {
      case 'listening':
        return `Listening... ${formatTimer(elapsedSeconds)}`;
      case 'processing':
        return 'Multi-agent reasoning in progress...';
      case 'speaking':
        return 'FertoBot speaking response...';
      case 'error':
        return 'Interaction error. Click Cancel or retry.';
      case 'idle':
      default:
        return 'Click microphone to start speaking';
    }
  };

  const isInteractive = state === 'idle' || state === 'error';

  return (
    <div className="flex flex-col items-center justify-center p-6 bg-slate-900/60 rounded-2xl border border-slate-800 backdrop-blur-sm relative">
      {/* Device selector trigger (top-right) */}
      {availableDevices.length > 0 && (
        <div className="absolute top-3 right-3">
          <button
            onClick={() => setShowDeviceMenu(!showDeviceMenu)}
            className="flex items-center gap-1.5 px-2 py-1 text-[11px] font-mono rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition-colors"
            title="Configure Microphone Input"
          >
            <Settings2 className="w-3.5 h-3.5 text-slate-400" />
            <span className="truncate max-w-[120px]">
              {availableDevices.find((d) => d.deviceId === selectedDeviceId)?.label || 'Microphone'}
            </span>
          </button>

          {showDeviceMenu && (
            <div className="absolute right-0 mt-1 w-64 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl p-2 z-50">
              <span className="text-[10px] uppercase font-semibold text-slate-400 px-2 py-1 block">
                Select Audio Input Device
              </span>
              <div className="space-y-1 mt-1">
                {availableDevices.map((dev) => (
                  <button
                    key={dev.deviceId}
                    onClick={() => {
                      onSelectDevice?.(dev.deviceId);
                      setShowDeviceMenu(false);
                    }}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs truncate transition-colors ${
                      selectedDeviceId === dev.deviceId
                        ? 'bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/40'
                        : 'text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    {dev.label || `Microphone ${dev.deviceId.slice(0, 5)}...`}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Main Microphone Button */}
      <div className="relative mb-3 mt-1">
        {(state === 'listening' || state === 'speaking') && (
          <div
            className={`absolute inset-0 rounded-full animate-ping opacity-25 ${
              isSpeakingDetected ? 'bg-emerald-500' : 'bg-current'
            }`}
          />
        )}

        <button
          onClick={
            isInteractive
              ? onMicClick
              : state === 'listening'
              ? (onDoneSpeaking || onCancelClick)
              : onCancelClick
          }
          disabled={disabled}
          title={
            isInteractive
              ? 'Start Voice Input'
              : state === 'listening'
              ? 'Finish Speaking & Process'
              : 'Cancel / Stop'
          }
          aria-label={
            isInteractive
              ? 'Start Voice Input'
              : state === 'listening'
              ? 'Finish Speaking & Process'
              : 'Cancel Voice Operation'
          }
          className={`relative w-28 h-28 rounded-full flex flex-col items-center justify-center transition-all duration-300 shadow-2xl ${getGlowStyles()} ${
            disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer active:scale-95'
          }`}
        >
          {state === 'listening' && (
            <Mic className={`w-10 h-10 ${isSpeakingDetected ? 'text-emerald-300 animate-pulse' : 'text-amber-400'}`} />
          )}
          {state === 'processing' && <Loader2 className="w-10 h-10 animate-spin text-blue-400" />}
          {state === 'speaking' && <Volume2 className="w-10 h-10 text-sky-400" />}
          {state === 'error' && <AlertCircle className="w-10 h-10 text-red-400" />}
          {state === 'idle' && <Mic className="w-10 h-10 text-slate-300 transition-transform group-hover:scale-110" />}

          <span className="text-[10px] uppercase font-bold tracking-wider mt-1 opacity-80">
            {isInteractive ? 'Speak' : state === 'listening' ? 'Done' : 'Cancel'}
          </span>
        </button>
      </div>

      {/* Real-time Waveform Canvas */}
      <div className="w-full max-w-xs h-10 mb-2 flex items-center justify-center">
        <canvas
          ref={canvasRef}
          width={280}
          height={36}
          className="rounded-lg bg-slate-950/60 border border-slate-800/80 shadow-inner"
        />
      </div>

      {/* Status Instruction and Speech Detection Badge */}
      <div className="flex items-center gap-2 mb-2">
        <p className="text-sm font-medium text-slate-200 tracking-wide text-center">
          {getStatusInstruction()}
        </p>

        {state === 'listening' && isSpeakingDetected && (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 animate-pulse">
            <Radio className="w-3 h-3 text-emerald-400" />
            SPEECH DETECTED
          </span>
        )}
      </div>

      {/* Real-time VU-Meter / Energy Level */}
      {state === 'listening' && (
        <div className="w-full max-w-xs mb-3 space-y-1">
          <div className="flex justify-between text-[10px] text-slate-400 font-mono">
            <span>MIC ENERGY</span>
            <span>{Math.round(audioLevel * 100)}%</span>
          </div>
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
            <div
              className={`h-full transition-all duration-75 rounded-full ${
                audioLevel > 0.6
                  ? 'bg-red-500'
                  : audioLevel > 0.3
                  ? 'bg-amber-400'
                  : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.min(100, Math.max(5, audioLevel * 100))}%` }}
            />
          </div>
        </div>
      )}

      {/* Real-time Partial / Interim Transcript Preview */}
      {state === 'listening' && partialTranscript && (
        <div className="w-full max-w-md p-2.5 mb-2 rounded-xl bg-slate-800/90 border border-emerald-500/40 text-emerald-200 text-xs shadow-md animate-fade-in flex items-start gap-2">
          <Radio className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5 animate-pulse" />
          <p className="italic">"{partialTranscript}..."</p>
        </div>
      )}

      {/* Silence Warning after 4 seconds of quiet */}
      {state === 'listening' && silenceDuration >= 4 && !partialTranscript && (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs mb-2 animate-bounce">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
          <span>No speech detected. Please speak into your microphone or click Stop.</span>
        </div>
      )}

      {/* Control Buttons */}
      <div className="flex items-center gap-3 mt-1">
        {state === 'idle' && (
          <button
            onClick={onMicClick}
            disabled={disabled}
            className="px-5 py-2 text-xs font-semibold rounded-lg bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors shadow-lg shadow-emerald-500/20 disabled:opacity-50 flex items-center gap-1.5"
          >
            <Mic className="w-3.5 h-3.5" />
            Start Listening
          </button>
        )}

        {state === 'listening' && (
          <div className="flex items-center gap-2">
            <button
              onClick={onDoneSpeaking || onCancelClick}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors shadow-md flex items-center gap-1.5 font-medium"
            >
              Done Speaking
            </button>
            <button
              onClick={onCancelClick}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-red-500/20 text-red-300 border border-red-500/40 hover:bg-red-500/30 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}

        {state !== 'idle' && state !== 'listening' && (
          <button
            onClick={onCancelClick}
            className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-red-500/20 text-red-300 border border-red-500/40 hover:bg-red-500/30 transition-colors"
          >
            Stop / Cancel
          </button>
        )}
      </div>
    </div>
  );
};
