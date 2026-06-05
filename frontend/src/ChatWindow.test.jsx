import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ChatWindow from "./ChatWindow";

describe("ChatWindow", () => {
  it("renders agent action cards", () => {
    render(
      <ChatWindow
        messages={[{
          id: "1",
          role: "agent",
          text: "Do this:\n1. Raise ticket\n2. Wait 3 days",
          memoryUsed: true,
          suggestedActions: ["raise_ticket: IT-123"],
          toolsUsed: ["raise_ticket"],
          time: "10:00",
        }]}
        isTyping={false}
        userName="Priya"
        sessionId="sess-1"
        team="platform"
      />
    );
    expect(screen.getByText(/Actions taken \(1\)/)).toBeInTheDocument();
    expect(document.querySelector(".action-card")).toBeTruthy();
  });
});
