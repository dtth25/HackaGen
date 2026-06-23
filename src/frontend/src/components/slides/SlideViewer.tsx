'use client';

import { Slide } from '@/lib/slides/types';
import { useState, useEffect, useCallback } from 'react';
import SlideCard from './SlideCard';

interface SlideViewerProps {
  slides: Slide[];
  className?: string;
}

type TransitionType = 'fade' | 'slide';

export default function SlideViewer({ slides, className = '' }: SlideViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [transition, setTransition] = useState<TransitionType>('fade');
  const [isAnimating, setIsAnimating] = useState(false);

  const currentSlide = slides[currentIndex];

  const goToSlide = useCallback((index: number) => {
    if (index < 0 || index >= slides.length || isAnimating) return;
    setIsAnimating(true);
    setCurrentIndex(index);
    setTimeout(() => setIsAnimating(false), 350);
  }, [slides.length, isAnimating]);

  const goNext = useCallback(() => {
    if (currentIndex < slides.length - 1) {
      goToSlide(currentIndex + 1);
    }
  }, [currentIndex, slides.length, goToSlide]);

  const goPrevious = useCallback(() => {
    if (currentIndex > 0) {
      goToSlide(currentIndex - 1);
    }
  }, [currentIndex, goToSlide]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        goNext();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        goPrevious();
      } else if (e.key === 'Home') {
        e.preventDefault();
        goToSlide(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        goToSlide(slides.length - 1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goNext, goPrevious, goToSlide, slides.length]);

  // Touch/swipe support
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const handleTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > 50;
    const isRightSwipe = distance < -50;

    if (isLeftSwipe) goNext();
    if (isRightSwipe) goPrevious();
  };

  const transitionClass = transition === 'fade'
    ? 'transition-opacity duration-300'
    : 'transition-transform duration-300';

  return (
    <div
      className={`relative ${className}`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Slide Container with transitions */}
      <div className={`${transitionClass} ${isAnimating ? 'opacity-0' : 'opacity-100'}`}>
        <SlideCard slide={currentSlide} />
      </div>

      {/* Click zones for navigation (desktop) */}
      <button
        onClick={goPrevious}
        disabled={currentIndex === 0}
        className="absolute left-0 top-0 bottom-0 w-1/4 opacity-0 hover:opacity-100 transition-opacity z-10 group"
        aria-label="Previous slide"
      >
        <div className="h-full flex items-center justify-start pl-4">
          <div className="bg-black/50 text-white rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </div>
        </div>
      </button>

      <button
        onClick={goNext}
        disabled={currentIndex === slides.length - 1}
        className="absolute right-0 top-0 bottom-0 w-1/4 opacity-0 hover:opacity-100 transition-opacity z-10 group"
        aria-label="Next slide"
      >
        <div className="h-full flex items-center justify-end pr-4">
          <div className="bg-black/50 text-white rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </button>
    </div>
  );
}