export interface Citation {
  page: number;
  source: string;
  chunk_id: string;
}

export type SlideContentType = 'bullets' | 'title-only' | 'two-column';

export interface Slide {
  id: string;
  title: string;
  content: {
    type: SlideContentType;
    items?: string[];
    mainText?: string;
    leftColumn?: string[];
    rightColumn?: string[];
  };
  layoutSuggestion?: string;
  imageSuggestion?: string;
  citations: Citation[];
}

export interface GenerateSlidesResponse {
  slides: Slide[];
  courseId: string;
  courseName: string;
}