// components/common/Toast.jsx

'use client';

import { Toaster, toast as hotToast } from 'react-hot-toast';
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { TOAST_DURATION } from '@/lib/constants';

export function ToastProvider() {
  return (
    <Toaster
      position="bottom-right"
      gutter={8}
      toastOptions={{
        duration: TOAST_DURATION,
      }}
    >
      {(t) => (
        <div
          className={`flex w-80 items-start gap-3 rounded-lg border border-border bg-card p-3.5 text-card-foreground shadow-lg transition-all ${
            t.visible ? 'animate-fade-in-up' : 'opacity-0'
          }`}
        >
          <ToastIcon type={t.type} customType={t.message?.props?.['data-type']} />
          <div className="flex-1 text-sm leading-snug">
            {typeof t.message === 'function' ? t.message(t) : t.message}
          </div>
          <button
            onClick={() => hotToast.dismiss(t.id)}
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </Toaster>
  );
}

function ToastIcon({ type, customType }) {
  const resolved = customType || type;

  if (resolved === 'success') return <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />;
  if (resolved === 'error') return <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />;
  if (resolved === 'warning') return <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />;
  return <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />;
}

export const toast = {
  success: (message) => hotToast.success(message),
  error: (message) => hotToast.error(message),
  info: (message) =>
    hotToast(
      () => <span data-type="info">{message}</span>,
      { icon: null }
    ),
  warning: (message) =>
    hotToast(
      () => <span data-type="warning">{message}</span>,
      { icon: null }
    ),
  promise: (promise, messages) => hotToast.promise(promise, messages),
  dismiss: (id) => hotToast.dismiss(id),
};
