import { render, screen } from "@testing-library/react";
import PositionsTable from "../app/components/PositionsTable";
import type { Position } from "../app/lib/types";

describe("PositionsTable", () => {
  const mockPositions: Position[] = [
    {
      ticker: "AAPL",
      quantity: 10,
      avg_cost: 150.0,
      current_price: 160.0,
      unrealized_pnl: 100.0,
      pnl_pct: 6.67,
      market_value: 1600.0,
    },
    {
      ticker: "GOOGL",
      quantity: 5,
      avg_cost: 180.0,
      current_price: 170.0,
      unrealized_pnl: -50.0,
      pnl_pct: -5.56,
      market_value: 850.0,
    },
  ];

  it("renders positions with correct data", () => {
    render(<PositionsTable positions={mockPositions} />);

    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("GOOGL")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("shows empty state when no positions", () => {
    render(<PositionsTable positions={[]} />);

    expect(screen.getByText("No open positions")).toBeInTheDocument();
  });

  it("displays P&L with correct sign", () => {
    render(<PositionsTable positions={mockPositions} />);

    expect(screen.getByText("$100.00")).toBeInTheDocument();
    expect(screen.getByText("-$50.00")).toBeInTheDocument();
  });
});
