// frontend/components/vision/ImageUploadAnalyze.jsx

'use client';

import { useRef, useState } from 'react';
import { Upload, Image as ImageIcon, X, Scan, MessageSquare } from 'lucide-react';
import { useImageAnalyze } from '@/hooks/useVision';
import { cn } from '@/lib/utils';

export function ImageUploadAnalyze({ className }) {
  const { result, isLoading, analyze, extractText, reset } = useImageAnalyze();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [question, setQuestion] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const handleFile = (f) => {
    if (!f || !f.type.startsWith('image/')) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    reset();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const clearFile = () => {
    setFile(null);
    setPreview(null);
    reset();
    setQuestion('');
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {!file ? (
        <div
          className={cn('upload-dropzone cursor-pointer', isDragging && 'border-primary bg-primary/5')}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted text-muted-foreground">
            <ImageIcon className="h-5 w-5" />
          </div>
          <div className="flex flex-col gap-1 text-center">
            <p className="text-sm font-medium text-foreground">Drop an image or click to upload</p>
            <p className="text-xs text-muted-foreground">PNG, JPG, WEBP up to 20MB</p>
          </div>
          <input ref={inputRef} type="file" accept="image/*" className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])} />
        </div>
      ) : (
        <div className="relative rounded-lg overflow-hidden border border-border">
          <img src={preview} alt="Upload preview" className="w-full max-h-64 object-cover" />
          <button type="button" onClick={clearFile}
            className="absolute top-2 right-2 flex h-7 w-7 items-center justify-center rounded-full bg-background/80 backdrop-blur text-foreground hover:bg-background transition-colors">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {file && (
        <>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground">Question (optional)</label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <MessageSquare className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="What do you see in this image?"
                  className="h-9 w-full rounded-md border border-input bg-background pl-8 pr-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button type="button" onClick={() => analyze(file, question)} disabled={isLoading}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50">
              <MessageSquare className="h-3.5 w-3.5" />
              {isLoading ? 'Analyzing…' : 'Analyze image'}
            </button>
            <button type="button" onClick={() => extractText(file)} disabled={isLoading}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-xs font-medium text-foreground hover:bg-muted transition-colors disabled:opacity-50">
              <Scan className="h-3.5 w-3.5" />
              Extract text (OCR)
            </button>
          </div>
        </>
      )}

      {result && (
        <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
          {result.description && (
            <div className="flex flex-col gap-1">
              <span className="text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">Description</span>
              <p className="text-xs text-foreground leading-relaxed">{result.description}</p>
            </div>
          )}
          {result.answer && (
            <div className="flex flex-col gap-1">
              <span className="text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">Answer</span>
              <p className="text-xs text-foreground leading-relaxed">{result.answer}</p>
            </div>
          )}
          {result.text && (
            <div className="flex flex-col gap-1">
              <span className="text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">Extracted Text</span>
              <pre className="text-xs text-foreground whitespace-pre-wrap leading-relaxed font-mono bg-muted/40 rounded-md p-3 max-h-40 overflow-y-auto scrollbar-thin">
                {result.text}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
