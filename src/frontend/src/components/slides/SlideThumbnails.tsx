'use client';

import { Slide } from '@/lib/slides/types';

interface SlideThumbnailsProps {
  slides: Slide[];
  currentIndex: number;
  onThumbnailClick: (index: number) => void;
}

export default function SlideThumbnails({
  slides,
  currentIndex,
  onThumbnailClick,
}: SlideThumbnailsProps) {
  return (
    <div className="flex items-center justify-center gap-3 mt-6 overflow-x-auto pb-2">
      {slides.map((slide, idx) => (
        <button
          key={slide.id}
          onClick={() => onThumbnailClick(idx)}
          className={`relative shrink-0 w-32 aspect-video rounded-lg border-2 transition-all ${
            idx === currentIndex
              ? 'border-primary shadow-lg'
              : 'border-border hover:border-muted-foreground'
          }`}
        >
          <div className="absolute inset-0 bg-card rounded-md p-2 overflow-hidden">
            <p className="text-xs font-medium text-foreground truncate">
              {slide.title}
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Slide {idx + 1}
            </p>
          </div>
        </button>
      ))}
    </div>
  );
}