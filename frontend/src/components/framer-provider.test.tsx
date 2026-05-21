import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { m } from "framer-motion";
import { FramerProvider } from "./framer-provider";

describe("FramerProvider", () => {
  it("renders children inside LazyMotion strict mode", () => {
    const { container } = render(
      <FramerProvider>
        <m.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          hello
        </m.div>
      </FramerProvider>,
    );
    expect(container.textContent).toBe("hello");
  });
});
