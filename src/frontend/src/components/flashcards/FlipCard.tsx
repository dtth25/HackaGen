'use client';

import { Flashcard } from '@/lib/flashcards/types';
import { useState } from 'react';

interface FlipCardProps {
  card: Flashcard;
}

export default function FlipCard({ card }: FlipCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div className="perspective-[1000px] w-full max-w-2xl mx-auto">
      <div
        className="relative w-full aspect-[4/3] cursor-pointer"
        onClick={() => setIsFlipped(!isFlipped)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsFlipped(!isFlipped);
          }
        }}
      >
        <div
          className={`relative w-full h-full transition-transform duration-500 ease-in-out transform-style-preserve-3d ${
            isFlipped ? 'rotate-y-180' : ''
          }`}
        >
          {/* Front */}
          <div className="absolute inset-0 backface-hidden rounded-2xl border border-border bg-card shadow-xl p-8 flex flex-col items-center justify-center">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-4">
              Mặt trước
            </h3>
            <p className="text-2xl font-semibold text-center text-foreground leading-relaxed">
              {card.front}
            </p>
            <p className="mt-6 text-xs text-muted-foreground">Click để lật thẻ</p>
          </div>

          {/* Back */}
          <div className="absolute inset-0 backface-hidden rotate-y-180 rounded-2xl border border-border bg-primary/5 shadow-xl p-8 flex flex-col">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-4">
              Mặt sau
            </h3>
            <p className="text-lg text-foreground leading-relaxed flex-1 overflow-auto">
              {card.back}
            </p>
            <div className="mt-4 pt-4 border-t border-border">
              {card.citations.map((citation, idx) => (
                <span
                  key={citation.chunk_id}
                  className="inline-flex items-center gap-1 text-xs text-muted-foreground mr-2"
                >
                  📄 Trang {citation.page}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}