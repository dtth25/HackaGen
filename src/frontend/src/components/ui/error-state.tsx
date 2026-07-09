"use client";

import { AlertCircle, RefreshCw } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title: string;
  description: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

export function ErrorState({
  title,
  description,
  onRetry,
  retryLabel = "Thử lại",
  className,
}: ErrorStateProps) {
  return (
    <Card className={cn("my-6 border-error/30 bg-error/5 p-8 text-center", className)}>
      <CardHeader>
        <AlertCircle className="mx-auto mb-2 h-12 w-12 text-error" />
        <CardTitle className="text-xl text-error">{title}</CardTitle>
        <CardDescription className="mt-1 text-sm">{description}</CardDescription>
      </CardHeader>
      {onRetry && (
        <CardFooter className="justify-center pt-2">
          <Button onClick={onRetry} variant="outline" className="gap-2">
            <RefreshCw className="h-4 w-4" /> {retryLabel}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
