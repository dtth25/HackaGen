'use client';

import { Button } from '@/components/ui';

interface SlideControlsProps {
  currentIndex: number;
  totalSlides: number;
  onPrevious: () => void;
  onNext: () => void;
}

export default function SlideControls({
  currentIndex,
  totalSlides,
  onPrevious,
  onNext,
}: SlideControlsProps) {
  return (
    <div className="flex items-center justify-center gap-6 mt-6">
      <Button
        variant="outline"
        onClick={onPrevious}
        disabled={currentIndex === 0}
        className="gap-2"
      >
        ◀ Trước
      </Button>

      <span className="text-sm text-muted-foreground min-w-[80px] text-center">
        Slide {currentIndex + 1} / {totalSlides}
      </span>

      <Button
        variant="outline"
        onClick={onNext}
        disabled={currentIndex === totalSlides - 1}
        className="gap-2"
      >
        Sau ▶
      </Button>
    </div>
  );
}