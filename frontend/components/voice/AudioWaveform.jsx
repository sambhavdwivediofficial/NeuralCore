// frontend/components/voice/AudioWaveform.jsx

'use client';

import { useEffect, useRef } from 'react';

export function AudioWaveform({ isActive = false, barCount = 32 }) {
  const barsRef = useRef([]);

  useEffect(() => {
    if (!isActive) {
      barsRef.current.forEach((bar) => {
        if (bar) bar.style.height = '4px';
      });
      return;
    }

    const intervals = barsRef.current.map((bar, i) => {
      if (!bar) return null;
      return setInterval(() => {
        const center = barCount / 2;
        const distFromCenter = Math.abs(i - center) / center;
        const maxH = (1 - distFromCenter * 0.6) * 28 + 4;
        const h = Math.random() * maxH + 4;
        bar.style.height = `${h}px`;
      }, 80 + Math.random() * 60);
    });

    return () => intervals.forEach((t) => t && clearInterval(t));
  }, [isActive, barCount]);

  return (
    <div className="flex items-center justify-center gap-0.5 h-10">
      {Array.from({ length: barCount }).map((_, i) => (
        <div
          key={i}
          ref={(el) => { barsRef.current[i] = el; }}
          className="w-1 rounded-full transition-all duration-75"
          style={{
            height: '4px',
            background: isActive
              ? `hsl(var(--primary) / ${0.4 + (i / barCount) * 0.6})`
              : 'hsl(var(--border))',
          }}
        />
      ))}
    </div>
  );
}
