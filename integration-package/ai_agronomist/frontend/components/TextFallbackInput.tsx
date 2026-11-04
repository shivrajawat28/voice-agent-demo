import { useState } from 'react';
import { Send } from 'lucide-react';

interface TextFallbackInputProps {
  onSubmit: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const TextFallbackInput: React.FC<TextFallbackInputProps> = ({
  onSubmit,
  disabled = false,
  placeholder = 'Type a message here (fallback for mic)...',
}) => {
  const [inputVal, setInputVal] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputVal.trim();
    if (trimmed && !disabled) {
      onSubmit(trimmed);
      setInputVal('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          disabled={disabled}
          placeholder={placeholder}
          className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all disabled:opacity-50"
        />
      </div>

      <button
        type="submit"
        disabled={disabled || !inputVal.trim()}
        className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-slate-50 text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-emerald-950"
      >
        <span>Send</span>
        <Send className="w-3.5 h-3.5" />
      </button>
    </form>
  );
};
