// frontend/hooks/useVoice.js

import { useCallback, useEffect, useRef, useState } from 'react';
import * as voiceService from '@/services/voice';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export function useVoices() {
  const [voices, setVoices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    voiceService.listVoices()
      .then((data) => setVoices(Array.isArray(data) ? data : data.items ?? []))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return { voices, isLoading };
}

export function useVoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [duration, setDuration] = useState(0);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start(100);
      setIsRecording(true);
      setDuration(0);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
    } catch {
      toast.error('Microphone access denied');
    }
  }, []);

  const stop = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
    clearInterval(timerRef.current);
  }, []);

  const reset = useCallback(() => {
    setAudioBlob(null);
    setDuration(0);
  }, []);

  useEffect(() => () => clearInterval(timerRef.current), []);

  return { isRecording, audioBlob, duration, start, stop, reset };
}

export function useVoiceTranscribe() {
  const [transcript, setTranscript] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const transcribe = useCallback(async (audioBlob) => {
    setIsLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', audioBlob, 'recording.webm');
      const data = await voiceService.transcribeAudio(fd);
      setTranscript(data.text ?? '');
      return data.text;
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { transcript, isLoading, transcribe };
}
