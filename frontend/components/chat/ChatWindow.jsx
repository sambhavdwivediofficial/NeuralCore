// frontend/components/chat/ChatWindow.jsx

'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Send, Square, RotateCcw, BookOpen } from 'lucide-react';
import { MessageBubble, ThinkingBubble } from '@/components/chat/MessageBubble';
import { SourceCitations } from '@/components/chat/SourceCitations';
import { PipelineSelector } from '@/components/chat/PipelineSelector';
import { usePipelineRun } from '@/hooks/usePipelines';
import { cn } from '@/lib/utils';

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <BookOpen className="h-7 w-7" />
      </div>
      <div className="flex flex-col gap-1.5">
        <h3 className="text-sm font-semibold text-foreground">Ask your knowledge base</h3>
        <p className="text-xs text-muted-foreground max-w-xs">
          Ask any question and NeuralCore will retrieve relevant context and generate a grounded answer.
        </p>
      </div>
    </div>
  );
}

export function ChatWindow({ knowledgeBaseId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [pipelineType, setPipelineType] = useState('rag');
  const { run, isLoading, reset } = usePipelineRun();
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const adjustHeight = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const handleSend = useCallback(async () => {
    const query = input.trim();
    if (!query || isLoading) return;

    const userMsg = { role: 'user', content: query, created_at: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    try {
      const result = await run({ query, knowledge_base_id: knowledgeBaseId, pipeline_type: pipelineType });
      const assistantMsg = {
        role: 'assistant',
        content: result.answer ?? 'No answer returned.',
        sources: result.sources ?? [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'Something went wrong. Please try again.',
        sources: [],
        created_at: new Date().toISOString(),
      }]);
    }
  }, [input, isLoading, run, knowledgeBaseId, pipelineType]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => { setMessages([]); reset(); };

  return (
    <div className="chat-main">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5 bg-card/50">
        <PipelineSelector value={pipelineType} onChange={setPipelineType} />
        {messages.length > 0 && (
          <button type="button" onClick={clearChat}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <RotateCcw className="h-3 w-3" /> Clear
          </button>
        )}
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map((msg, i) => (
            <div key={i} className="flex flex-col gap-1.5">
              <MessageBubble message={msg} />
              {msg.role === 'assistant' && msg.sources?.length > 0 && (
                <div className="pl-10">
                  <SourceCitations sources={msg.sources} />
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && <ThinkingBubble />}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-box">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); adjustHeight(); }}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your knowledge base… (Enter to send, Shift+Enter for new line)"
            rows={1}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={isLoading ? undefined : handleSend}
            disabled={(!input.trim() && !isLoading)}
            className={cn(
              'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md transition-colors',
              input.trim() && !isLoading
                ? 'bg-primary text-primary-foreground hover:opacity-90'
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            )}
          >
            {isLoading ? <Square className="h-3.5 w-3.5" /> : <Send className="h-3.5 w-3.5" />}
          </button>
        </div>
        <p className="mt-1.5 text-center text-[0.625rem] text-muted-foreground/50">
          NeuralCore can make mistakes. Verify important information from sources.
        </p>
      </div>
    </div>
  );
}
