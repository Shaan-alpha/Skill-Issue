import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Stub Next 16 Cache Components helpers in vitest. They throw at runtime
// unless `cacheComponents: true` is loaded from `next.config.ts`, which
// vitest does not load. We test the cached functions for their data shape;
// the caching behavior itself is covered by the build + manual smoke.
vi.mock("next/cache", () => ({
  cacheTag: vi.fn(),
  cacheLife: vi.fn(),
  revalidateTag: vi.fn(),
}));
