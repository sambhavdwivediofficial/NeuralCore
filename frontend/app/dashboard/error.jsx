// app/dashboard/error.jsx

'use client';

import { useEffect } from 'react';
import { AlertTriangle, RotateCw } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';

export default function DashboardError({ error, reset }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <AppShell>
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <div className="flex flex-col gap-1">
          <h2 className="text-base font-semibold text-foreground">Unable to load dashboard</h2>
          <p className="max-w-sm text-sm text-muted-foreground">
            There was a problem fetching your workspace data. Please try again.
          </p>
        </div>
        <Button variant="outline" onClick={() => reset()}>
          <RotateCw className="h-3.5 w-3.5" />
          Try again
        </Button>
      </div>
    </AppShell>
  );
}
