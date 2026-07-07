import { Video } from "lucide-react";

export function VidTab() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="rounded-2xl bg-primary/5 p-5 mb-5">
        <Video className="h-12 w-12 text-primary" />
      </div>
      <h3 className="text-xl font-semibold text-foreground">
        Video học tập
      </h3>
      <p className="mt-2 text-muted-foreground max-w-md">
        Tạo video bài giảng với voiceover tự động — Sắp ra mắt
      </p>
    </div>
  );
}
