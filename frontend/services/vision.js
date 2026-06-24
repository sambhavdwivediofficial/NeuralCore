// frontend/services/vision.js

import { apiUpload } from '@/services/api';

export async function analyzeImage(formData) {
  return apiUpload('/vision/analyze', formData);
}

export async function extractText(formData) {
  return apiUpload('/vision/ocr', formData);
}
