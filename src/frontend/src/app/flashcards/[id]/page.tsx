'use client';

import { useState, useEffect, useCallback } from 'react';
import { mockFlashcards, mockFlashcardCourseName } from '@/lib/flashcards/mockData';
import { Flashcard } from '@/lib/flashcards/types';
import FlipCard from '@/components/flashcards/FlipCard';
import FlashcardControls from '@/components/flashcards/FlashcardControls';
import MemoryStatus from '@/components/flashcards/MemoryStatus';
import ProgressBar from '@/components/flashcards/ProgressBar';
import CitationPanel from '@/components/flashcards/CitationPanel';
import { Button } from '@/components/ui';

export default function FlashcardsPage({
  params,
}: {
  params: { id: string };
}) {
  const [cards] = useState<Flashcard[]>(mockFlashcards);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [memoryStatuses, setMemoryStatuses] = useState<
    Record<string, 'remembered' | 'partial' | 'forgot'>
  >({});

  const currentCard = cards[currentIndex];

  const handlePrevious = useCallback(() => {
    if (currentIndex > 0) setCurrentIndex((prev) => prev - 1);
  }, [currentIndex]);

  const handleNext = useCallback(() => {
    if (currentIndex < cards.length - 1) setCurrentIndex((prev) => prev + 1);
  }, [currentIndex, cards.length]);

  const handleStatusChange = useCallback((status: 'remembered' | 'partial' | 'forgot') => {
    setMemoryStatuses((prev) => ({
      ...prev,
      [currentCard.id]: status,
    }));
  }, [currentCard.id]);

  // Load saved progress from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('flashcard-progress');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setMemoryStatuses(parsed);
      } catch (e) {
        console.error('Failed to parse saved progress', e);
      }
    }
  }, []);

  // Save progress to localStorage
  useEffect(() => {
    localStorage.setItem('flashcard-progress', JSON.stringify(memoryStatuses));
  }, [memoryStatuses]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlePrevious();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNext();
      } else if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        // Flip handled by FlipCard component
        document.querySelector('.flip-card-container')?.dispatchEvent(new MouseEvent('click'));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlePrevious, handleNext]);

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">
              Flashcards
            </h1>
            <p className="text-sm text-muted-foreground">
              {mockFlashcardCourseName}
            </p>
          </div>
          <Button variant="ghost" size="sm">
            ← Quay lại
          </Button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 bg-background">
        <div className="max-w-7xl mx-auto px-4 py-8">
          {/* Progress */}
          <div className="mb-6">
            <p className="text-sm text-muted-foreground">
              Thẻ {currentIndex + 1} / {cards.length}
            </p>
          </div>

      {/* Progress */}
          <div className="mb-6">
            <ProgressBar current={currentIndex + 1} total={cards.length} />
          </div>

          {/* Flashcard */}
          <div className="flip-card-container">
            <FlipCard card={currentCard} />
          </div>

          {/* Controls */}
          <FlashcardControls
            currentIndex={currentIndex}
            totalCards={cards.length}
            onPrevious={handlePrevious}
            onNext={handleNext}
            onFlip={() => {
              document.querySelector('.flip-card-container')?.dispatchEvent(new MouseEvent('click'));
            }}
          />

          {/* Memory status */}
          <MemoryStatus
            currentStatus={memoryStatuses[currentCard.id]}
            onStatusChange={handleStatusChange}
          />

          {/* Citation Panel */}
          <CitationPanel citations={currentCard.citations} />
        </div>
      </main>
    </div>
  );
}
