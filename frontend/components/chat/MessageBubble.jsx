// frontend/components/chat/MessageBubble.jsx

'use client';

import { Sparkles, User, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button type="button" onClick={copy}
      className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-foreground transition-all">
      {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
    </button>
  );
}

export function ThinkingBubble() {
  return (
    <div className="chat-message" data-role="assistant">
      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Sparkles className="h-3.5 w-3.5" />
      </div>
      <div className="chat-bubble" data-role="assistant">
        <div className="flex items-center gap-1.5 py-0.5">
          <span className="chat-thinking-dot" />
          <span className="chat-thinking-dot" />
          <span className="chat-thinking-dot" />
        </div>
      </div>
    </div>
  );
}

export function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('chat-message group')} data-role={message.role}>
      <div className={cn(
        'flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full flex-shrink-0',
        isUser ? 'bg-muted text-foreground' : 'bg-primary/10 text-primary'
      )}>
        {isUser ? <User className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
      </div>

      <div className="flex flex-col gap-1 min-w-0">
        <div className="chat-bubble" data-role={message.role}>
          {isUser ? (
            <p className="text-sm leading-relaxed">{message.content}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }) {
                  return inline ? (
                    <code className={className} {...props}>{children}</code>
                  ) : (
                    <pre><code className={className} {...props}>{children}</code></pre>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {message.created_at && (
          <div className={cn('flex items-center gap-2 px-1', isUser && 'flex-row-reverse')}>
            <span className="text-[0.625rem] text-muted-foreground/60">
              {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            <CopyButton text={message.content} />
          </div>
        )}
      </div>
    </div>
  );
}
