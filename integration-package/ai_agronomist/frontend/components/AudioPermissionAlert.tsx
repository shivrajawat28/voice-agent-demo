import { AlertCircle, MicOff, Info } from 'lucide-react';
import { MicPermissionState, VoiceCapabilities } from '../types/voiceAgent';

interface AudioPermissionAlertProps {
  error: string | null;
  permission: MicPermissionState;
  capabilities: VoiceCapabilities;
  onDismissError?: () => void;
}

export const AudioPermissionAlert: React.FC<AudioPermissionAlertProps> = ({
  error,
  permission,
  capabilities,
  onDismissError,
}) => {
  if (permission === 'denied') {
    return (
      <div className="flex items-start gap-3 p-3.5 bg-red-950/40 border border-red-500/30 rounded-xl text-xs text-red-200">
        <MicOff className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="font-semibold text-red-300">Microphone Permission Blocked</p>
          <p className="mt-0.5 text-red-300/80 leading-relaxed">
            The browser blocked microphone access. Please enable microphone permissions in your site settings,
            or continue testing using the text input and scenario buttons below.
          </p>
        </div>
      </div>
    );
  }

  if (!capabilities.speechRecognitionSupported) {
    return (
      <div className="flex items-start gap-3 p-3.5 bg-amber-950/30 border border-amber-500/30 rounded-xl text-xs text-amber-200">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="font-semibold text-amber-300">Speech Recognition Unsupported in this Browser</p>
          <p className="mt-0.5 text-amber-300/80 leading-relaxed">
            Web Speech Recognition API is unavailable in this browser engine (recommended: Chrome or Chromium-based browsers).
            Text input and scenario simulation work at 100% fidelity.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-start justify-between gap-3 p-3.5 bg-red-950/40 border border-red-500/30 rounded-xl text-xs text-red-200">
        <div className="flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-300">Interaction Notice</p>
            <p className="mt-0.5 text-red-300/90 leading-relaxed">{error}</p>
          </div>
        </div>
        {onDismissError && (
          <button
            onClick={onDismissError}
            className="text-red-400 hover:text-red-200 text-[11px] font-semibold underline shrink-0"
          >
            Dismiss
          </button>
        )}
      </div>
    );
  }

  return null;
};
