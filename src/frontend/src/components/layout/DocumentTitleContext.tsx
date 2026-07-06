"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

const DocumentTitleContext = createContext<{
  title: string | null;
  setTitle: (title: string | null) => void;
} | null>(null);

export function DocumentTitleProvider({ children }: { children: React.ReactNode }) {
  const [title, setTitle] = useState<string | null>(null);
  return (
    <DocumentTitleContext.Provider value={{ title, setTitle }}>
      {children}
    </DocumentTitleContext.Provider>
  );
}

export function useDocumentTitle(): string | null {
  const ctx = useContext(DocumentTitleContext);
  return ctx?.title ?? null;
}

/** Pages viewing a specific document call this to surface its title in the top bar. */
export function useSetDocumentTitle(title: string | null | undefined) {
  const ctx = useContext(DocumentTitleContext);
  useEffect(() => {
    if (!ctx) return;
    ctx.setTitle(title || null);
    return () => ctx.setTitle(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title]);
}
