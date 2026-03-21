import { formatCurrency, formatPercent, formatQuantity } from "../app/lib/format";

describe("formatCurrency", () => {
  it("formats positive values", () => {
    expect(formatCurrency(1234.56)).toBe("$1,234.56");
  });

  it("formats negative values", () => {
    expect(formatCurrency(-50)).toBe("-$50.00");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });
});

describe("formatPercent", () => {
  it("formats positive percent with + sign", () => {
    expect(formatPercent(5.5)).toBe("+5.50%");
  });

  it("formats negative percent", () => {
    expect(formatPercent(-3.2)).toBe("-3.20%");
  });

  it("formats zero as positive", () => {
    expect(formatPercent(0)).toBe("+0.00%");
  });
});

describe("formatQuantity", () => {
  it("formats integers without decimals", () => {
    expect(formatQuantity(10)).toBe("10");
  });

  it("formats fractional quantities", () => {
    expect(formatQuantity(10.5)).toBe("10.5000");
  });
});
