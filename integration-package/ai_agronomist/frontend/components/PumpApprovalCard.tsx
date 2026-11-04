import React, { useState, useEffect } from 'react';
import { PumpActionPayload } from '../types/voiceAgent';
import { ShieldAlert, CheckCircle2, XCircle, Clock, Zap, AlertTriangle, Loader2 } from 'lucide-react';

interface PumpApprovalCardProps {
  action: PumpActionPayload;
  onApprove: (actionId: string) => Promise<void>;
  onReject: (actionId: string) => Promise<void>;
}

export const PumpApprovalCard: React.FC<PumpApprovalCardProps> = ({
  action,
  onApprove,
  onReject,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittingAction, setSubmittingAction] = useState<'approve' | 'reject' | null>(null);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(() => {
    const remaining = Math.max(0, Math.floor(action.expires_at - Date.now() / 1000));
    return remaining;
  });

  useEffect(() => {
    if (action.state !== 'AWAITING_USER_APPROVAL') return;

    const timer = setInterval(() => {
      const remaining = Math.max(0, Math.floor(action.expires_at - Date.now() / 1000));
      setSecondsRemaining(remaining);
      if (remaining <= 0) {
        clearInterval(timer);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [action.expires_at, action.state]);

  const isExpired = action.state === 'EXPIRED' || (action.state === 'AWAITING_USER_APPROVAL' && secondsRemaining <= 0);

  const formatCountdown = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `${mins}:${s.toString().padStart(2, '0')}`;
  };

  const handleApproveClick = async () => {
    if (isSubmitting || isExpired || action.state !== 'AWAITING_USER_APPROVAL') return;
    setIsSubmitting(true);
    setSubmittingAction('approve');
    try {
      await onApprove(action.action_id);
    } finally {
      setIsSubmitting(false);
      setSubmittingAction(null);
    }
  };

  const handleRejectClick = async () => {
    if (isSubmitting || isExpired || action.state !== 'AWAITING_USER_APPROVAL') return;
    setIsSubmitting(true);
    setSubmittingAction('reject');
    try {
      await onReject(action.action_id);
    } finally {
      setIsSubmitting(false);
      setSubmittingAction(null);
    }
  };

  return (
    <div className="mt-3 p-3.5 bg-gradient-to-br from-emerald-50/90 to-teal-50/70 border border-emerald-200 rounded-xl shadow-sm text-xs font-sans">
      {/* Header with Title and Mode Badge */}
      <div className="flex items-center justify-between pb-2 border-b border-emerald-200/70">
        <div className="flex items-center gap-1.5 font-bold text-emerald-950">
          <Zap className="w-4 h-4 text-emerald-600 fill-emerald-500" />
          <span>कृषि पंप नियंत्रण अनुमोदन (Pump Approval)</span>
        </div>
        <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100/90 text-emerald-800 border border-emerald-300 font-mono text-[10px] tracking-wide font-semibold">
          <ShieldAlert className="w-3 h-3 text-emerald-700" />
          <span>SIMULATED • ACTUATION OFF</span>
        </div>
      </div>

      {/* Target Zone & Action Metadata */}
      <div className="grid grid-cols-2 gap-2 my-2.5 py-1 px-2 bg-white/70 rounded-lg border border-emerald-100 text-slate-700">
        <div>
          <span className="text-slate-500 block text-[10px]">लक्ष्य क्षेत्र (Target Zone)</span>
          <span className="font-semibold text-slate-900">{action.zone_id}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px]">प्रस्तावित कार्रवाई (Action)</span>
          <span className="font-semibold text-emerald-700">
            {action.action_type === 'PUMP_ON' ? 'पंप चालू (PUMP ON)' : 'पंप बंद (PUMP OFF)'}
          </span>
        </div>
      </div>

      {/* State Renderers */}
      {action.state === 'AWAITING_USER_APPROVAL' && !isExpired && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-slate-600">
            <span className="text-[11px]">क्या आप इस सिंचाई आदेश की पुष्टि करते हैं?</span>
            <div className="flex items-center gap-1 text-[11px] font-mono text-amber-700 font-semibold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
              <Clock className="w-3.5 h-3.5" />
              <span>{formatCountdown(secondsRemaining)}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={handleApproveClick}
              disabled={isSubmitting}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white rounded-lg font-semibold shadow transition-colors active:scale-95"
            >
              {isSubmitting && submittingAction === 'approve' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5" />
              )}
              <span>हाँ, चालू करें</span>
            </button>
            <button
              onClick={handleRejectClick}
              disabled={isSubmitting}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 bg-white hover:bg-rose-50 disabled:bg-slate-50 text-rose-700 border border-rose-200 hover:border-rose-300 rounded-lg font-semibold transition-colors active:scale-95"
            >
              {isSubmitting && submittingAction === 'reject' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-600" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-rose-600" />
              )}
              <span>नहीं, रद्द करें</span>
            </button>
          </div>
        </div>
      )}

      {action.state === 'COMPLETED' && (
        <div className="p-2.5 bg-emerald-100/90 border border-emerald-300 rounded-lg flex items-start gap-2 text-emerald-950">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-[11px]">पंप सक्रिय (सिम्युलेटेड चालू)</div>
            <div className="text-[10px] text-emerald-800">
              अनुमोदन सत्यापित। सिम्युलेटेड पंप चल रहा है। सुरक्षा सीमा: भौतिक हार्डवेयर रिले सुरक्षित (आइसोलेटेड) है।
            </div>
          </div>
        </div>
      )}

      {action.state === 'REJECTED' && (
        <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2 text-rose-950">
          <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-[11px]">कार्रवाई रद्द (Action Cancelled)</div>
            <div className="text-[10px] text-rose-800">
              किसान द्वारा अनुरोध अस्वीकार कर दिया गया। पंप बंद रहेगा।
            </div>
          </div>
        </div>
      )}

      {isExpired && action.state !== 'COMPLETED' && action.state !== 'REJECTED' && (
        <div className="p-2.5 bg-amber-50 border border-amber-300 rounded-lg flex items-start gap-2 text-amber-950">
          <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-[11px]">समय सीमा समाप्त (Timed Out)</div>
            <div className="text-[10px] text-amber-800">
              5 मिनट की सुरक्षा विंडो में कोई इनपुट प्राप्त नहीं हुआ। अनुरोध स्वतः निरस्त किया गया।
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
