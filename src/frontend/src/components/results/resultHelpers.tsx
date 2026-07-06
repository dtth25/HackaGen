"use client";

import React, { useCallback, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, Layers, Loader2, ShieldCheck } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { assetUrl, getDocumentSources, type SourceExcerpt } from "@/lib/api";

export type PlainObject = Record<string, unknown>;

export function isObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function asString(value: unknown, fallback = "") {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

const SUBSCRIPT: Record<string, string> = {
  "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
  i: "ᵢ", I: "ᵢ", j: "ⱼ", J: "ⱼ", n: "ₙ", N: "ₙ", m: "ₘ", M: "ₘ", k: "ₖ", K: "ₖ",
};

const SUPERSCRIPT: Record<string, string> = {
  "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
  n: "ⁿ", N: "ⁿ",
};

function mapMathToken(value: string, map: Record<string, string>) {
  return value
    .split("")
    .map((char) => map[char] ?? char)
    .join("");
}

export function normalizeMathText(value: string) {
  return value
    .replace(/\*\*|`|\$/g, "")
    .replace(/\\\(|\\\)/g, "")
    .replace(/\\leq?|<=/g, "≤")
    .replace(/\\geq?|>=/g, "≥")
    .replace(/\\neq|!=/g, "≠")
    .replace(/\\times/g, "×")
    .replace(/\\sum|\bsum\s*\(/gi, (match) => (match.endsWith("(") ? "Σ(" : "Σ"))
    .replace(/\bMEX\s*\(\s*([^)]+?)\s*\)/gi, (_, inner: string) => `MEX(${inner.trim()})`)
    .replace(/\bP\s*\(\s*([^,)]+)\s*,\s*([^)]+)\)/g, (_, left: string, right: string) => `P(${left.trim()}, ${right.trim()})`)
    .replace(/([A-Za-z0-9)])\^\{([0-9nN]+)\}/g, (_, base: string, exp: string) => `${base}${mapMathToken(exp, SUPERSCRIPT)}`)
    .replace(/([A-Za-z0-9)])\^([0-9nN]+)/g, (_, base: string, exp: string) => `${base}${mapMathToken(exp, SUPERSCRIPT)}`)
    .replace(/\b([A-Za-z])_\{([A-Za-z0-9]+)\}/g, (_, base: string, sub: string) => `${base}${mapMathToken(sub, SUBSCRIPT)}`)
    .replace(/\b([A-Za-z])_([A-Za-z0-9]+)\b/g, (_, base: string, sub: string) => `${base}${mapMathToken(sub, SUBSCRIPT)}`)
    .replace(/\b([AWVxXLRCP])([ijmnMN0-9])\b/g, (_, base: string, sub: string) => `${base}${mapMathToken(sub, SUBSCRIPT)}`)
    .replace(/\s+\*\s+/g, " × ")
    .replace(/\b([A-Z])([ᵢⱼₙₘₖ₀-₉])\s+([a-zA-Z])([ᵢⱼₙₘₖ₀-₉])\b/g, "$1$2 × $3$4")
    .replace(/\bO\s*\(\s*([^)]+?)\s*\)/g, (_, inner: string) => `O(${inner.replace(/\s+/g, " ").trim()})`);
}

export function stripInternalMarkers(value: string, compact = true) {
  const cleaned = normalizeMathText(value)
    .replace(/===\s*BẮT ĐẦU.*?===/giu, " ")
    .replace(/===\s*KẾT THÚC.*?===/giu, " ")
    .replace(/\[MÃ ĐỊNH DANH TRANG:\s*\d+\]/giu, " ")
    .replace(/\bNỘI DUNG:\s*/giu, " ")
    .replace(/\bpage\s*:\s*\d+\b/giu, " ")
    .replace(/\bchunk_id\s*:\s*[\w.-]+\b/giu, " ")
    .replace(/\bsource\s*:\s*[\w./\\:-]+\b/giu, " ")
    .replace(/(?:\.\s*){3,}/g, " ");

  if (compact) return cleaned.replace(/\s+/g, " ").trim();
  return cleaned.replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").trim();
}

const DEVELOPER_MODE = process.env.NEXT_PUBLIC_DEVELOPER_MODE === "true";

export function SourcesPanel({
  documentId,
  sourceChunkIds,
  fallbackCount,
  defaultOpen = false,
}: {
  documentId?: string;
  sourceChunkIds?: unknown;
  fallbackCount?: number;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [sources, setSources] = useState<SourceExcerpt[]>([]);
  const [totalSourceChunks, setTotalSourceChunks] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ids = useMemo(
    () =>
      Array.from(
        new Set(
          asArray(sourceChunkIds)
            .map((id) => asString(id))
            .filter(Boolean),
        ),
      ),
    [sourceChunkIds],
  );
  const sourceCount = ids.length || fallbackCount || totalSourceChunks || sources.length;
  const canLoadSources = Boolean(documentId);

  const loadSources = useCallback((markLoading = true) => {
    if (!documentId || (loading && markLoading) || sources.length > 0 || error) return () => undefined;
    let cancelled = false;
    if (markLoading) setLoading(true);
    getDocumentSources(documentId, ids, DEVELOPER_MODE)
      .then((payload) => {
        if (cancelled) return;
        setSources(payload.sources || []);
        setTotalSourceChunks(payload.total_source_chunks ?? null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Không thể tải nguồn được dùng.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [documentId, error, ids, loading, sources.length]);

  const handleToggleSources = () => {
    const nextOpen = !open;
    setOpen(nextOpen);
    if (nextOpen) loadSources();
  };

  if (!canLoadSources && !sourceCount) return null;

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={handleToggleSources}
        className="flex items-center gap-1.5 rounded-xl border border-border/80 bg-muted/30 px-3 py-2 text-xs font-medium text-foreground/80 hover:bg-muted/60 transition-all select-none"
      >
        <Layers className="h-4 w-4 text-primary" />
        <span>Xem nguồn được dùng{sourceCount ? ` (${sourceCount})` : ""}</span>
      </button>
      {open && (
        <div className="mt-2 rounded-xl border border-border/60 bg-muted/20 p-3">
          {!canLoadSources && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-300">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>Nguồn đã được gắn metadata, nhưng trang này chưa có document id để tải trích đoạn sạch.</span>
            </div>
          )}

          {loading && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              Đang tải trích đoạn nguồn...
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs leading-5 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-300">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && canLoadSources && sources.length === 0 && (
            <div className="flex items-start gap-2 text-xs leading-5 text-muted-foreground">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
              <span>Output này có grounding metadata, nhưng chưa tìm thấy trích đoạn tương ứng trong Vector DB.</span>
            </div>
          )}

          {sources.length > 0 && (
            <div className="space-y-2">
              {sources.map((source, index) => (
                <div key={`${source.source_chunk_id ?? "source"}-${index}`} className="rounded-lg border bg-background p-3 shadow-2xs">
                  <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-300">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      Nguồn trong tài liệu
                    </span>
                    {source.filename ? (
                      <span className="normal-case font-medium text-foreground/70 truncate max-w-[220px]">
                        {source.filename}
                      </span>
                    ) : null}
                    {source.page ? <span>Trang {source.page}</span> : null}
                    {DEVELOPER_MODE && source.source_chunk_id ? (
                      <span className="rounded bg-muted px-1.5 py-0.5 font-mono normal-case">
                        {source.source_chunk_id}
                      </span>
                    ) : null}
                  </div>
                  <p className="text-xs leading-5 text-foreground/85">
                    {stripInternalMarkers(source.excerpt)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function markdownLines(content: string) {
  return stripInternalMarkers(content, false).replace(/\r/g, "").split("\n");
}

export function MarkdownBlock({ content }: { content: string }) {
  const blocks: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = () => {
    if (listItems.length > 0) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="space-y-1 pl-5 text-sm leading-6">
          {listItems.map((item, index) => (
            <li key={`${item}-${index}`} className="list-disc">
              {item}
            </li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  markdownLines(content).forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      return;
    }

    const headingMatch = /^(#{1,3})\s+(.+)$/.exec(line);
    if (headingMatch) {
      flushList();
      blocks.push(
        <h4 key={`h-${blocks.length}`} className="text-base font-semibold leading-tight">
          {headingMatch[2].replace(/[*_`]/g, "")}
        </h4>
      );
      return;
    }

    const bulletMatch = /^[-*]\s+(.+)$/.exec(line);
    if (bulletMatch) {
      listItems.push(bulletMatch[1].replace(/[*_`]/g, ""));
      return;
    }

    flushList();
    blocks.push(
      <p key={`p-${blocks.length}`} className="text-sm leading-7 text-foreground/90">
        {line.replace(/[*_`]/g, "")}
      </p>
    );
  });

  flushList();
  return <div className="space-y-3">{blocks}</div>;
}

export function textList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => stripInternalMarkers(asString(item))).filter(Boolean);
  }

  const text = stripInternalMarkers(asString(value), false);
  if (!text) return [];

  return text
    .split(/\n|;|•/)
    .map((item) => item.replace(/^[-*\d.)\s]+/, "").trim())
    .filter(Boolean);
}

export function DownloadLink({
  href,
  label,
  icon,
  variant = "outline",
}: {
  href?: string | null;
  label: string;
  icon: ReactNode;
  variant?: "default" | "outline" | "secondary" | "ghost";
}) {
  const resolved = assetUrl(href);
  if (!resolved) return null;

  return (
    <a
      href={resolved}
      className={buttonVariants({ variant, size: "lg" })}
      target="_blank"
      rel="noreferrer"
    >
      {icon}
      {label}
    </a>
  );
}

export function LessonList({
  title,
  icon,
  items,
}: {
  title: string;
  icon: ReactNode;
  items: string[];
}) {
  if (items.length === 0) return null;

  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
        {icon}
        {title}
      </div>
      <ul className="space-y-1 pl-5 text-sm leading-6 text-muted-foreground">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className="list-disc">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function EmptyResult({ message }: { message: string }) {
  return (
    <div className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">
      {message}
    </div>
  );
}
