import React, { useState } from 'react';
import { Volume2, CheckCircle2, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

interface VoiceEvaluationPanelProps {
  currentVoice: string;
  onSelectVoice: (voice: string) => void;
}

interface AudioSample {
  id: string;
  title: string;
  voice: 'Nalini' | 'Deepak' | 'Kaveri' | 'Poorvi';
  language: string;
  duration: string;
  text: string;
  audioUrl: string;
}

const SAMPLES: AudioSample[] = [
  {
    id: 's1-nalini',
    title: '1. Hindi Greeting & Introduction (Nalini - Recommended)',
    voice: 'Nalini',
    language: 'Hindi (hi-IN)',
    duration: '4.96s',
    text: 'नमस्ते! मैं फर्टोबॉट हूँ। बताइए, मैं आपकी खेती में कैसे मदद कर सकता हूँ?',
    audioUrl: '/samples/sample_1_nalini.wav',
  },
  {
    id: 's1-deepak',
    title: '1b. Hindi Greeting & Introduction (Deepak - Male)',
    voice: 'Deepak',
    language: 'Hindi (hi-IN)',
    duration: '4.64s',
    text: 'नमस्ते! मैं फर्टोबॉट हूँ। बताइए, मैं आपकी खेती में कैसे मदद कर सकता हूँ?',
    audioUrl: '/samples/sample_1_deepak.wav',
  },
  {
    id: 's2-nalini',
    title: '2. Decimal Soil Moisture (Nalini)',
    voice: 'Nalini',
    language: 'Hindi (hi-IN)',
    duration: '3.20s',
    text: 'आपकी मिट्टी में नमी अड़तालीस दशमलव दो प्रतिशत है।',
    audioUrl: '/samples/sample_2_nalini.wav',
  },
  {
    id: 's2-deepak',
    title: '2b. Decimal Soil Moisture (Deepak)',
    voice: 'Deepak',
    language: 'Hindi (hi-IN)',
    duration: '3.20s',
    text: 'आपकी मिट्टी में नमी अड़तालीस दशमलव दो प्रतिशत है।',
    audioUrl: '/samples/sample_2_deepak.wav',
  },
  {
    id: 's3-nalini',
    title: '3. Soil pH Pronunciation (Nalini)',
    voice: 'Nalini',
    language: 'Hindi (hi-IN)',
    duration: '2.56s',
    text: 'आपकी मिट्टी का पीएच छह दशमलव आठ है।',
    audioUrl: '/samples/sample_3_nalini.wav',
  },
  {
    id: 's3-deepak',
    title: '3b. Soil pH Pronunciation (Deepak)',
    voice: 'Deepak',
    language: 'Hindi (hi-IN)',
    duration: '2.40s',
    text: 'आपकी मिट्टी का पीएच छह दशमलव आठ है।',
    audioUrl: '/samples/sample_3_deepak.wav',
  },
  {
    id: 's4-nalini',
    title: '4. Wheat Crop Advisory (Nalini)',
    voice: 'Nalini',
    language: 'Hindi (hi-IN)',
    duration: '4.64s',
    text: 'गेहूँ की फसल में सिंचाई का सही समय मिट्टी की नमी और मौसम पर निर्भर करता है।',
    audioUrl: '/samples/sample_4_nalini.wav',
  },
  {
    id: 's4-deepak',
    title: '4b. Wheat Crop Advisory (Deepak)',
    voice: 'Deepak',
    language: 'Hindi (hi-IN)',
    duration: '4.48s',
    text: 'गेहूँ की फसल में सिंचाई का सही समय मिट्टी की नमी और मौसम पर निर्भर करता है।',
    audioUrl: '/samples/sample_4_deepak.wav',
  },
  {
    id: 's5-nalini',
    title: '5. Device Battery & Online Status (Nalini)',
    voice: 'Nalini',
    language: 'Hindi (hi-IN)',
    duration: '3.68s',
    text: 'आपके डिवाइस की बैटरी बानवे प्रतिशत है और डिवाइस ऑनलाइन है।',
    audioUrl: '/samples/sample_5_nalini.wav',
  },
  {
    id: 's5-deepak',
    title: '5b. Device Battery & Online Status (Deepak)',
    voice: 'Deepak',
    language: 'Hindi (hi-IN)',
    duration: '3.52s',
    text: 'आपके डिवाइस की बैटरी बानवे प्रतिशत है और डिवाइस ऑनलाइन है।',
    audioUrl: '/samples/sample_5_deepak.wav',
  },
];

export const VoiceEvaluationPanel: React.FC<VoiceEvaluationPanelProps> = ({
  currentVoice,
  onSelectVoice,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [acceptedVoice, setAcceptedVoice] = useState<string | null>(null);

  const handleAcceptVoice = (voice: string) => {
    onSelectVoice(voice);
    setAcceptedVoice(voice);
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 overflow-hidden shadow-lg">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between px-4 py-3 cursor-pointer bg-slate-800/40 hover:bg-slate-800/70 transition"
      >
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <div>
            <span className="text-xs font-bold text-white tracking-wide">
              GNANI AI Neural Voice Evaluation & Sample Review Panel
            </span>
            <span className="text-[11px] text-slate-400 ml-2">
              (Listen to live-generated Timbre v2.5 Indian Hindi audio clips)
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {acceptedVoice ? (
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              {acceptedVoice} Accepted
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
              PENDING_USER_AUDIO_REVIEW
            </span>
          )}
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </div>

      {isOpen && (
        <div className="p-4 space-y-3.5 border-t border-slate-800/60 bg-slate-950/40 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-200">
            <span>
              <strong>Audio Provenance:</strong> Generated via official GNANI AI (Vachana) REST endpoint{' '}
              <code className="text-[11px] bg-slate-900 px-1 py-0.5 rounded">POST /api/v1/tts/inference</code> using Timbre v2.5 with natural Devanagari spoken numbers.
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleAcceptVoice('Nalini')}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition cursor-pointer flex items-center gap-1 ${
                  currentVoice === 'Nalini'
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <CheckCircle2 className="w-3 h-3" /> Set Nalini as Primary (Female)
              </button>
              <button
                onClick={() => handleAcceptVoice('Deepak')}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition cursor-pointer flex items-center gap-1 ${
                  currentVoice === 'Deepak'
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <CheckCircle2 className="w-3 h-3" /> Set Deepak as Primary (Male)
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {SAMPLES.map((sample) => (
              <div
                key={sample.id}
                className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200 text-xs flex items-center gap-1.5">
                    <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
                    {sample.title}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {sample.duration} • {sample.voice}
                  </span>
                </div>
                <p className="text-slate-300 text-[11px] italic bg-slate-950/60 p-2 rounded border border-slate-800/80">
                  "{sample.text}"
                </p>
                <audio
                  controls
                  preload="none"
                  src={sample.audioUrl}
                  className="w-full h-8 rounded"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
