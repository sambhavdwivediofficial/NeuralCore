// components/common/SearchBar.jsx

'use client';

import { useEffect, useState } from 'react';
import { Search, X } from 'lucide-react';
import { cn, debounce } from '@/lib/utils';

export function SearchBar({ value, onChange, placeholder = 'Search', className, debounceMs = 300 }) {
  const [internalValue, setInternalValue] = useState(value || '');

  useEffect(() => {
    setInternalValue(value || '');
  }, [value]);

  useEffect(() => {
    const handler = debounce((next) => onChange(next), debounceMs);
    if (internalValue !== value) {
      handler(internalValue);
    }
  }, [internalValue]);

  return (
    <div className={cn('relative flex items-center', className)}>
      <Search className="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-muted-foreground" />
      <input
        type="text"
        value={internalValue}
        onChange={(event) => setInternalValue(event.target.value)}
        placeholder={placeholder}
        className="h-9 w-full rounded-md border border-input bg-transparent pl-8 pr-8 text-sm shadow-xs placeholder:text-muted-foreground focus-ring"
      />
      {internalValue ? (
        <button
          type="button"
          onClick={() => {
            setInternalValue('');
            onChange('');
          }}
          className="absolute right-2.5 text-muted-foreground transition-colors hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      ) : null}
    </div>
  );
}
