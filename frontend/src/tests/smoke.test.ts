import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import HomePage from "@/app/page";

describe("HomePage", () => {
  it("should render scaffold message when page loads", () => {
    render(createElement(HomePage));

    expect(screen.getByText("Frontend scaffold ready.")).toBeInTheDocument();
  });
});
