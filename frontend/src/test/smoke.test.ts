describe("test framework smoke", () => {
  it("runs", () => {
    expect(2 + 2).toBe(4);
  });

  it("has DOM globals from happy-dom", () => {
    const el = document.createElement("div");
    el.textContent = "ok";
    expect(el.textContent).toBe("ok");
  });
});
