# Features Research: AI Trading Workstation

**Research Date:** 2026-03-21
**Focus:** What features do Bloomberg-like AI trading terminals have?

## Table Stakes (Must Have)

Features users expect from any trading terminal. Missing these breaks immersion.

### Data Layer
| Feature | Complexity | Dependencies |
|---------|-----------|--------------|
| Persistent watchlist (survives refresh) | Low | Database |
| Live price updates with visual feedback | Medium | SSE, frontend |
| Price flash animations (green uptick, red downtick) | Low | CSS transitions |
| Connection status indicator | Low | Frontend SSE state |

### Portfolio Management
| Feature | Complexity | Dependencies |
|---------|-----------|--------------|
| Cash balance display | Low | Database |
| Position tracking (qty, avg cost, current price) | Medium | Database, price cache |
| Unrealized P&L per position | Medium | Price cache, positions |
| Total portfolio value (cash + holdings) | Low | Positions, prices |
| Trade execution (buy/sell at market) | Medium | Database, price cache |
| Trade validation (sufficient cash/shares) | Low | Database |

### Visualization
| Feature | Complexity | Dependencies |
|---------|-----------|--------------|
| Positions table | Low | Portfolio API |
| Sparkline mini-charts in watchlist | Medium | SSE price accumulation |
| Selected ticker detail chart | Medium | Charting library |
| Portfolio value over time chart | Medium | Snapshots API |
| Dark terminal aesthetic | Medium | Tailwind theme |

### Infrastructure
| Feature | Complexity | Dependencies |
|---------|-----------|--------------|
| Single Docker container | Medium | Multi-stage build |
| Health check endpoint | Low | FastAPI |
| Database lazy initialization | Medium | App startup |

## Differentiators (Competitive Advantage)

Features that make this demo impressive and showcase agentic AI capabilities.

| Feature | Complexity | Impact | Dependencies |
|---------|-----------|--------|--------------|
| AI chat assistant with portfolio awareness | High | Core demo value | LLM, portfolio context |
| AI auto-executes trades (no confirmation) | Medium | "Wow" factor | LLM structured output, trade API |
| AI manages watchlist via natural language | Medium | Fluid UX | LLM structured output, watchlist API |
| Inline trade confirmations in chat | Low | Professional feel | Frontend rendering |
| Portfolio heatmap (treemap by weight, colored by P&L) | High | Visual impact | D3/Recharts treemap |
| Sparklines that fill progressively from SSE | Medium | Live data feel | Frontend state accumulation |
| Price flash CSS animations | Low | Trading terminal feel | CSS transitions |
| Correlated market moves (sector grouping) | Already built | Realism | Market simulator |

## Anti-Features (Deliberately NOT Building)

| Feature | Reason | Risk if Included |
|---------|--------|-----------------|
| User authentication | Single-user demo; adds complexity with zero value | 2-3 phases of work for no visible benefit |
| Limit orders / order book | Eliminates order matching, partial fills, queue priority | Massive complexity for a demo |
| Real money / brokerage API | Legal, compliance, error handling nightmare | Out of scope entirely |
| WebSocket (instead of SSE) | Bidirectional not needed; SSE is simpler | Extra complexity, debugging |
| Chat streaming (token-by-token) | Cerebras is fast enough; loading spinner sufficient | SSE complexity in chat path |
| Mobile-responsive design | Desktop-first terminal; tablet functional | Design constraint dilution |
| Multiple user profiles | `user_id="default"` everywhere; schema ready for future | Unnecessary for demo |
| Trade confirmation dialogs | Zero stakes (fake money); kills demo flow | UX friction |
| Historical data API | Sparklines from SSE since page load; no historical endpoint needed | Storage, complexity |
| Candlestick charts | Line charts sufficient for demo; candlestick needs OHLC data | Data model expansion |
| Social features / sharing | Not a social platform | Scope creep |
| Notifications / alerts | Nice-to-have but not core | Extra backend + frontend work |
| Dark/light theme toggle | Dark only — it's a terminal | Design decision dilution |
| Internationalization | English only for demo | Unnecessary |

## Feature Dependencies (Build Order)

```
Database Layer ─────────────┐
                            ├──→ Watchlist API ──→ Frontend Watchlist
                            ├──→ Portfolio API ──→ Frontend Portfolio
                            ├──→ Trade API ─────→ Frontend Trade Bar
                            └──→ Chat API ──────→ Frontend Chat Panel
                                    │
Market Data (existing) ─────────────┤
                                    ▼
                            LLM Integration ──→ AI Auto-Execution
```

**Critical path:** Database → API Routes → Frontend (parallel with LLM integration)

## Complexity Budget

| Component | Estimated Effort | Risk |
|-----------|-----------------|------|
| Database + lazy init | Low | Low — well-understood pattern |
| API routes (portfolio, watchlist, trade) | Medium | Low — standard CRUD |
| LLM integration + structured outputs | Medium | Medium — API quirks, prompt engineering |
| Frontend shell + layout | Medium | Low — Tailwind + component structure |
| Live price display + flash animations | Medium | Low — EventSource is standard |
| Charting (sparklines, detail, P&L) | High | Medium — library integration |
| Portfolio heatmap (treemap) | High | Medium — custom visualization |
| AI chat panel | Medium | Low — message list + input |
| Docker multi-stage build | Medium | Low — well-documented pattern |
| E2E tests | Medium | Medium — SSE timing in tests |

---
*Features research: 2026-03-21*
