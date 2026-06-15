// app/error.jsx

'use client';

import { useEffect } from 'react';
import { AlertTriangle, RotateCw, Home } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { ROUTES } from '@/lib/routes';

export default function RootError({ error, reset }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <div className="flex flex-col gap-1">
        <h1 className="text-base font-semibold text-foreground">Something went wrong</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          An unexpected error occurred while rendering this page. You can try again or return to the
          dashboard.
        </p>
      </div>
      {error?.digest ? (
        <p className="kbd">Error ID: {error.digest}</p>
      ) : null}
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={() => reset()}>
          <RotateCw className="h-3.5 w-3.5" />
          Try again
        </Button>
        <Button asChild>
          <a href={ROUTES.DASHBOARD}>
            <Home className="h-3.5 w-3.5" />
            Go to dashboard
          </a>
        </Button>
      </div>
    </div>
  );
}
