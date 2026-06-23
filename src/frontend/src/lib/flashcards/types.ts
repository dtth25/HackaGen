export interface Citation {
  page: number;
  source: string;
  chunk_id: string;
}

export type MemoryStatus = 'remembered' | 'partial' | 'forgot';

export interface Flashcard {
  id: string;
  front: string;
  back: string;
  citations: Citation[];
  memoryStatus?: MemoryStatus;
}

export interface GenerateFlashcardsResponse {
  flashcards: Flashcard[];
  courseId: string;
  courseName: string;
}