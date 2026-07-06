"use client";

import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  CheckCircle2,
  FileText,
  FileWarning,
  Loader2,
  Trash2,
  UploadCloud,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ALLOWED_MIME_TYPES, MAX_FILE_SIZE, validateFiles } from "@/lib/validation";
import { type UploadResponse, uploadFiles } from "@/lib/api";

const ACCEPTED_TYPES: Record<string, string[]> = {};
for (const mime of ALLOWED_MIME_TYPES) {
  ACCEPTED_TYPES[mime] = [];
}

type UploadStatus = "idle" | "uploading" | "success" | "error";

interface FileItem {
  id: string;
  file: File;
  status: UploadStatus;
  progress: number;
  error?: string;
}

interface UploadBoxProps {
  onUploaded?: (result: UploadResponse) => void;
}

function fileId(file: File) {
  return `${file.name}-${file.size}-${file.lastModified}`;
}

export default function UploadBox({ onUploaded }: UploadBoxProps) {
  const [fileItems, setFileItems] = useState<FileItem[]>([]);

  const updateFileStatus = (id: string, updates: Partial<FileItem>) => {
    setFileItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...updates } : item))
    );
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const { validFiles, errors } = validateFiles(acceptedFiles);
    errors.forEach((errMsg) => toast.error(errMsg));

    if (validFiles.length === 0) return;

    setFileItems((prev) => {
      const seen = new Set(prev.map((item) => item.id));
      const nextItems = validFiles
        .filter((file) => !seen.has(fileId(file)))
        .map((file) => ({
          id: fileId(file),
          file,
          status: "idle" as UploadStatus,
          progress: 0,
        }));

      if (nextItems.length === 0) {
        toast.info("Các file này đã có trong danh sách.");
        return prev;
      }

      toast.success(`Đã chọn ${nextItems.length} file.`);
      return [...prev, ...nextItems];
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_FILE_SIZE,
    multiple: true,
  });

  const handleRemoveFile = (id: string) => {
    setFileItems((prev) => prev.filter((item) => item.id !== id));
  };

  const handleUpload = async () => {
    const filesToUpload = fileItems.filter((item) => item.status !== "success");
    if (filesToUpload.length === 0) {
      toast.error("Chưa có file nào để tải lên.");
      return;
    }

    filesToUpload.forEach((item) => {
      updateFileStatus(item.id, { status: "uploading", progress: 0, error: undefined });
    });

    let totalProgress = 0;
    const progressInterval = window.setInterval(() => {
      totalProgress = Math.min(90, totalProgress + Math.random() * 12);
      filesToUpload.forEach((item) => {
        updateFileStatus(item.id, { progress: Math.round(totalProgress) });
      });
      if (totalProgress >= 90) window.clearInterval(progressInterval);
    }, 300);

    try {
      const result = await uploadFiles(filesToUpload.map((item) => item.file));
      window.clearInterval(progressInterval);

      filesToUpload.forEach((item) => {
        updateFileStatus(item.id, { status: "success", progress: 100 });
      });

      toast.success("Tài liệu đã được tải lên. Hệ thống đang phân tích nội dung.");
      onUploaded?.(result);
      return result;
    } catch (err) {
      window.clearInterval(progressInterval);
      const errorMessage =
        err instanceof Error ? err.message : "Có lỗi xảy ra khi tải tài liệu lên.";
      filesToUpload.forEach((item) => {
        updateFileStatus(item.id, {
          status: "error",
          error: errorMessage,
          progress: 0,
        });
      });
      toast.error(errorMessage);
    }
  };

  const getStatusIcon = (status: UploadStatus) => {
    switch (status) {
      case "uploading":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case "success":
        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
      case "error":
        return <FileWarning className="h-4 w-4 text-red-500" />;
      default:
        return <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />;
    }
  };

  const hasFilesToUpload = fileItems.some((item) => item.status !== "success");
  const isUploading = fileItems.some((item) => item.status === "uploading");

  return (
    <Card className="w-full shadow-md border-border/80 bg-card/95 backdrop-blur-sm transition-all">
      <CardHeader className="space-y-1.5 pb-4">
        <CardTitle className="text-xl font-bold flex items-center gap-2 text-foreground">
          <UploadCloud className="h-5 w-5 text-primary" />
          Tải lên tài liệu học tập
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Hỗ trợ định dạng PDF, DOCX hoặc TXT. Dung lượng tối đa 50MB mỗi file.
        </p>
      </CardHeader>
      <CardContent>
        <div
          {...getRootProps()}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-all duration-200 ${
            isDragActive
              ? "border-primary bg-primary/10 shadow-inner scale-[0.99]"
              : "border-border hover:border-primary/60 hover:bg-secondary/50 hover:shadow-sm"
          }`}
        >
          <Input {...getInputProps()} />
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary shadow-sm">
            <UploadCloud className="h-7 w-7" />
          </div>
          <p className="text-base font-semibold text-foreground">
            {isDragActive
              ? "Thả tài liệu vào đây ngay..."
              : "Kéo thả tài liệu vào đây hoặc click để chọn file"}
          </p>
          <p className="mt-1.5 text-xs font-medium text-muted-foreground">
            Một lần tải lên để tạo Sách, mindmap, quiz, flashcards và summary.
          </p>
        </div>

        {fileItems.length > 0 && (
          <div className="mt-6">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold">Tài liệu đã chọn</h3>
              <span className="text-xs text-muted-foreground">
                {fileItems.length} file
              </span>
            </div>

            <ul className="space-y-2">
              {fileItems.map((item) => (
                <li
                  key={item.id}
                  className={`rounded-md border p-3 ${
                    item.status === "error"
                      ? "border-destructive/30 bg-destructive/5"
                      : item.status === "success"
                        ? "border-emerald-200 bg-emerald-50"
                        : "bg-muted/30"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex min-w-0 flex-1 items-center gap-2">
                      {getStatusIcon(item.status)}
                      <span className="truncate text-sm">{item.file.name}</span>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {(item.file.size / (1024 * 1024)).toFixed(1)} MB
                      </span>
                    </div>
                    {item.status === "idle" && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => handleRemoveFile(item.id)}
                        className="text-destructive hover:bg-destructive/10"
                        type="button"
                        aria-label={`Xóa ${item.file.name}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>

                  {item.status === "uploading" && (
                    <div className="mt-2">
                      <Progress value={item.progress} className="h-1.5" />
                      <p className="mt-1 text-xs text-muted-foreground">
                        Đang tải lên {item.progress}%
                      </p>
                    </div>
                  )}

                  {item.status === "error" && item.error && (
                    <p className="mt-1 text-xs text-destructive">{item.error}</p>
                  )}

                  {item.status === "success" && (
                    <p className="mt-1 text-xs text-emerald-700">
                      Đã tải lên thành công
                    </p>
                  )}
                </li>
              ))}
            </ul>

            {hasFilesToUpload && (
              <Button
                onClick={handleUpload}
                className="mt-6 w-full"
                size="lg"
                disabled={isUploading}
                type="button"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Đang tải tài liệu
                  </>
                ) : (
                  <>
                    <UploadCloud className="mr-2 h-4 w-4" />
                    Tải lên {fileItems.length} file
                  </>
                )}
              </Button>
            )}
          </div>
        )}

        {/* Privacy & Trust Layer Notice */}
        <div className="mt-8 rounded-2xl border border-border/80 bg-muted/30 p-5 text-sm">
          <div className="flex items-center gap-2 font-semibold text-foreground mb-3">
            <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            Cam kết bảo mật & Quyền riêng tư (Trust & Privacy Layer)
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-muted-foreground">
            <div className="flex items-start gap-2">
              <span className="mt-1 h-2 w-2 rounded-full bg-emerald-500" />
              <span>
                <strong className="text-foreground">Tài liệu của bạn được giữ riêng tư.</strong> File được lưu trong workspace của ứng dụng, chỉ tài khoản của bạn (và quản trị viên) truy cập được.
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="mt-1 h-2 w-2 rounded-full bg-amber-500" />
              <span>
                <strong className="text-foreground">Bạn có thể xóa tài liệu bất cứ lúc nào.</strong> Xóa sẽ gỡ file gốc, dữ liệu vector và học liệu đã tạo.
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="mt-1 h-2 w-2 rounded-full bg-primary" />
              <span>
                <strong className="text-foreground">Nội dung được tạo dựa trên nguồn trong file của bạn.</strong> Mỗi output có thể xem lại trích đoạn nguồn gốc.
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="mt-1 h-2 w-2 rounded-full bg-rose-500" />
              <span>
                <strong className="text-foreground">AI có thể sai, hãy kiểm tra lại thông tin quan trọng.</strong>
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
