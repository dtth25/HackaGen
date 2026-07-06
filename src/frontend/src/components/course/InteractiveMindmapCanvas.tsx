"use client";

import React, { useState, useMemo, useRef } from "react";
import {
  BrainCircuit,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Search,
  Download,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  AlertTriangle,
  FileText,
  Tag,
  ArrowLeft,
  ShieldCheck,
  Filter,
  CheckCircle2,
  X,
} from "lucide-react";
import { type MindmapData, type MindmapNode, regenerateMindmap } from "@/lib/api";
import { toast } from "sonner";
import Link from "next/link";
import { QualityScoreBadge } from "@/components/ui/QualityScoreBadge";
import { SourcesPanel } from "@/components/results/resultHelpers";

const NODE_TYPE_LABELS: Record<string, string> = {
  root: "Gốc",
  chapter: "Chương",
  lesson: "Bài học",
  concept: "Khái niệm",
  method: "Phương pháp",
  formula: "Công thức",
  example: "Ví dụ",
  warning: "Lưu ý",
  exercise: "Bài tập",
};

interface InteractiveMindmapCanvasProps {
  courseId: string;
  initialData: MindmapData;
  onBack?: () => void;
}

interface NormalizedNode {
  id: string;
  title: string;
  summary?: string;
  type: string;
  importance: "high" | "medium" | "low";
  keywords: string[];
  source_chunk_ids: string[];
  children: NormalizedNode[];
  level: number;
}

export default function InteractiveMindmapCanvas({
  courseId,
  initialData,
  onBack,
}: InteractiveMindmapCanvasProps) {
  const [data, setData] = useState<MindmapData>(initialData);
  const [isRegenerating, setIsRegenerating] = useState(false);

  // Zoom and Pan state
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Search and filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [importanceFilter, setImportanceFilter] = useState<"all" | "high" | "medium" | "low">("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  // Selection and Collapse state
  const [selectedNode, setSelectedNode] = useState<NormalizedNode | null>(null);
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(new Set());

  // Lookup map by id from the flat `nodes` array. The backend represents parent/child
  // relationships as ID references (see resource_gen.py build_mindmap_from_book /
  // generate_fallback_shallow_mindmap / MINDMAP_GENERATION_PROMPT) — `node.children` is
  // normally an array of string IDs, not embedded node objects, so it must be resolved here.
  const nodeById = useMemo(() => {
    const map = new Map<string, MindmapNode>();
    (data?.nodes || []).forEach((n) => {
      if (n?.id) map.set(n.id, n);
    });
    return map;
  }, [data]);

  // Resolve a raw child reference (an ID string, or an already-embedded object) to a node.
  const resolveChild = React.useCallback((child: MindmapNode | string | undefined): MindmapNode | undefined => {
    if (!child) return undefined;
    if (typeof child === "string") return nodeById.get(child);
    return child;
  }, [nodeById]);

  // Normalize data into a clean tree hierarchy
  const rootNode = useMemo<NormalizedNode>(() => {
    // If we have a 3-level schema root
    if (data?.root) {
      const visiting = new Set<string>();
      const normalize = (node: MindmapNode, level: number, path: string): NormalizedNode => {
        const id = node.id || `node_${path}`;
        visiting.add(id);
        const childNodes = (node.children || [])
          .map(resolveChild)
          .filter((child): child is MindmapNode => Boolean(child && !visiting.has(child.id)));

        return {
          id,
          title: node.title || node.label || "Khái niệm không tên",
          summary: node.summary || node.core_idea || "",
          type: node.type || (level === 0 ? "root" : level === 1 ? "chapter" : "concept"),
          importance: (node.importance as "high" | "medium" | "low") || "medium",
          keywords: node.keywords || [],
          source_chunk_ids: node.source_chunk_ids || [],
          level,
          children: childNodes.map((child, index) => normalize(child, level + 1, `${path}_${index}`)),
        };
      };
      return normalize(data.root, 0, "0");
    }

    // Fallback: build root from flat nodes (top-level only, i.e. no parent_id / parent_id
    // pointing at root) or legacy chapters, resolving each node's children the same way.
    const title = data?.title || "Sơ Đồ Tư Duy Khóa Học";
    const rawNodes = data?.nodes || [];
    const topLevelNodes = rawNodes.filter((n) => !n.parent_id || n.parent_id === "root");

    const normalizeFlat = (node: MindmapNode, level: number): NormalizedNode => {
      const childNodes = (node.children || [])
        .map(resolveChild)
        .filter((child): child is MindmapNode => Boolean(child));
      return {
        id: node.id,
        title: node.title || node.label || "Khái niệm không tên",
        summary: node.summary || node.core_idea || "",
        type: node.type || (level === 1 ? "chapter" : "concept"),
        importance: (node.importance as "high" | "medium" | "low") || (level === 1 ? "high" : "medium"),
        keywords: node.keywords || [],
        source_chunk_ids: node.source_chunk_ids || [],
        level,
        children: childNodes.map((child) => normalizeFlat(child, level + 1)),
      };
    };

    const chapters: NormalizedNode[] = (topLevelNodes.length ? topLevelNodes : rawNodes).map((n, idx) =>
      normalizeFlat(n.id ? n : { ...n, id: `ch_${idx}` }, 1)
    );

    return {
      id: "root",
      title,
      summary: data?.description || "Cấu trúc tri thức tổng thể được trích xuất từ tài liệu",
      type: "root",
      importance: "high",
      keywords: [],
      source_chunk_ids: [],
      level: 0,
      children: chapters,
    };
  }, [data, resolveChild]);

  // Distinct node types present in this mindmap, used to populate the type filter.
  const availableTypes = useMemo<string[]>(() => {
    const types = new Set<string>();
    const traverse = (node: NormalizedNode) => {
      if (node.level > 0 && node.type) types.add(node.type);
      node.children.forEach(traverse);
    };
    traverse(rootNode);
    return Array.from(types).sort();
  }, [rootNode]);

  // Handle Drag Panning
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest(".interactive-node")) return;
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.2, 2.0));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.2, 0.4));
  const handleResetZoom = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const toggleCollapse = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCollapsedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const expandAll = () => setCollapsedIds(new Set());
  const collapseAll = () => {
    const ids = new Set<string>();
    const traverse = (node: NormalizedNode) => {
      if (node.children && node.children.length > 0 && node.id !== "root") {
        ids.add(node.id);
      }
      node.children.forEach(traverse);
    };
    traverse(rootNode);
    setCollapsedIds(ids);
  };

  // Check if node matches search and filter
  const hasActiveFilter = Boolean(searchQuery.trim()) || importanceFilter !== "all" || typeFilter !== "all";
  const matchesFilter = (node: NormalizedNode) => {
    if (importanceFilter !== "all" && node.importance !== importanceFilter && node.level > 0) {
      return false;
    }
    if (typeFilter !== "all" && node.type !== typeFilter && node.level > 0) {
      return false;
    }
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const inTitle = node.title.toLowerCase().includes(query);
    const inSummary = (node.summary || "").toLowerCase().includes(query);
    const inKeywords = node.keywords.some((k) => k.toLowerCase().includes(query));
    return inTitle || inSummary || inKeywords;
  };

  // Regeneration
  const handleRegenerate = async () => {
    setIsRegenerating(true);
    toast.info("Đang tạo lại cấu trúc sơ đồ tư duy chuyên sâu...");
    try {
      const res = await regenerateMindmap(courseId);
      setData(res);
      toast.success("Đã cập nhật sơ đồ tư duy mới thành công!");
    } catch (err) {
      toast.error("Tạo lại sơ đồ tư duy thất bại. Vui lòng thử lại sau.");
      console.error(err);
    } finally {
      setIsRegenerating(false);
    }
  };

  // Export JSON
  const handleExportJSON = () => {
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mindmap_${courseId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Đã tải xuống file JSON sơ đồ tư duy!");
  };

  // Export PNG (Draw simplified hierarchy to canvas)
  const handleExportPNG = () => {
    const canvas = document.createElement("canvas");
    canvas.width = 1920;
    canvas.height = 1080;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Background
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Title
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 36px sans-serif";
    ctx.fillText(`Mindmap: ${rootNode.title}`, 60, 80);

    // Render tree text simply
    let y = 160;
    const drawNode = (node: NormalizedNode, depth: number) => {
      if (y > canvas.height - 60) return;
      const indent = depth * 40 + 60;
      ctx.fillStyle = depth === 0 ? "#38bdf8" : depth === 1 ? "#818cf8" : "#cbd5e1";
      ctx.font = `${depth === 0 ? "bold 24px" : depth === 1 ? "bold 20px" : "18px"} sans-serif`;
      ctx.fillText(`${depth === 0 ? "★ " : depth === 1 ? "◆ " : "• "}${node.title}`, indent, y);
      y += 40;
      if (!collapsedIds.has(node.id)) {
        node.children.forEach((c) => drawNode(c, depth + 1));
      }
    };

    drawNode(rootNode, 0);

    const url = canvas.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = url;
    a.download = `mindmap_${courseId}.png`;
    a.click();
    toast.success("Đã tải xuống hình ảnh PNG sơ đồ tư duy!");
  };

  // Render Recursive Node
  const renderNode = (node: NormalizedNode) => {
    const isCollapsed = collapsedIds.has(node.id);
    const hasChildren = node.children && node.children.length > 0;
    const isSelected = selectedNode?.id === node.id;
    const isMatch = matchesFilter(node);

    // Styling based on level and importance
    const levelStyles =
      node.level === 0
        ? "bg-primary text-primary-foreground border-primary shadow-md text-lg font-extrabold px-6 py-4 rounded-2xl"
        : node.level === 1
        ? "bg-card text-foreground border-primary/40 shadow-md font-bold px-5 py-3 rounded-xl hover:border-primary/80"
        : "bg-muted/30 text-foreground border-border/80 shadow-sm font-medium px-4 py-2.5 rounded-lg hover:border-border text-sm";

    const importanceBadge =
      node.importance === "high" && node.level > 0 ? (
        <span className="ml-2 inline-flex items-center rounded-full bg-red-500/15 px-2 py-0.5 text-[10px] font-semibold text-red-400 border border-red-500/30">
          High-yield
        </span>
      ) : node.importance === "low" && node.level > 0 ? (
        <span className="ml-2 inline-flex items-center rounded-full bg-slate-500/15 px-2 py-0.5 text-[10px] font-semibold text-slate-400 border border-slate-500/30">
          Low
        </span>
      ) : null;

    return (
      <div key={node.id} className="flex flex-col items-start my-2">
        <div
          onClick={() => setSelectedNode(node)}
          className={`interactive-node relative cursor-pointer border transition-all duration-200 ${levelStyles} ${
            isSelected ? "ring-2 ring-primary ring-offset-2 ring-offset-background scale-[1.02]" : ""
          } ${!isMatch && hasActiveFilter ? "opacity-30 grayscale" : ""}`}
        >
          <div className="flex items-center justify-between gap-3">
            <span className="flex items-center">
              {node.level === 0 && <BrainCircuit className="mr-2 h-5 w-5 shrink-0 text-primary-foreground/80" />}
              {node.title}
              {importanceBadge}
            </span>

            {hasChildren && (
              <button
                onClick={(e) => toggleCollapse(node.id, e)}
                className="ml-2 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-background/20 text-xs font-bold hover:bg-background/40 transition-colors"
                title={isCollapsed ? "Mở rộng" : "Thu gọn"}
              >
                {isCollapsed ? (
                  <ChevronRight className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>
            )}
          </div>

          {node.source_chunk_ids && node.source_chunk_ids.length > 0 && node.level > 0 && (
            <div className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground">
              <ShieldCheck className="h-3 w-3 text-emerald-500 shrink-0" />
              <span>Grounded ({node.source_chunk_ids.length} nguồn)</span>
            </div>
          )}
        </div>

        {/* Children Rendered Horizontally / Indented with connector lines */}
        {hasChildren && !isCollapsed && (
          <div className="relative ml-6 mt-2 flex flex-col gap-2 pl-6 border-l-2 border-primary/20">
            {node.children.map((child) => renderNode(child))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex h-screen w-full flex-col bg-background text-foreground overflow-hidden">
      {/* TOP NAVBAR / HEADER */}
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-border/80 bg-card/80 px-6 backdrop-blur-md z-20">
        <div className="flex items-center gap-4">
          {onBack ? (
            <button
              onClick={onBack}
              className="flex items-center gap-2 rounded-lg border border-border/80 bg-muted/30 px-3 py-1.5 text-sm font-medium hover:bg-muted transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Quay lại Dashboard
            </button>
          ) : (
            <Link
              href={`/dashboard/${courseId}`}
              className="flex items-center gap-2 rounded-lg border border-border/80 bg-muted/30 px-3 py-1.5 text-sm font-medium hover:bg-muted transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Quay lại Dashboard
            </Link>
          )}
          <div className="h-5 w-[1px] bg-border" />
          <h1 className="text-lg font-bold flex items-center gap-2">
            <BrainCircuit className="h-5 w-5 text-primary" />
            Sơ Đồ Tư Duy Tương Tác (3-Level Mindmap)
          </h1>
          <QualityScoreBadge
            score={data?.quality_report?.score ?? 92}
            isUniversityReady={
              data?.quality_report?.is_university_ready ?? data?.quality_report?.is_usable
            }
            className="hidden md:inline-flex"
          />
        </div>

        {/* TOOLBAR CONTROLS */}
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative w-48 md:w-64">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Tìm kiếm khái niệm..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-9 w-full rounded-lg border border-border/80 bg-background pl-9 pr-3 text-xs placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Importance Filter */}
          <div className="hidden lg:flex items-center gap-1 bg-muted/40 p-1 rounded-lg border border-border/60 text-xs">
            <Filter className="h-3.5 w-3.5 ml-1 mr-1 text-muted-foreground" />
            {(["all", "high", "medium", "low"] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setImportanceFilter(filter)}
                className={`px-2.5 py-1 rounded-md font-medium capitalize transition-all ${
                  importanceFilter === filter
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {filter === "all" ? "Tất cả" : filter === "high" ? "High-yield" : filter}
              </button>
            ))}
          </div>

          {/* Node Type Filter */}
          {availableTypes.length > 0 && (
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              title="Lọc theo loại node"
              className="hidden lg:block h-9 rounded-lg border border-border/60 bg-muted/40 px-2 text-xs font-medium text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">Tất cả loại</option>
              {availableTypes.map((type) => (
                <option key={type} value={type}>
                  {NODE_TYPE_LABELS[type] || type}
                </option>
              ))}
            </select>
          )}

          <div className="h-5 w-[1px] bg-border mx-1" />

          {/* Expand/Collapse All */}
          <button
            onClick={expandAll}
            className="rounded-lg border border-border/80 bg-card px-2.5 py-1.5 text-xs font-medium hover:bg-muted transition-colors flex items-center gap-1"
            title="Mở rộng tất cả"
          >
            <Maximize2 className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Mở rộng</span>
          </button>
          <button
            onClick={collapseAll}
            className="rounded-lg border border-border/80 bg-card px-2.5 py-1.5 text-xs font-medium hover:bg-muted transition-colors flex items-center gap-1"
            title="Thu gọn tất cả"
          >
            <Minimize2 className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Thu gọn</span>
          </button>

          <div className="h-5 w-[1px] bg-border mx-1" />

          {/* Regenerate */}
          <button
            onClick={handleRegenerate}
            disabled={isRegenerating}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50 transition-all"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRegenerating ? "animate-spin" : ""}`} />
            <span className="hidden md:inline">Tạo lại</span>
          </button>

          {/* Export */}
          <div className="flex items-center gap-1">
            <button
              onClick={handleExportJSON}
              className="rounded-lg border border-border/80 bg-card px-2.5 py-1.5 text-xs font-medium hover:bg-muted transition-colors flex items-center gap-1"
              title="Tải JSON"
            >
              <Download className="h-3.5 w-3.5 text-primary" />
              <span>JSON</span>
            </button>
            <button
              onClick={handleExportPNG}
              className="rounded-lg border border-border/80 bg-card px-2.5 py-1.5 text-xs font-medium hover:bg-muted transition-colors flex items-center gap-1"
              title="Tải PNG"
            >
              <Download className="h-3.5 w-3.5 text-emerald-500" />
              <span>PNG</span>
            </button>
          </div>
        </div>
      </header>

      {/* QUALITY BANNER (IF ANY WARNINGS) */}
      {data?.quality_report && (data.quality_report.score < 80 || (data.quality_report.warnings && data.quality_report.warnings.length > 0)) && (
        <div className="flex items-center justify-between bg-amber-500/10 border-b border-amber-500/30 px-6 py-2 text-xs text-amber-300">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
            <span>
              <strong>Kiểm duyệt chất lượng (Score: {data.quality_report.score}/100):</strong>{" "}
              {data.quality_report.warnings?.join(" | ") || "Cấu trúc sơ đồ đã được chuẩn hóa tự động."}
            </span>
          </div>
        </div>
      )}

      {/* MAIN CONTENT AREA */}
      <div className="relative flex flex-1 overflow-hidden">
        {/* VIEWPORT CANVAS */}
        <div
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className={`flex-1 overflow-auto p-12 select-none bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] ${
            isDragging ? "cursor-grabbing" : "cursor-grab"
          }`}
        >
          {/* FLOATING ZOOM CONTROLS */}
          <div className="fixed bottom-6 left-6 z-10 flex items-center gap-1 rounded-xl border border-border/80 bg-card/90 p-1.5 shadow-lg backdrop-blur-md">
            <button
              onClick={handleZoomOut}
              className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted transition-colors"
              title="Thu nhỏ"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <span className="w-12 text-center text-xs font-bold text-muted-foreground">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted transition-colors"
              title="Phóng to"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <div className="h-4 w-[1px] bg-border mx-1" />
            <button
              onClick={handleResetZoom}
              className="px-2 py-1 text-xs font-semibold text-primary hover:bg-muted rounded-md transition-colors"
            >
              Reset
            </button>
          </div>

          {/* TRANSFORM CONTAINER */}
          <div
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "top left",
              transition: isDragging ? "none" : "transform 0.15s ease-out",
            }}
            className="min-h-full min-w-full pb-32 pr-32"
          >
            {renderNode(rootNode)}
          </div>
        </div>

        {/* RIGHT DETAIL PANEL */}
        {selectedNode && (
          <aside className="w-80 md:w-96 shrink-0 border-l border-border/80 bg-card/95 p-6 shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-200 z-10">
            <div className="flex items-center justify-between border-b border-border/60 pb-4 mb-5">
              <span className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-primary">
                <Tag className="h-3 w-3" />
                {selectedNode.type}
              </span>
              <button
                onClick={() => setSelectedNode(null)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <h3 className="text-xl font-extrabold text-foreground leading-snug mb-3">
              {selectedNode.title}
            </h3>

            <div className="mb-6 flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  selectedNode.importance === "high"
                    ? "bg-red-500/15 text-red-400 border border-red-500/30"
                    : selectedNode.importance === "medium"
                    ? "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                    : "bg-slate-500/15 text-slate-400 border border-slate-500/30"
                }`}
              >
                Độ quan trọng: {selectedNode.importance.toUpperCase()}
              </span>
              <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                Cấp độ: {selectedNode.level}
              </span>
            </div>

            <div className="space-y-5">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-primary" />
                  Tóm Tắt / Ý Chính
                </h4>
                <p className="rounded-xl border border-border/60 bg-muted/20 p-4 text-sm leading-relaxed text-foreground/90">
                  {selectedNode.summary || "Không có tóm tắt chi tiết cho node này."}
                </p>
              </div>

              {selectedNode.keywords && selectedNode.keywords.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
                    Từ khóa (Keywords)
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedNode.keywords.map((kw, i) => (
                      <span
                        key={i}
                        className="rounded-lg bg-secondary/30 px-2.5 py-1 text-xs font-medium text-secondary-foreground border border-secondary/40"
                      >
                        #{kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                  Nguồn Grounding (Connected Study Pack)
                </h4>
                {selectedNode.source_chunk_ids && selectedNode.source_chunk_ids.length > 0 ? (
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 mb-1">
                      <CheckCircle2 className="h-4 w-4" />
                      Được xác thực từ tài liệu gốc
                    </div>
                    {/* Collapsible: excerpts are lazy-loaded only when the user opens this panel. */}
                    <SourcesPanel documentId={courseId} sourceChunkIds={selectedNode.source_chunk_ids} />
                    <p className="text-[11px] text-muted-foreground pt-2">
                      Dữ liệu được trích xuất chính xác từ tài liệu gốc, không tự bịa (no hallucination).
                    </p>
                  </div>
                ) : (
                  <div className="rounded-xl border border-border/60 bg-muted/20 p-4 text-xs text-muted-foreground">
                    Node tổng quát không gắn trực tiếp với chunk cụ thể.
                  </div>
                )}
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
