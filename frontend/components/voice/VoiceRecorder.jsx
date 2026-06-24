// frontend/components/voice/VoiceRecorder.jsx

'use client';

import { Mic, Square, RotateCcw, Send } from 'lucide-react';
import { AudioWaveform } from '@/components/voice/AudioWaveform';
import { useVoiceRecorder, useVoiceTranscribe } from '@/hooks/useVoice';
import { cn } from '@/lib/utils';

function formatDuration(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

export function VoiceRecorder({ onTranscript, onAudioBlob, className }) {
  const { isRecording, audioBlob, duration, start, stop, reset } = useVoiceRecorder();
  const { transcript, isLoading, transcribe } = useVoiceTranscribe();

  const handleTranscribe = async () => {
    if (!audioBlob) return;
    const text = await transcribe(audioBlob);
    if (text) onTranscript?.(text);
    if (audioBlob) onAudioBlob?.(audioBlob);
  };

  return (
    <div className={cn('flex flex-col gap-4 rounded-xl border border-border bg-card p-5', className)}>
      <div className="flex flex-col items-center gap-4">
        <AudioWaveform isActive={isRecording} />

        {isRecording && (
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-destructive animate-pulse" />
            <span className="text-sm font-mono text-foreground">{formatDuration(duration)}</span>
          </div>
        )}

        {audioBlob && !isRecording && (
          <audio src={URL.createObjectURL(audioBlob)} controls className="w-full h-8 rounded" />
        )}

        <div className="flex items-center gap-3">
          {!isRecording && !audioBlob && (
            <button type="button" onClick={start}
              className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground hover:opacity-90 transition-opacity shadow-lg shadow-primary/20">
              <Mic className="h-5 w-5" />
            </button>
          )}

          {isRecording && (
            <button type="button" onClick={stop}
              className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive text-destructive-foreground hover:opacity-90 transition-opacity">
              <Square className="h-5 w-5" />
            </button>
          )}

          {audioBlob && !isRecording && (
            <>
              <button type="button" onClick={reset}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:bg-muted transition-colors">
                <RotateCcw className="h-4 w-4" />
              </button>
              <button type="button" onClick={handleTranscribe} disabled={isLoading}
                className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50">
                <Send className="h-5 w-5" />
              </button>
            </>
          )}
        </div>
      </div>

      {isLoading && (
        <p className="text-center text-xs text-muted-foreground animate-pulse">Transcribing…</p>
      )}

      {transcript && !isLoading && (
        <div className="rounded-md border border-border bg-muted/40 p-3">
          <p className="text-xs text-foreground leading-relaxed">{transcript}</p>
        </div>
      )}

      <p className="text-center text-[0.625rem] text-muted-foreground/50">
        {isRecording ? 'Recording… click stop when done' : audioBlob ? 'Click send to transcribe' : 'Click mic to start recording'}
      </p>
    </div>
  );
}
