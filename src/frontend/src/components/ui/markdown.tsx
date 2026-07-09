"use client";

import { Component, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { cn } from "@/lib/utils";

interface MarkdownProps {
  children: string | null | undefined;
  className?: string;
  /** Suppress the block <p> wrapper for text living inside an existing
   * inline/list/button wrapper (quiz options, objective bullets). */
  inline?: boolean;
}

class MarkdownErrorBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function buildComponents(inline: boolean): Partial<Components> {
  return {
    p: inline
      ? ({ children }) => <>{children}</>
      : ({ children }) => (
          <p className="mt-3 first:mt-0 text-[15px] leading-7 text-foreground/90">{children}</p>
        ),
    strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
    em: ({ children }) => <em className="italic">{children}</em>,
    code: ({ children }) => (
      <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.9em]">{children}</code>
    ),
    ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
    ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
    li: ({ children }) => <li>{children}</li>,
    a: ({ children, href }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary underline underline-offset-2"
      >
        {children}
      </a>
    ),
  };
}

const INLINE_COMPONENTS = buildComponents(true);
const BLOCK_COMPONENTS = buildComponents(false);

/** Renders LLM-authored prose as real Markdown + KaTeX math instead of raw text. */
export function Markdown({ children, className, inline = false }: MarkdownProps) {
  const text = children ?? "";
  if (!text) return null;

  return (
    <MarkdownErrorBoundary fallback={<span className={className}>{text}</span>}>
      <span className={cn(inline ? "inline" : "block", className)}>
        <ReactMarkdown
          remarkPlugins={[[remarkGfm, { singleTilde: false }], remarkMath]}
          rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
          components={inline ? INLINE_COMPONENTS : BLOCK_COMPONENTS}
        >
          {text}
        </ReactMarkdown>
      </span>
    </MarkdownErrorBoundary>
  );
}
