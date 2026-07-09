import { CONTAINER_WIDE } from "@/lib/layout";
import { cn } from "@/lib/utils";

export function Footer() {
  return (
    <footer className="border-t bg-background">
      <div className={cn(CONTAINER_WIDE, "py-6 text-center text-sm text-muted-foreground")}>
        © {new Date().getFullYear()} HackaGen
      </div>
    </footer>
  );
}
