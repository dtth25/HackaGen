"use client";

import React from "react";
import { BookOpen, HelpCircle, Presentation, Video } from "lucide-react";

export type FeatureType = "book" | "slide" | "quiz" | "vid";

interface FeatureOption {
  type: FeatureType;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const FEATURES: FeatureOption[] = [
  {
    type: "book",
    label: "Sách",
    description: "Tạo sách tiếng Việt có cấu trúc từ tài liệu của bạn.",
    icon: <BookOpen className="h-5 w-5" />,
  },
  {
    type: "slide",
    label: "Slides",
    description: "Bản trình chiếu tùy chọn",
    icon: <Presentation className="h-5 w-5" />,
  },
  {
    type: "quiz",
    label: "Quiz",
    description: "Câu hỏi trắc nghiệm tương tác",
    icon: <HelpCircle className="h-5 w-5" />,
  },
  {
    type: "vid",
    label: "Video",
    description: "Video học tập tùy chọn",
    icon: <Video className="h-5 w-5" />,
  },
];

interface FeatureSelectorProps {
  selected: FeatureType;
  onSelect: (feature: FeatureType) => void;
}

export default function FeatureSelector({
  selected,
  onSelect,
}: FeatureSelectorProps) {
  return (
    <div className="w-full">
      <h3 className="mb-4 text-lg font-semibold">Chọn phần học liệu</h3>
      <div className="grid grid-cols-2 gap-3">
        {FEATURES.map((feature) => {
          const isSelected = selected === feature.type;
          return (
            <button
              key={feature.type}
              onClick={() => onSelect(feature.type)}
              className={`flex min-h-28 flex-col items-start rounded-lg border p-4 text-left transition-all ${
                isSelected
                  ? "border-primary bg-primary/10 ring-2 ring-primary/30"
                  : "border-muted-foreground/20 hover:border-muted-foreground/40 hover:bg-muted/50"
              }`}
              type="button"
            >
              <div
                className={`mb-2 rounded-md p-2 ${
                  isSelected
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {feature.icon}
              </div>
              <span className="text-sm font-medium">{feature.label}</span>
              <span className="mt-1 text-xs leading-tight text-muted-foreground">
                {feature.description}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
