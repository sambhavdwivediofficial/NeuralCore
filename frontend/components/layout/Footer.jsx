// components/layout/Footer.jsx

import { APP_NAME, APP_VERSION } from '@/lib/constants';

export function Footer() {
  return (
    <footer className="relative sticky bottom-0 z-10 border-t border-border bg-background px-4 py-2 md:h-11 md:py-0 text-2xs text-muted-foreground">
      {/* Desktop */}
      <div className="hidden h-full md:flex items-center justify-between">
        <span>
          {APP_NAME} v{APP_VERSION}
        </span>

        <span className="absolute left-1/2 -translate-x-1/2 whitespace-nowrap">
          Built &amp; Maintained by{" "}
          <a
            href="https://www.sambhavdwivedi.in"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-foreground transition-colors hover:text-primary hover:underline"
          >
            Sambhav Dwivedi
          </a>
        </span>

        <span className="flex items-center gap-1.5 whitespace-nowrap">
          <span className="status-dot bg-success" />
          All systems operational
        </span>
      </div>

      {/* Mobile */}
      <div className="flex flex-col gap-2 py-1 md:hidden">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate">
            {APP_NAME} v{APP_VERSION}
          </span>

          <span className="flex shrink-0 items-center gap-1.5 whitespace-nowrap">
            <span className="status-dot bg-success" />
            Operational
          </span>
        </div>

        <div className="text-center leading-tight">
          Built &amp; Maintained by{" "}
          <a
            href="https://www.sambhavdwivedi.in"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-foreground transition-colors hover:text-primary hover:underline"
          >
            Sambhav Dwivedi
          </a>
        </div>
      </div>
    </footer>
  );
}