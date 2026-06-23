'use client';

import { useState } from 'react';
import { mockSlides, mockSlideCourseName } from '@/lib/slides/mockData';
import { Slide } from '@/lib/slides/types';
import SlideViewer from '@/components/slides/SlideViewer';
import SlideThumbnails from '@/components/slides/SlideThumbnails';
import SlideControls from '@/components/slides/SlideControls';
import { Button } from '@/components/ui';

export default function SlidesPage({
  params,
}: {
  params: { id: string };
}) {
  const [slides] = useState<Slide[]>(mockSlides);

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Slides</h1>
            <p className="text-sm text-muted-foreground">{mockSlideCourseName}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              🖥️ Present
            </Button>
            <Button variant="ghost" size="sm">
              ← Quay lại
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 bg-background">
        <div className="max-w-7xl mx-auto px-4 py-8">
          {/* Slide viewer with transitions and keyboard navigation */}
          <SlideViewer slides={slides} />

          {/* Slide info */}
          <div className="mt-4 text-center text-sm text-muted-foreground">
            Sử dụng phím ← → để điều hướng | Home/End để về đầu/cuối
          </div>
        </div>
      </main>
    </div>
  );
}
