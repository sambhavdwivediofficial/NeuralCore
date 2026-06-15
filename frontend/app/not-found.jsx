// app/not-found.jsx

import { FileQuestion } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { ROUTES } from '@/lib/routes';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <FileQuestion className="h-6 w-6" />
      </div>
      <div className="flex flex-col gap-1">
        <h1 className="text-base font-semibold text-foreground">Page not found</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          The page you are looking for does not exist or may have been moved.
        </p>
      </div>
      <Button asChild>
        <a href={ROUTES.DASHBOARD}>Return to dashboard</a>
      </Button>
    </div>
  );
}
