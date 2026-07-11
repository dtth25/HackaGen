import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Testing Library's auto-cleanup only self-registers when it detects a global
// `afterEach` (e.g. with vitest's `globals: true`). This project intentionally imports
// test globals explicitly instead, so register cleanup by hand — otherwise DOM from one
// test leaks into the next and later tests match stale elements from prior renders.
afterEach(() => {
  cleanup();
});
