// components/common/Table.jsx

import { cn } from '@/lib/utils';

export function Table({ className, ...props }) {
  return (
    <div className="w-full overflow-auto">
      <table className={cn('w-full caption-bottom text-sm', className)} {...props} />
    </div>
  );
}

export function TableHeader({ className, ...props }) {
  return <thead className={cn('border-b border-border', className)} {...props} />;
}

export function TableBody({ className, ...props }) {
  return <tbody className={cn('divide-y divide-border', className)} {...props} />;
}

export function TableFooter({ className, ...props }) {
  return (
    <tfoot className={cn('border-t border-border bg-muted/40 font-medium', className)} {...props} />
  );
}

export function TableRow({ className, ...props }) {
  return <tr className={cn('interactive-row', className)} {...props} />;
}

export function TableHead({ className, ...props }) {
  return (
    <th
      className={cn(
        'h-10 whitespace-nowrap px-3 text-left align-middle text-xs font-medium text-muted-foreground',
        className
      )}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }) {
  return <td className={cn('whitespace-nowrap px-3 py-3 align-middle', className)} {...props} />;
}

export function TableCaption({ className, ...props }) {
  return <caption className={cn('mt-3 text-xs text-muted-foreground', className)} {...props} />;
}