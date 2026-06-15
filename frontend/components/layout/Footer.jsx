// components/layout/Footer.jsx

import { APP_NAME, APP_VERSION } from '@/lib/constants';

export function Footer() {
  return (
    <footer className="flex h-11 items-center justify-between border-t border-border px-4 text-2xs text-muted-foreground">
      <span>
        {APP_NAME} v{APP_VERSION}
      </span>
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span className="status-dot bg-success" />
          All systems operational
        </span>
      </div>
    </footer>
  );
}