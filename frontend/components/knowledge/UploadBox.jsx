// components/knowledge/UploadBox.jsx

'use client';

import { useCallback, useRef, useState } from 'react';
import { UploadCloud, FileText, X } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { SUPPORTED_FILE_TYPES, MAX_FILE_SIZE_MB } from '@/lib/constants';
import { formatBytes } from '@/lib/utils';
import { toast } from '@/components/common/Toast';
import '@/styles/knowledge.css';

export function UploadBox({ onUpload, isUploading, progress }) {
  const inputRef = useRef(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [pendingFiles, setPendingFiles] = useState([]);

  const validateFiles = useCallback((files) => {
    const valid = [];
    Array.from(files).forEach((file) => {
      const extension = `.${file.name.split('.').pop().toLowerCase()}`;
      const sizeMb = file.size / (1024 * 1024);

      if (!SUPPORTED_FILE_TYPES.includes(extension)) {
        toast.error(`${file.name}: unsupported file type`);
        return;
      }
      if (sizeMb > MAX_FILE_SIZE_MB) {
        toast.error(`${file.name}: exceeds ${MAX_FILE_SIZE_MB}MB limit`);
        return;
      }
      valid.push(file);
    });
    return valid;
  }, []);

  const handleFiles = useCallback(
    (files) => {
      const valid = validateFiles(files);
      if (valid.length > 0) {
        setPendingFiles((prev) => [...prev, ...valid]);
      }
    },
    [validateFiles]
  );

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragActive(false);
    handleFiles(event.dataTransfer.files);
  };

  const removeFile = (index) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadClick = () => {
    if (pendingFiles.length === 0) return;
    onUpload(pendingFiles);
    setPendingFiles([]);
  };

  return (
    <div className="flex flex-col gap-3">
      <div
        className="upload-dropzone"
        data-active={isDragActive}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragActive(true);
        }}
        onDragLeave={() => setIsDragActive(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
      >
        <UploadCloud className="h-7 w-7 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium text-foreground">
            Drag and drop files, or click to browse
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Supports {SUPPORTED_FILE_TYPES.join(', ')} up to {MAX_FILE_SIZE_MB}MB each
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={SUPPORTED_FILE_TYPES.join(',')}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {pendingFiles.length > 0 ? (
        <div className="flex flex-col gap-2">
          {pendingFiles.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center justify-between rounded-md border border-border px-3 py-2"
            >
              <div className="flex items-center gap-2 overflow-hidden">
                <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate text-sm text-foreground">{file.name}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatBytes(file.size)}
                </span>
              </div>
              <button
                onClick={() => removeFile(index)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}

          <Button onClick={handleUploadClick} isLoading={isUploading} className="self-end">
            Upload {pendingFiles.length} file{pendingFiles.length > 1 ? 's' : ''}
          </Button>
        </div>
      ) : null}

      {isUploading && progress !== undefined ? (
        <div className="upload-progress-bar">
          <div className="upload-progress-bar-fill" style={{ width: `${progress}%` }} />
        </div>
      ) : null}
    </div>
  );
}
