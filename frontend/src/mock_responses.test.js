import { describe, it, expect } from "vitest";
import { getPersonaMemories } from "./mock_responses";

describe("getPersonaMemories", () => {
  it("returns more memories for person10 on fp_and_a", () => {
    const p1 = getPersonaMemories("person1", "fp_and_a");
    const p10 = getPersonaMemories("person10", "fp_and_a");
    expect(p10.length).toBeGreaterThan(p1.length);
  });
});
