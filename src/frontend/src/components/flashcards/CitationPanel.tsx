'use client';

import { Citation } from '@/lib/flashcards/types';

interface CitationPanelProps {
  citations: Citation[];
  className?: string;
}

export default function CitationPanel({ citations, className = '' }: CitationPanelProps) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className={`mt-4 p-4 bg-muted/50 rounded-lg border border-border ${className}`}>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
        📚 Nguồn tham khảo
      </h4>
      
      <div className="space-y-2">
        {citations.map((citation) => (
          <div
            key={citation.chunk_id}
            className="flex items-start gap-3 text-sm bg-card p-3 rounded border border-border hover:border-primary/50 transition-colors"
          >
            <span className="shrink-0 inline-flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-semibold text-xs">
              {citation.page}
            </span>
            
            <div className="flex-1 min-w-0">
              <p className="font-medium text-foreground truncate" title={citation.source}>
                {citation.source}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Chunk ID: {citation.chunk_id}
              </p>
            </div>
            
            <span className="shrink-0 text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
              Trang {citation.page}
            </span>
          </div>
        ))}
      </div>
      
      <p className="text-xs text-muted-foreground mt-3 pt-3 border-t border-border">
        💡 Nội dung được trích dẫn từ tài liệu gốc. Mỗi citation có thể trace ngược về Milvus.
      </p>
    </div>
  );
}