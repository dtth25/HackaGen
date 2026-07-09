"use client";

/**
 * App Router `template.tsx` remounts on every navigation, so wrapping children
 * here gives a smooth enter animation between routes without any extra
 * dependency. Uses tw-animate-css utilities already imported in globals.css.
 */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300 ease-out">
      {children}
    </div>
  );
}
