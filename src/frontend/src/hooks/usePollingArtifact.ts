"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Shared poll cadence — was a `3000` literal duplicated independently across 6 call
 * sites (the 4 tabs below, plus the simpler list/status pollers in courses/page.tsx and
 * course/[id]/page.tsx, which poll a plain status field rather than an artifact-generation
 * state machine and so don't fit this hook's shape). */
export const DEFAULT_POLL_MS = 3000;

/** Common shape of the 4 artifact status responses (Book/Slide/Quiz/Vid). */
export interface ArtifactStatusLike<T> {
  status?: string;
  data?: T | null;
  progress?: number | null;
  error?: string | null;
  regen_used?: number;
  regen_max?: number;
}

interface UsePollingArtifactOptions<T> {
  courseId: string;
  fetchFn: (courseId: string) => Promise<ArtifactStatusLike<T>>;
  /** True once `data` actually has renderable content (e.g. chapters.length > 0) — a
   * "ready" status with an empty payload is treated as not-ready-yet. */
  isReady: (data: T) => boolean;
  timeoutMs: number;
  timeoutMessage: string;
  defaultErrorMessage: string;
  pollMs?: number;
  /** Fires once, right when data first becomes ready — for feature-specific side effects
   * like resetting the active chapter/slide index or quiz-taking state. */
  onReady?: (data: T) => void;
}

/**
 * Shared "generate → poll until ready/error/timeout" state machine for Book/Slide/Quiz/
 * Vid tabs — was 4 independent copies with divergent timeouts and no shared error
 * handling before this hook.
 */
export function usePollingArtifact<T>({
  courseId,
  fetchFn,
  isReady,
  timeoutMs,
  timeoutMessage,
  defaultErrorMessage,
  pollMs = DEFAULT_POLL_MS,
  onReady,
}: UsePollingArtifactOptions<T>) {
  const [data, setData] = useState<T | null>(null);
  const [hasFetched, setHasFetched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [regenUsed, setRegenUsed] = useState<number | null>(null);
  const [regenMax, setRegenMax] = useState<number | null>(null);

  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep the latest callbacks in refs so `startPolling`'s recursive closure always calls
  // the current version without needing to be recreated (and without going in the
  // initial-fetch effect's dependency array, which would restart in-flight polling on
  // every render). Synced in an effect, not during render, per react-hooks/refs.
  const fetchFnRef = useRef(fetchFn);
  const isReadyRef = useRef(isReady);
  const onReadyRef = useRef(onReady);
  useEffect(() => {
    fetchFnRef.current = fetchFn;
    isReadyRef.current = isReady;
    onReadyRef.current = onReady;
  });

  const startPolling = useCallback(
    (startedAt: number) => {
      const poll = async () => {
        try {
          const res = await fetchFnRef.current(courseId);
          if (typeof res.regen_used === "number") setRegenUsed(res.regen_used);
          if (typeof res.regen_max === "number") setRegenMax(res.regen_max);
          if (res.status === "ready" && res.data && isReadyRef.current(res.data)) {
            setData(res.data);
            setHasFetched(true);
            setGenerating(false);
            setProgress(100);
            onReadyRef.current?.(res.data);
            return;
          }
          if (res.status === "error") {
            setError(res.error || defaultErrorMessage);
            setGenerating(false);
            return;
          }
          if (typeof res.progress === "number") setProgress(res.progress);
        } catch {
          // Ignore transient errors while the background job is still running.
        }
        if (Date.now() - startedAt > timeoutMs) {
          setError(timeoutMessage);
          setGenerating(false);
          return;
        }
        pollTimer.current = setTimeout(poll, pollMs);
      };
      pollTimer.current = setTimeout(poll, pollMs);
    },
    [courseId, timeoutMs, timeoutMessage, defaultErrorMessage, pollMs]
  );

  useEffect(() => {
    if (hasFetched) return;
    fetchFnRef
      .current(courseId)
      .then((res) => {
        if (typeof res.regen_used === "number") setRegenUsed(res.regen_used);
        if (typeof res.regen_max === "number") setRegenMax(res.regen_max);
        if (res.status === "ready" && res.data && isReadyRef.current(res.data)) {
          setData(res.data);
          onReadyRef.current?.(res.data);
        } else if (res.status === "processing") {
          setGenerating(true);
          setProgress(res.progress ?? 5);
          startPolling(Date.now());
        } else if (res.status === "error") {
          setError(res.error || defaultErrorMessage);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : defaultErrorMessage))
      .finally(() => setHasFetched(true));

    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId, hasFetched]);

  return {
    data,
    setData,
    hasFetched,
    error,
    setError,
    generating,
    setGenerating,
    progress,
    setProgress,
    regenUsed,
    setRegenUsed,
    regenMax,
    setRegenMax,
    startPolling,
  };
}
