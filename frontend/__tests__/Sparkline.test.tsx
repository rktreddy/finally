import { render } from "@testing-library/react";
import Sparkline from "../app/components/Sparkline";

describe("Sparkline", () => {
  it("renders nothing with fewer than 2 data points", () => {
    const { container } = render(<Sparkline data={[100]} />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("renders an SVG with valid data", () => {
    const { container } = render(
      <Sparkline data={[100, 102, 101, 105, 103]} />
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg?.querySelector("polyline")).toBeInTheDocument();
  });

  it("uses green color when price goes up", () => {
    const { container } = render(<Sparkline data={[100, 110]} />);
    const line = container.querySelector("polyline");
    expect(line?.getAttribute("stroke")).toBe("#3fb950");
  });

  it("uses red color when price goes down", () => {
    const { container } = render(<Sparkline data={[110, 100]} />);
    const line = container.querySelector("polyline");
    expect(line?.getAttribute("stroke")).toBe("#f85149");
  });
});
