// frontend/services/voice.js

import { apiGet, apiPost, apiUpload } from '@/services/api';

export async function listVoices() {
  return apiGet('/voice/voices');
}

export async function transcribeAudio(formData) {
  return apiUpload('/voice/transcribe', formData);
}

export async function textToSpeech(payload) {
  return apiPost('/voice/speak', payload);
}

export async function voiceQuery(formData) {
  return apiUpload('/voice/query', formData);
}
