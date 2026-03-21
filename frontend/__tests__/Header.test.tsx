import { render, screen } from "@testing-library/react";
import Header from "../app/components/Header";

describe("Header", () => {
  it("renders portfolio value and cash balance", () => {
    render(
      <Header
        totalValue={12345.67}
        cashBalance={5000.0}
        connectionStatus="connected"
      />
    );

    expect(screen.getByText("$12,345.67")).toBeInTheDocument();
    expect(screen.getByText("$5,000.00")).toBeInTheDocument();
    expect(screen.getByText("FinAlly")).toBeInTheDocument();
  });

  it("shows connection status", () => {
    render(
      <Header
        totalValue={10000}
        cashBalance={10000}
        connectionStatus="disconnected"
      />
    );

    expect(screen.getByText("Disconnected")).toBeInTheDocument();
  });

  it("shows reconnecting status", () => {
    render(
      <Header
        totalValue={10000}
        cashBalance={10000}
        connectionStatus="reconnecting"
      />
    );

    expect(screen.getByText("Reconnecting...")).toBeInTheDocument();
  });

  it("shows live status when connected", () => {
    render(
      <Header
        totalValue={10000}
        cashBalance={10000}
        connectionStatus="connected"
      />
    );

    expect(screen.getByText("Live")).toBeInTheDocument();
  });
});
