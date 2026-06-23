'use client';

import { Button } from '@/components/ui';

interface FlashcardControlsProps {
  currentIndex: number;
  totalCards: number;
  onPrevious: () => void;
  onNext: () => void;
  onFlip: () => void;
}

export default function FlashcardControls({
  currentIndex,
  totalCards,
  onPrevious,
  onNext,
  onFlip,
}: FlashcardControlsProps) {
  return (
    <div className="flex items-center justify-center gap-4 mt-6">
      <Button
        variant="outline"
        onClick={onPrevious}
        disabled={currentIndex === 0}
        className="gap-2"
      >
        ◀ Trước
      </Button>

      <Button onClick={onFlip} className="gap-2">
        🔄 Lật thẻ
      </Button>

      <Button
        variant="outline"
        onClick={onNext}
        disabled={currentIndex === totalCards - 1}
        className="gap-2"
      >
        Sau ▶
      </Button>
    </div>
  );
}