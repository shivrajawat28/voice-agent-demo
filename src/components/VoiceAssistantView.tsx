import React, { useState } from 'react';
import {
  Bot,
  Mic,
  MicOff,
  Send,
  Volume2,
  VolumeX,
  FileCheck,
  HelpCircle,
  Droplets,
  Thermometer,
  Activity,
  Layers,
  Search,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { TranscriptView } from './TranscriptView';
import { UseVoiceAgentReturn } from '../hooks/useVoiceAgent';

interface RegisteredQuestion {
  id: string;
  ticketId: string;
  farmerName: string;
  crop: string;
  question: string;
  answer: string;
  priority: 'HIGH' | 'NORMAL' | 'URGENT';
  status: 'answered' | 'pending';
  timestamp: string;
  sensorSnapshot: {
    moisture: number;
    temp: number;
    pH: number;
    tank: number;
    nitrogen: number;
  };
}

interface VoiceAssistantViewProps {
  voiceAgent: UseVoiceAgentReturn;
}

export const VoiceAssistantView: React.FC<VoiceAssistantViewProps> = ({ voiceAgent }) => {
  const [subTab, setSubTab] = useState<'chat' | 'registry'>('chat');
  const [inputText, setInputText] = useState('');
  const [searchFilter, setSearchFilter] = useState('');
  const [voiceMuted, setVoiceMuted] = useState(false);
  const [testPlaying, setTestPlaying] = useState(false);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [regQuestionText, setRegQuestionText] = useState('');
  const [regPriority, setRegPriority] = useState<'NORMAL' | 'HIGH' | 'URGENT'>('NORMAL');

  const [registeredQuestions, setRegisteredQuestions] = useState<RegisteredQuestion[]>([
    {
      id: 'q-1',
      ticketId: 'FRM-20261030-8421',
      farmerName: 'Prince (Farm Lead)',
      crop: 'Wheat (गेहूं)',
      question: 'गेहूं में पहली सिंचाई (CRI अवस्था) पर यूरिया की कितनी मात्रा देनी चाहिए?',
      answer:
        'राम-राम किसान भाई! गेहूं में CRI (ताज मूल अवस्था, 20-25 DAS) पर पहली सिंचाई अत्यंत महत्वपूर्ण है। इस समय प्रति एकड़ 25 से 30 किलोग्राम यूरिया की टॉप-ड्रेसिंग करें। आपके खेत की वर्तमान मिट्टी नमी 48.2% है जो अनुकूल सीमा में है।',
      priority: 'HIGH',
      status: 'answered',
      timestamp: '30 Oct 2026, 11:20 AM',
      sensorSnapshot: {
        moisture: 48.2,
        temp: 24.5,
        pH: 6.8,
        tank: 78,
        nitrogen: 140,
      },
    },
    {
      id: 'q-2',
      ticketId: 'FRM-20261030-3195',
      farmerName: 'Prince (Farm Lead)',
      crop: 'Wheat (गेहूं)',
      question: 'पानी की टंकी और पंप की स्थिति क्या है, क्या हम आज शाम सिंचाई कर सकते हैं?',
      answer:
        'राम-राम किसान भाई! मुख्य पानी की टंकी में 78% पानी उपलब्ध है और सेक्टर B-3 का सिंचाई वॉल्व तैयार है। मिट्टी में अभी 48.2% नमी है, इसलिए आज शाम 45 मिनट के लिए ड्रिप सिंचाई पर्याप्त रहेगी।',
      priority: 'NORMAL',
      status: 'answered',
      timestamp: '30 Oct 2026, 02:45 PM',
      sensorSnapshot: {
        moisture: 48.2,
        temp: 24.5,
        pH: 6.8,
        tank: 78,
        nitrogen: 140,
      },
    },
  ]);

  const {
    state: agentState,
    transcript,
    lastError,
    micPermission,
    activeZoneId,
    setActiveZoneId,
    language,
    setLanguage,
    selectedVoice,
    setSelectedVoice,
    audioLevel,
    partialTranscript,
    startListening,
    finishListening,
    stopOrCancel,
    submitText,
    playbackState,
    currentSpeakingMsgId,
    currentSpeakingSentenceIndex,
    revealedSentenceCount,
    replayMessage,
    clearTranscript,
    repeatLastResponse,
    approvePumpAction,
    rejectPumpAction,
  } = voiceAgent;

  const isListening = agentState === 'listening';
  const isFinalizing = agentState === 'finalizing';
  const isProcessing = agentState === 'processing';

  const quickPrompts = [
    'गेहूँ में पहली सिंचाई कब करें?',
    'पानी की टंकी और पंप की स्थिति क्या है?',
    'यूरिया और डीएपी की सही मात्रा?',
    'मिट्टी का pH और सुधार उपाय?',
    'कोई चेतावनी या रोग का खतरा?',
    'मक्का में 40% नमी पर पानी देना चाहिए या नहीं?',
  ];

  const handleSend = (textToSend?: string) => {
    const q = textToSend || inputText;
    if (!q.trim()) return;
    submitText(q);
    setInputText('');
  };

  const handleTestVoice = async () => {
    if (testPlaying) return;
    setTestPlaying(true);
    try {
      const sampleUrl =
        selectedVoice === 'Deepak'
          ? '/samples/sample_1_deepak.wav'
          : '/samples/sample_1_nalini.wav';
      const audio = new Audio(sampleUrl);
      audio.onended = () => setTestPlaying(false);
      audio.onerror = () => setTestPlaying(false);
      await audio.play();
    } catch {
      setTestPlaying(false);
    }
  };

  const handleRegisterOfficialQuestion = () => {
    const q = regQuestionText.trim();
    if (!q) return;

    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    const dateStr = '20261030';
    const ticketId = `FRM-${dateStr}-${randomSuffix}`;

    const newRec: RegisteredQuestion = {
      id: `q-${Date.now()}`,
      ticketId,
      farmerName: 'Prince (Farm Lead)',
      crop: activeZoneId === 'DEMO-ZONE-002' ? 'Cotton' : activeZoneId === 'DEMO-ZONE-003' ? 'Tomato' : activeZoneId === 'DEMO-ZONE-004' ? 'Mustard' : 'Wheat',
      question: q,
      answer: 'सवाल दर्ज कर लिया गया है। AI कृषि मित्र इसका विश्लेषण कर रहा है...',
      priority: regPriority,
      status: 'pending',
      timestamp: new Date().toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }),
      sensorSnapshot: {
        moisture: 48.2,
        temp: 24.5,
        pH: 6.8,
        tank: 78,
        nitrogen: 140,
      },
    };

    setRegisteredQuestions((prev) => [newRec, ...prev]);
    submitText(`[आधिकारिक सवाल दर्ज: ${ticketId}] ${q}`);
    setRegQuestionText('');
    setShowRegisterModal(false);
  };

  const filteredQuestions = registeredQuestions.filter(
    (q) =>
      q.question.toLowerCase().includes(searchFilter.toLowerCase()) ||
      q.answer.toLowerCase().includes(searchFilter.toLowerCase()) ||
      q.ticketId.toLowerCase().includes(searchFilter.toLowerCase()) ||
      q.crop.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="space-y-5 max-w-5xl mx-auto pb-12 animate-fadeIn">
      {/* Top Hero Card (Matches Reference Screenshot 2) */}
      <div className="matte-card rounded-2xl p-5 sm:p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border border-slate-800/80">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 text-xs font-semibold mb-2">
            <Bot className="w-3.5 h-3.5" />
            <span>FERTOBOT GEMINI 3.8 AI BRAIN</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] text-emerald-300 font-mono">
              1,372 CROP RECORDS + 50 PROBES
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            फ़र्टोबॉट कृषि मित्र (AI Voice Assistant)
          </h1>
          <p className="text-xs text-slate-400 max-w-xl leading-relaxed mt-1">
            बोलकर या लिखकर खेती का कोई भी सवाल पूछें। AI के पास भारत की सभी फसलों और आपके खेत के
            सेंसर्स का लाइव डेटा उपलब्ध है।
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Crop / Zone Selector */}
          <div className="flex items-center gap-1.5 bg-[#0D131A] px-2.5 py-1.5 rounded-xl border border-slate-800">
            <Layers className="w-3.5 h-3.5 text-emerald-400" />
            <select
              value={activeZoneId}
              onChange={(e) => setActiveZoneId(e.target.value)}
              className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              <option value="DEMO-ZONE-001" className="bg-slate-900 text-white">
                गेहूं (Wheat) • Zone 1 (North)
              </option>
              <option value="DEMO-ZONE-002" className="bg-slate-900 text-white">
                कपास (Cotton) • Zone 2 (South)
              </option>
              <option value="DEMO-ZONE-003" className="bg-slate-900 text-white">
                टमाटर (Tomato) • Zone 3 (East)
              </option>
              <option value="DEMO-ZONE-004" className="bg-slate-900 text-white">
                सरसों / चना (Mustard/Gram) • Zone 4 (West)
              </option>
            </select>
          </div>

          {/* Language Toggle */}
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-[#0D131A] border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500 cursor-pointer"
          >
            <option value="hi-IN">🌐 हिंदी (Hindi)</option>
            <option value="en-US">English (US)</option>
            <option value="en-IN">English (India)</option>
            <option value="hi-Latn">Hinglish</option>
          </select>

          {/* Voice Selector */}
          <select
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
            className="bg-[#0D131A] border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-purple-300 font-mono focus:outline-none focus:border-purple-500 cursor-pointer"
          >
            {language === 'en-IN' || language === 'en-US' ? (
              <>
                <option value="Kaveri">Voice: Kaveri (Female)</option>
                <option value="Pranav">Voice: Pranav (Male)</option>
              </>
            ) : language === 'hi-Latn' ? (
              <>
                <option value="Poorvi">Voice: Poorvi (Female / Hinglish)</option>
                <option value="Nalini">Voice: Nalini (Hindi Female)</option>
                <option value="Deepak">Voice: Deepak (Hindi Male)</option>
              </>
            ) : (
              <>
                <option value="Nalini">Voice: Nalini (महिला / Female)</option>
                <option value="Deepak">Voice: Deepak (पुरुष / Male)</option>
              </>
            )}
          </select>

          {/* Test Voice Sample Button */}
          <button
            onClick={handleTestVoice}
            disabled={testPlaying}
            className="px-2.5 py-1.5 rounded-xl bg-purple-950/40 hover:bg-purple-900/50 border border-purple-800/60 text-xs text-purple-300 transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
            title="Play sample neural voice"
          >
            <Volume2 className="w-3.5 h-3.5" />
            <span>{testPlaying ? 'Playing...' : 'Test Voice'}</span>
          </button>

          {/* Voice Output Mute Toggle */}
          <button
            onClick={() => setVoiceMuted(!voiceMuted)}
            className={`p-2 rounded-xl border transition-colors cursor-pointer ${
              !voiceMuted
                ? 'bg-emerald-950/40 border-emerald-800/80 text-emerald-400'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
            title={!voiceMuted ? 'Voice playback active' : 'Voice muted'}
          >
            {!voiceMuted ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>

          {/* Register Question Button */}
          <button
            onClick={() => setShowRegisterModal(true)}
            className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-lg shadow-emerald-900/30 cursor-pointer"
          >
            <FileCheck className="w-4 h-4" />
            <span>सवाल रजिस्टर करें</span>
          </button>
        </div>
      </div>

      {/* 4 Live Telemetry Sensor Cards Strip (Matches Reference Screenshot 2) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="matte-card rounded-xl p-3 flex items-center gap-3 border border-slate-800/80">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
            <Droplets className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">
              मिट्टी की नमी
            </div>
            <div className="text-sm font-bold text-white flex items-center gap-1.5">
              <span>48.2%</span>
              <span className="text-[10px] text-emerald-400 font-normal">Sector B-3 • अनुकूल</span>
            </div>
          </div>
        </div>

        <div className="matte-card rounded-xl p-3 flex items-center gap-3 border border-slate-800/80">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <Thermometer className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">
              तापमान
            </div>
            <div className="text-sm font-bold text-white flex items-center gap-1.5">
              <span>24.5°C</span>
              <span className="text-[10px] text-slate-400 font-normal">अनुकूल</span>
            </div>
          </div>
        </div>

        <div className="matte-card rounded-xl p-3 flex items-center gap-3 border border-slate-800/80">
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">
              मिट्टी का pH & NPK
            </div>
            <div className="text-sm font-bold text-white flex items-center gap-1.5">
              <span>pH 6.8</span>
              <span className="text-[10px] text-slate-400 font-normal font-mono">
                N:140 P:24 K:185
              </span>
            </div>
          </div>
        </div>

        <div className="matte-card rounded-xl p-3 flex items-center gap-3 border border-slate-800/80">
          <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
            <Droplets className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">
              पानी की टंकी
            </div>
            <div className="text-sm font-bold text-white flex items-center gap-1.5">
              <span>78%</span>
              <span className="text-[10px] text-teal-400 font-normal">पंप तैयार</span>
            </div>
          </div>
        </div>
      </div>

      {/* Sub-Tabs: Chat vs Question Registry */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setSubTab('chat')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
            subTab === 'chat'
              ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/30'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <Bot className="w-3.5 h-3.5" />
          <span>बातचीत (Live AI Chat)</span>
        </button>

        <button
          onClick={() => setSubTab('registry')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
            subTab === 'registry'
              ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/30'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          }`}
        >
          <FileCheck className="w-3.5 h-3.5" />
          <span>दर्ज सवाल रजिस्टर ({registeredQuestions.length})</span>
        </button>
      </div>

      {/* SUB-VIEW 1: Conversational Chat */}
      {subTab === 'chat' && (
        <div className="space-y-4">
          {/* Quick Suggestions Chips (Screenshot 2 & 3) */}
          <div className="space-y-1.5">
            <div className="text-xs text-slate-500 flex items-center gap-1">
              <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
              <span>जल्दी पूछें (Quick Suggestions):</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {quickPrompts.map((p, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(p)}
                  className="px-2.5 py-1 rounded-lg bg-[#121820] hover:bg-[#161F2A] border border-slate-800 text-xs text-slate-300 transition-colors hover:border-slate-700 cursor-pointer"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Transcript Thread with Progressive Disclosure */}
          <TranscriptView
            transcript={transcript}
            currentSpeakingMsgId={currentSpeakingMsgId}
            currentSpeakingSentenceIndex={currentSpeakingSentenceIndex}
            playbackState={playbackState}
            revealedSentenceCount={revealedSentenceCount}
            onReplayMessage={replayMessage}
            onRepeatResponse={repeatLastResponse}
            onClearTranscript={clearTranscript}
            onStopSpeaking={stopOrCancel}
            onApprovePump={approvePumpAction}
            onRejectPump={rejectPumpAction}
          />

          {/* Active Speaking & Listening / Finalizing Live VU Meter Banner */}
          {(isListening || isFinalizing) && (
            <div
              className={`matte-card rounded-xl p-3 border ${
                isFinalizing
                  ? 'border-indigo-500/40 bg-indigo-950/20'
                  : 'border-rose-500/40 bg-rose-950/20'
              } flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fadeIn`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-8 h-8 rounded-lg ${
                    isFinalizing ? 'bg-indigo-600' : 'bg-rose-600'
                  } text-white flex items-center justify-center shrink-0 ${
                    isListening ? 'animate-pulse' : ''
                  }`}
                >
                  {isFinalizing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Mic className="w-4 h-4" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs font-bold ${
                        isFinalizing ? 'text-indigo-300' : 'text-rose-300'
                      } uppercase tracking-wide`}
                    >
                      {isFinalizing
                        ? 'ऑडियो विश्लेषण (Finalizing Speech...)'
                        : 'माइक्रोफोन सक्रिय (Listening via GNANI AI)'}
                    </span>
                    <span
                      className={`w-2 h-2 rounded-full ${
                        isFinalizing ? 'bg-indigo-500 animate-pulse' : 'bg-rose-500 animate-ping'
                      }`}
                    />
                  </div>
                  <p className="text-xs text-slate-300 italic mt-0.5">
                    {partialTranscript ||
                      (isFinalizing
                        ? 'अंतिम वाक्य तैयार किया जा रहा है...'
                        : 'अपनी आवाज़ में बोलें... फ़र्टोबॉट सुन रहा है...')}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Live VU meter bar */}
                <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
                  <div
                    className={`h-full ${
                      isFinalizing ? 'bg-indigo-500' : 'bg-rose-500'
                    } transition-all duration-75`}
                    style={{ width: `${Math.min(100, Math.round(audioLevel * 100))}%` }}
                  />
                </div>

                <button
                  onClick={finishListening}
                  disabled={isFinalizing}
                  className={`px-3 py-1 rounded-lg text-white text-xs font-semibold transition-colors flex items-center gap-1 ${
                    isFinalizing
                      ? 'bg-indigo-700/60 opacity-80 cursor-not-allowed'
                      : 'bg-emerald-600 hover:bg-emerald-500 cursor-pointer'
                  }`}
                >
                  {isFinalizing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{isFinalizing ? 'Finalizing...' : 'Done Speaking'}</span>
                </button>
                <button
                  onClick={stopOrCancel}
                  className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Microphone Permission Blocked Notice */}
          {micPermission === 'denied' && (
            <div className="matte-card rounded-xl p-3.5 border border-red-500/40 bg-red-950/30 flex items-start gap-3 animate-fadeIn">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div className="text-xs text-red-200">
                <p className="font-semibold text-red-300">माइक्रोफ़ोन अनुमति अवरुद्ध (Microphone Access Blocked)</p>
                <p className="text-red-300/80 mt-1 leading-relaxed">
                  ब्राउज़र ने माइक्रोफ़ोन की अनुमति ब्लॉक कर दी है। कृपया अपने ब्राउज़र के एड्रेस बार (URL bar) में लॉक 🔒 / साइट सेटिंग्स आइकन पर क्लिक करके 'Microphone' को 'Allow' (अनुमति दें) करें, फिर पेज को रीफ़्रेश करें।
                </p>
              </div>
            </div>
          )}

          {/* General Audio / Voice Error Alert */}
          {lastError && micPermission !== 'denied' && (
            <div className="matte-card rounded-xl p-3 border border-amber-500/40 bg-amber-950/20 flex items-start gap-2.5 animate-fadeIn">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="text-xs text-amber-200 flex-1">
                <span className="font-semibold text-amber-300">ऑडियो सूचना: </span>
                <span>{lastError}</span>
              </div>
            </div>
          )}

          {/* Bottom Voice & Text Input Bar (Matches Reference Screenshot 3) */}
          <div className="matte-card rounded-xl p-2.5 flex items-center gap-2 border border-slate-800 shadow-md">
            <button
              onClick={() => {
                if (isListening) {
                  finishListening();
                } else if (!isFinalizing && !isProcessing) {
                  startListening();
                }
              }}
              disabled={isFinalizing}
              className={`p-2.5 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer ${
                isFinalizing
                  ? 'bg-indigo-700/70 text-white cursor-not-allowed'
                  : isListening
                  ? 'bg-rose-600 text-white animate-pulse shadow-lg shadow-rose-900/50'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
              title={
                isFinalizing
                  ? 'आवाज़ प्रोसेस हो रही है...'
                  : isListening
                  ? 'माइक बंद करें'
                  : 'बोलकर पूछें (Click to speak)'
              }
            >
              {isFinalizing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : isListening ? (
                <MicOff className="w-4 h-4" />
              ) : (
                <Mic className="w-4 h-4" />
              )}
              {isFinalizing && (
                <span className="text-[10px] font-bold uppercase tracking-wider">Finalizing</span>
              )}
              {isListening && !isFinalizing && (
                <span className="text-[10px] font-bold uppercase tracking-wider">Listening</span>
              )}
            </button>

            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="अपनी फसल या खेत के बारे में कुछ भी पूछें... (या माइक दबाकर बोलें)"
              className="flex-1 bg-transparent px-2 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none"
            />

            <button
              onClick={() => handleSend()}
              disabled={!inputText.trim() || isProcessing}
              className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors disabled:opacity-40 flex items-center gap-1 text-xs cursor-pointer shadow-md shadow-emerald-900/30"
            >
              <span>भेजें</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: Registered Questions Registry */}
      {subTab === 'registry' && (
        <div className="space-y-4">
          <div className="matte-card rounded-2xl p-4 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-1">
              <Search className="w-4 h-4 text-slate-500 ml-1" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="सवाल, टिकट ID या फसल खोजें..."
                className="bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none flex-1"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">
                कुल दर्ज सवाल: {registeredQuestions.length}
              </span>
              <button
                onClick={() => setShowRegisterModal(true)}
                className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors flex items-center gap-1 cursor-pointer"
              >
                <FileCheck className="w-3.5 h-3.5" />
                <span>नया सवाल दर्ज करें</span>
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {filteredQuestions.length === 0 ? (
              <div className="matte-card rounded-2xl p-8 text-center text-slate-400 text-xs border border-slate-800">
                कोई सवाल नहीं मिला। नया सवाल दर्ज करने के लिए ऊपर दिए गए बटन पर क्लिक करें।
              </div>
            ) : (
              filteredQuestions.map((q) => (
                <div
                  key={q.id}
                  className="matte-card rounded-2xl p-4 sm:p-5 border border-slate-800/80 space-y-3 hover:border-slate-700 transition-colors"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-400 text-xs font-mono font-semibold">
                        {q.ticketId}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/80 text-emerald-300 text-xs font-medium">
                        🌾 {q.crop}
                      </span>
                      <span
                        className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-bold ${
                          q.priority === 'HIGH'
                            ? 'bg-rose-950/60 text-rose-300 border border-rose-800/60'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {q.priority}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-400 font-mono">{q.timestamp}</div>
                  </div>

                  <div className="space-y-1">
                    <div className="text-xs font-semibold text-slate-200">
                      सवाल: <span className="font-normal text-white">{q.question}</span>
                    </div>
                    <div className="text-xs text-slate-300 pt-1 leading-relaxed bg-[#0D131A] p-2.5 rounded-xl border border-slate-800">
                      {q.answer}
                    </div>
                  </div>

                  {/* Sensor Snapshot at time of question */}
                  <div className="pt-2 border-t border-slate-800/60 flex flex-wrap items-center gap-3 text-[10px] text-slate-400 font-mono">
                    <span>नमी: {q.sensorSnapshot.moisture}%</span>
                    <span>•</span>
                    <span>तापमान: {q.sensorSnapshot.temp}°C</span>
                    <span>•</span>
                    <span>pH: {q.sensorSnapshot.pH}</span>
                    <span>•</span>
                    <span>टंकी: {q.sensorSnapshot.tank}%</span>
                    <span>•</span>
                    <span>N: {q.sensorSnapshot.nitrogen} ppm</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Register Question Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="matte-card w-full max-w-lg rounded-2xl p-6 border border-slate-700 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-emerald-400" />
                <span>नया कृषि सवाल दर्ज करें (Official Registry)</span>
              </h3>
              <button
                onClick={() => setShowRegisterModal(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 font-medium mb-1">फसल / ज़ोन</label>
                <div className="p-2 rounded-lg bg-[#0D131A] border border-slate-800 text-slate-200 font-mono">
                  {activeZoneId} (गेहूं / Wheat) • Sensor B-3 (Moisture: 48.2%)
                </div>
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">प्राथमिकता (Priority)</label>
                <select
                  value={regPriority}
                  onChange={(e) => setRegPriority(e.target.value as any)}
                  className="w-full bg-[#0D131A] border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="NORMAL">सामान्य (Normal)</option>
                  <option value="HIGH">महत्वपूर्ण (High)</option>
                  <option value="URGENT">अति-आवश्यक (Urgent)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">
                  आपका कृषि प्रश्न (Question Description)
                </label>
                <textarea
                  rows={4}
                  value={regQuestionText}
                  onChange={(e) => setRegQuestionText(e.target.value)}
                  placeholder="अपनी समस्या या सवाल का विवरण लिखें..."
                  className="w-full bg-[#0D131A] border border-slate-800 rounded-lg p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowRegisterModal(false)}
                className="px-3.5 py-1.5 rounded-lg text-slate-400 hover:text-white text-xs cursor-pointer"
              >
                रद्द करें
              </button>
              <button
                onClick={handleRegisterOfficialQuestion}
                disabled={!regQuestionText.trim()}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors disabled:opacity-50 cursor-pointer shadow-md shadow-emerald-900/30"
              >
                दर्ज करें व उत्तर पाएं
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
