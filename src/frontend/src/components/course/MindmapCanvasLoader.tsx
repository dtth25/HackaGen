"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Loader2, AlertTriangle } from "lucide-react";
import { getMindmap, getStudyPack, type MindmapData } from "@/lib/api";

const InteractiveMindmapCanvas = dynamic(
  () => import("@/components/course/InteractiveMindmapCanvas"),
  {
    ssr: false,
    loading: () => <MindmapLoadingState />,
  }
);

function MindmapLoadingState() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-background text-muted-foreground">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm font-medium">Đang tải không gian sơ đồ tư duy tương tác...</p>
      </div>
    </div>
  );
}

const EMPTY_MINDMAP: MindmapData = {
  title: "Sơ Đồ Tư Duy Khóa Học",
  root: { id: "root", title: "Sơ Đồ Tư Duy", children: [] },
  nodes: [],
};

export default function MindmapCanvasLoader({ courseId }: { courseId: string }) {
  const [data, setData] = useState<MindmapData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const mindmap = await getMindmap(courseId);
        if (!cancelled) setData(mindmap);
        return;
      } catch (err) {
        try {
          const sp = await getStudyPack(courseId);
          if (!cancelled) {
            setData((sp?.study_pack?.mindmap as MindmapData) || EMPTY_MINDMAP);
          }
        } catch {
          if (!cancelled) {
            setError(err instanceof Error ? err.message : "Không thể tải sơ đồ tư duy.");
            setData(EMPTY_MINDMAP);
          }
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  if (!data) return <MindmapLoadingState />;

  return (
    <div className="flex h-screen w-full flex-col">
      {error && (
        <div className="flex items-center gap-2 border-b border-amber-500/30 bg-amber-500/10 px-6 py-2 text-xs text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
          <span>
            Không tải được sơ đồ tư duy từ backend ({error}). Đang hiển thị bản trống —{" "}
            <Link href={`/dashboard/${courseId}`} className="underline">
              quay lại Dashboard
            </Link>{" "}
            để tạo Sách trước.
          </span>
        </div>
      )}
      <InteractiveMindmapCanvas courseId={courseId} initialData={data} />
    </div>
  );
}
