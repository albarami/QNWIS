# QNWIS Frontend Redesign Specification

> **Goal:** Anyone who sees this frontend should be **amazed by its power and information** yet find it **surprisingly simple to use**. The live debate must remain real-time and readable.

---

## Design Philosophy

### The "Bloomberg Terminal Meets Apple" Principle

```
POWER                          SIMPLICITY
├── 6 parallel scenarios       ├── One clear verdict
├── 10,000 Monte Carlo sims    ├── One robustness score
├── 12 expert agents           ├── One recommendation
├── 150 debate turns           ├── Progressive disclosure
├── Sensitivity analysis       ├── Clean visual hierarchy
└── Cross-scenario math        └── Instant comprehension
```

**Rule:** Show the RESULT prominently. Reveal the PROCESS on demand.

---

## Current State vs Target State

### Current (Problems)
```
┌──────────────────────────────────────────────┐
│ Question Input (too big)                      │
├──────────────┬───────────────────────────────┤
│ Progress     │ Scenarios (no results shown)  │
│ Timeline     │ Agents (status only)          │
│ Facts        │ Debate (150 turns - overload) │
│              │ Critique                      │
│              │ Verification                  │
└──────────────┴───────────────────────────────┘
│ Synthesis (text blob)                         │
└───────────────────────────────────────────────┘

❌ Engine B results invisible
❌ No clear answer to "will this succeed?"
❌ Debate drowns the user
❌ No data visualization
```

### Target (Solution)
```
┌──────────────────────────────────────────────────────────────┐
│ 📊 VERDICT CARD (Hero Component)                             │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │  "20% Qatarization by 2028"                              │ │
│ │                                                          │ │
│ │  ██████████░░░░░░░░░░  58% SUCCESS RATE                  │ │
│ │                                                          │ │
│ │  Robustness: ●●●●○○ 4/6 scenarios viable                 │ │
│ │  Confidence: 72%  |  Risk: MEDIUM  |  Trend: ↗           │ │
│ │                                                          │ │
│ │  ⚠️ VULNERABLE TO: Oil crash, GCC labor mobility         │ │
│ └──────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [📊 Scenarios]  [🔥 Live Debate]  [📋 Evidence]  [📄 Brief] │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  TAB CONTENT (full width, ample space)                       │
│                                                              │
│  • Scenarios: 6 cards with Monte Carlo results               │
│  • Live Debate: Real-time conversation (FEATURED)            │
│  • Evidence: Facts + sensitivity charts                      │
│  • Brief: Downloadable ministerial document                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Hero Verdict Card (NEW) ⭐

**File:** `components/verdict/VerdictCard.tsx`

**Purpose:** The ONE thing users see first. Answers: "Should I do this?"

```tsx
interface VerdictCardProps {
  question: string
  verdict: 'APPROVE' | 'PROCEED_WITH_CAUTION' | 'RECONSIDER' | 'REJECT'
  successRate: number           // 0-100, from Monte Carlo
  robustness: {
    passed: number              // e.g., 4
    total: number               // e.g., 6
    vulnerabilities: string[]   // ["Oil crash", "GCC mobility"]
  }
  confidence: number            // 0-100
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  trend: 'increasing' | 'stable' | 'decreasing'
  topDriver: string             // "Training pipeline (38%)"
}
```

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  "Should Qatar accelerate Qatarization to 20% by 2028?"        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │        ████████████░░░░░░░░  58%                         │ │
│  │                                                           │ │
│  │           SUCCESS PROBABILITY                             │ │
│  │      (across 10,000 simulations × 6 scenarios)           │ │
│  │                                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ ROBUSTNESS  │  │ CONFIDENCE  │  │    TREND    │            │
│  │   ●●●●○○    │  │    72%      │  │     ↗       │            │
│  │  4/6 pass   │  │   Medium    │  │  Increasing │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  ⚠️ Vulnerabilities: Oil Price Crash (45%), GCC Mobility (44%) │
│  🎯 Top Driver: Training pipeline capacity (38% of variance)   │
│                                                                 │
│  [PROCEED WITH CAUTION]  ← Verdict badge                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Color System:**
- `APPROVE`: Green gradient (#10B981 → #22C55E)
- `PROCEED_WITH_CAUTION`: Amber gradient (#F59E0B → #FBBF24)
- `RECONSIDER`: Orange gradient (#F97316 → #FB923C)
- `REJECT`: Red gradient (#EF4444 → #F87171)

---

### 2. Cross-Scenario Table (NEW) ⭐

**File:** `components/scenarios/CrossScenarioTable.tsx`

**Purpose:** Show how the policy performs across all 6 possible futures

```tsx
interface CrossScenarioTableProps {
  scenarios: {
    id: string
    name: string
    icon: string              // 📊 📉 🏆 🦠 🤖 🌐
    successRate: number       // Monte Carlo result
    riskLevel: 'low' | 'medium' | 'high' | 'critical'
    trend: 'increasing' | 'stable' | 'decreasing'
    topDriver: string
    isVulnerable: boolean     // < 50% success
    isRecommended: boolean    // Base case or best performing
  }[]
  overallRobustness: string   // "4/6 scenarios pass"
}
```

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CROSS-SCENARIO ANALYSIS                                                 │
│ How does this policy perform across different possible futures?         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Scenario              Success Rate      Risk       Trend    Status    │
│  ──────────────────────────────────────────────────────────────────    │
│                                                                         │
│  📊 Base Case          ████████████░░░  68.4%    ●●○○ MED   ↗  ✓ PASS  │
│                                                                         │
│  📉 Oil Price Crash    ██████░░░░░░░░░  45.2%    ●●●● HIGH  ↘  ⚠ RISK  │
│                                                                         │
│  🏆 Saudi Talent War   ████████░░░░░░░  52.1%    ●●●○ HIGH  →  ✓ PASS  │
│                                                                         │
│  🦠 Pandemic 2.0       █████████████░░  78.3%    ●○○○ LOW   ↗  ✓ BEST  │
│                                                                         │
│  🤖 AI Automation      ██████████░░░░░  61.5%    ●●○○ MED   ↗  ✓ PASS  │
│                                                                         │
│  🌐 GCC Labor Mobility ██████░░░░░░░░░  44.8%    ●●●● HIGH  →  ⚠ RISK  │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ROBUSTNESS SUMMARY                                                     │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  ●●●●○○  Policy succeeds in 4/6 scenarios (>50% success rate)  │    │
│  │                                                                 │    │
│  │  🟢 Best case:  Pandemic scenario (78.3% success)               │    │
│  │  🔴 Worst case: GCC Mobility scenario (44.8% success)           │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Interaction:**
- Click scenario row → Expand to show Monte Carlo details
- Hover → Tooltip with key assumptions
- Sort by any column

---

### 3. Scenario Detail Card (NEW) ⭐

**File:** `components/scenarios/ScenarioDetailCard.tsx`

**Purpose:** Deep dive into ONE scenario's Engine B results

```tsx
interface ScenarioDetailCardProps {
  scenario: {
    name: string
    description: string
    assumptions: Record<string, number>  // e.g., { gdp: 0.5, risk: 0.7 }
  }
  monteCarloResult: {
    successRate: number
    meanOutcome: number
    stdDev: number
    simulations: number        // 10,000
    confidenceInterval: [number, number]
  }
  sensitivityAnalysis: {
    driver: string
    contribution: number       // percentage
  }[]
  forecast: {
    trend: string
    projection2028: number
  }
}
```

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────────┐
│ 📉 OIL PRICE CRASH SCENARIO                                     │
│                                                                 │
│ "Oil drops to $45/barrel for 18 months, triggering budget cuts"│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ASSUMPTIONS APPLIED                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  GDP Growth:     0.5× (half of normal)                  │   │
│  │  Risk Factor:    0.5× (increased uncertainty)           │   │
│  │  Budget:         0.7× (30% cuts expected)               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  MONTE CARLO RESULTS (n=10,000)                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │         Distribution of Outcomes                        │   │
│  │              ▁▂▃▅██▅▃▂▁                                 │   │
│  │              |   |    |                                 │   │
│  │            20%  45%  70%                                │   │
│  │                  ↑                                      │   │
│  │            Mean: 45.2%                                  │   │
│  │       95% CI: [38.1%, 52.3%]                           │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  SENSITIVITY ANALYSIS                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  GDP Contraction     ████████████████████░░  42%        │   │
│  │  Budget Cuts         ██████████████░░░░░░░░  28%        │   │
│  │  Investor Confidence █████████░░░░░░░░░░░░░  18%        │   │
│  │  Other Factors       ██████░░░░░░░░░░░░░░░░  12%        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  FORECAST                                                       │
│  Trend: ↘ Decreasing   |   2028 Projection: 0.38               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4. Live Debate Panel (REDESIGNED) ⭐⭐⭐ THE STAR OF THE SHOW

**File:** `components/debate/LiveDebatePanel.tsx`

**Critical Requirement:** THE FULL DEBATE IS ALWAYS VISIBLE AND LIVE

> **This is the magic moment.** Users WATCH agents debate in real-time. 
> Dr. Fatima challenges Dr. Hassan. Dr. Khalid jumps in with Qatarization data.
> It's like watching a live panel discussion between 12 PhD economists.
> This is what makes ministers say "WOW."

**Design Principles:**
1. **FULL CONVERSATION ALWAYS VISIBLE** - Not hidden, not collapsed, not summarized away
2. **Live typing indicators** - See who is "thinking" right now
3. **Summary is a BONUS** - Small card at top, optional, doesn't replace the debate
4. **Auto-scroll follows the action** - Like watching a live chat
5. **Pause to read** - User can freeze and catch up
6. **Data citations inline** - See the Engine B data agents are referencing

```tsx
interface LiveDebatePanelProps {
  isLive: boolean
  summary: string                    // AI-generated live summary
  keyConsensusPoints: string[]       // Extracted agreements
  keyDisagreements: string[]         // Unresolved debates
  turns: ConversationTurn[]
  currentSpeaker?: string
  totalTurns: number
  debateProgress: number             // 0-100
}
```

**Visual Design - THE DEBATE IS THE MAIN EVENT:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔥 LIVE EXPERT DEBATE                          Turn 47/150  ●●● LIVE   │
│                                                                         │
│ [Following ●] [Pause] [Show Summary]              12 experts debating   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ╔═══════════════════════════════════════════════════════════════════╗ │
│  ║                                                                   ║ │
│  ║  ┌─ Dr. Fatima 📊 ─ Turn 43 ─ OPENING ────────────────────────┐  ║ │
│  ║  │                                                             │  ║ │
│  ║  │  "Based on the Engine B analysis, the base case shows a    │  ║ │
│  ║  │  68.4% success rate for the 20% Qatarization target.       │  ║ │
│  ║  │  However, I want to draw attention to the training         │  ║ │
│  ║  │  pipeline - it's the #1 driver at 38% of variance..."      │  ║ │
│  ║  │                                                             │  ║ │
│  ║  │  📊 [Base Case: 68.4%] [Training: 38% driver]              │  ║ │
│  ║  └─────────────────────────────────────────────────────────────┘  ║ │
│  ║                                                                   ║ │
│  ║  ┌─ Dr. Hassan 📈 ─ Turn 44 ─ RESPONSE ───────────────────────┐  ║ │
│  ║  │                                                             │  ║ │
│  ║  │  "Dr. Fatima makes a critical point. But let's look at     │  ║ │
│  ║  │  the cross-scenario view. In the oil crash scenario,       │  ║ │
│  ║  │  success drops to just 45.2%. The policy is NOT robust     │  ║ │
│  ║  │  against commodity price shocks..."                        │  ║ │
│  ║  │                                                             │  ║ │
│  ║  │  📊 [Oil Crash: 45.2%] [Robustness: 4/6]                   │  ║ │
│  ║  └─────────────────────────────────────────────────────────────┘  ║ │
│  ║                                                                   ║ │
│  ║  ┌─ Dr. Khalid 🏛️ ─ Turn 45 ─ CHALLENGE ──────────────────────┐  ║ │
│  ║  │                                                             │  ║ │
│  ║  │  "I must challenge both of you here. The Qatarization      │  ║ │
│  ║  │  mandate is not just about numbers - it's about national   │  ║ │
│  ║  │  strategy. Even if we reduce to 15%, we need to consider   │  ║ │
│  ║  │  the signaling effect to the private sector..."            │  ║ │
│  ║  │                                                             │  ║ │
│  ║  │  📊 [Current Rate: 10.2%] [Private Sector: 1.2M workers]   │  ║ │
│  ║  └─────────────────────────────────────────────────────────────┘  ║ │
│  ║                                                                   ║ │
│  ║  ┌─ Dr. Mariam 🎓 ─ Turn 46 ─ CONTRIBUTION ───────────────────┐  ║ │
│  ║  │                                                             │  ║ │
│  ║  │  "From a workforce development perspective, I've run       │  ║ │
│  ║  │  the numbers. Current graduate pipeline is 347/year.       │  ║ │
│  ║  │  To hit 20%, we need 1,200/year. That's a 3.5x increase   │  ║ │
│  ║  │  in 4 years. The sensitivity analysis is right - this     │  ║ │
│  ║  │  IS the constraint we must solve first..."                 │  ║ │
│  ║  │                                                             │  ║ │
│  ║  │  📊 [Graduates: 347/yr] [Needed: 1,200/yr] [Gap: 3.5x]     │  ║ │
│  ║  └─────────────────────────────────────────────────────────────┘  ║ │
│  ║                                                                   ║ │
│  ║  ┌─ Dr. Noura 🔍 ─ Turn 47 ─ typing... ────────────────────────┐ ║ │
│  ║  │                                                              │ ║ │
│  ║  │  ●●● analyzing patterns in historical Qatarization data... │ ║ │
│  ║  │                                                              │ ║ │
│  ║  └──────────────────────────────────────────────────────────────┘ ║ │
│  ║                                                                   ║ │
│  ║                            ▼ auto-scrolling...                    ║ │
│  ╚═══════════════════════════════════════════════════════════════════╝ │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  Opening ━━━━▶ Challenge ━━━━▶ [ACTIVE] ━━━━▶ Consensus ━━━━▶ Final   │
│  ████████████████████████████░░░░░░░░░░░░░░░░░░░  47/150 (31%)         │
└─────────────────────────────────────────────────────────────────────────┘
```

**THE CONVERSATION TAKES 80% OF THE SPACE - IT IS THE MAIN EVENT**

**Optional Summary Panel (toggleable, appears at top when clicked):**
```
┌─ Quick Summary (updated every 10 turns) ─────────────────── [×] ─┐
│                                                                   │
│  📍 Current focus: Training pipeline capacity constraints         │
│                                                                   │
│  ✓ AGREED: 20% is ambitious, 15% more realistic                  │
│  ⚡ DEBATING: Oil price assumptions, timeline flexibility         │
│  🎯 KEY INSIGHT: Need 3.5x more graduates (347 → 1,200/year)     │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

**The summary is OPTIONAL and can be dismissed. The real debate is what users watch.**

**Key UX Features:**

1. **🔥 THE LIVE CONVERSATION IS THE HERO**
   - Full messages visible, not truncated by default
   - Agent avatars with icons and colors (Dr. Fatima 📊, Dr. Hassan 📈)
   - Turn types clearly labeled (OPENING, CHALLENGE, RESPONSE, CONSENSUS)
   - Each message has a subtle animation on arrival
   - Tall viewport to show 4-5 messages at once (min-height: 600px)

2. **⌨️ Live Typing Indicators**
   - Shows "Dr. Noura is analyzing..." with animated dots
   - Creates anticipation - user WAITS to see what she'll say
   - Shows agent's specialty while typing ("analyzing patterns...")

3. **📊 Engine B Data Citations (Inline)**
   - Each message shows referenced data: `[Oil Crash: 45.2%]`
   - Clickable chips that highlight the scenario in the table
   - Agents are GROUNDED in the math - users can SEE it

4. **⏸️ Auto-Scroll with Pause Control**
   - Default: follows conversation like a live chat
   - User clicks [Pause] → freezes scroll, can read at own pace
   - Shows "3 new messages" indicator when paused
   - Click indicator to jump to latest

5. **📋 Optional Summary (Toggle)**
   - Small button: [Show Summary]
   - Appears as collapsible card at top
   - Does NOT replace the conversation
   - Useful if user stepped away and wants to catch up

6. **📈 Phase Progress Bar**
   - Visual: Opening → Challenge → [CURRENT] → Consensus → Final
   - Shows turn count: 47/150
   - Users know where they are in the debate

7. **🎨 Visual Hierarchy by Turn Type**
   - OPENING: Blue border - setting the stage
   - CHALLENGE: Amber border - disagreement
   - RESPONSE: Green border - answering
   - CONSENSUS: Emerald glow - agreement reached
   - Makes it easy to scan for conflicts and resolutions

---

### 5. Sensitivity Chart (NEW) ⭐

**File:** `components/analysis/SensitivityChart.tsx`

**Purpose:** Tornado diagram showing what drives success/failure

```tsx
interface SensitivityChartProps {
  drivers: {
    name: string
    contribution: number    // percentage of variance
    direction: 'positive' | 'negative' | 'mixed'
  }[]
  title: string
}
```

**Visual Design (Tornado Chart):**
```
┌─────────────────────────────────────────────────────────────┐
│ WHAT DRIVES SUCCESS?                                        │
│ Sensitivity Analysis: Top factors affecting outcome          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                        ◄── Negative    Positive ──►         │
│                              0%                              │
│                              │                               │
│  Training Pipeline     ◄████│████████████████████►  38%    │
│                              │                               │
│  Policy Effectiveness  ◄████│████████████████►      28%    │
│                              │                               │
│  External Factors      ◄████│██████████►            15%    │
│                              │                               │
│  Implementation           ◄█│████████►              12%    │
│                              │                               │
│  Other                     ◄│████►                   7%    │
│                              │                               │
├─────────────────────────────────────────────────────────────┤
│ 💡 INSIGHT: Improving training pipeline has 3× more impact  │
│    than any other intervention.                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 6. Evidence Panel (ENHANCED)

**File:** `components/evidence/EvidencePanel.tsx`

**Combines:** Facts + Sources + Data Quality

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 EVIDENCE BASE                                                │
│ Deterministic data grounding this analysis                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ BY CATEGORY ────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │  📈 ECONOMIC (8 facts)                              [▼]  │  │
│  │  ├── GDP Growth: 3.2% [QCB 2024] ████████░░ 95%          │  │
│  │  ├── Oil Price: $78/bbl [OPEC] ███████░░░ 90%            │  │
│  │  └── + 6 more...                                          │  │
│  │                                                           │  │
│  │  👥 LABOR MARKET (12 facts)                         [▼]  │  │
│  │  ├── Qatarization Rate: 10.2% [LMIS Q1-2024] █████████ 98%│ │
│  │  ├── Private Sector Workers: 1.2M [LMIS] ████████░░ 95%  │  │
│  │  └── + 10 more...                                         │  │
│  │                                                           │  │
│  │  🎓 EDUCATION (5 facts)                             [▼]  │  │
│  │  └── Graduates/Year: 347 [MoE 2023] ████████░░ 92%       │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ DATA SOURCES ───────────────────────────────────────────┐  │
│  │  LMIS (12) • World Bank (4) • QCB (3) • MoE (2) • PSA (4)│  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tab Navigation Structure

```tsx
// App.tsx - New Structure
const TABS = [
  { id: 'scenarios', label: 'Scenarios', icon: '📊', badge: '6' },
  { id: 'debate', label: 'Live Debate', icon: '🔥', live: true },
  { id: 'evidence', label: 'Evidence', icon: '📋', badge: '25' },
  { id: 'brief', label: 'Brief', icon: '📄' },
]
```

**Tab Content:**

| Tab | Primary Component | Secondary |
|-----|-------------------|-----------|
| Scenarios | `CrossScenarioTable` | `ScenarioDetailCard` (on click) |
| Live Debate | `LiveDebatePanel` | - |
| Evidence | `EvidencePanel` | `SensitivityChart` |
| Brief | `LegendaryBriefing` | Export button |

---

## Page Layout (Final)

```
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER (slim - logo, connection status)                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─ QUESTION INPUT (collapsible after submit) ─────────────────────┐│
│  │ [                                                              ] ││
│  │ [Debate: ● Standard ● Deep ● Legendary]  [Submit to Council]    ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─ VERDICT CARD (Hero - always visible during analysis) ──────────┐│
│  │                                                                  ││
│  │  "20% Qatarization by 2028?"                                     ││
│  │                                                                  ││
│  │      ████████████░░░░░░  58% SUCCESS RATE                       ││
│  │                                                                  ││
│  │  Robustness: 4/6  |  Confidence: 72%  |  Trend: ↗               ││
│  │                                                                  ││
│  │  ⚠️ Vulnerabilities: Oil crash, GCC mobility                     ││
│  │                                                                  ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [📊 Scenarios (6)]  [🔥 Live Debate ●]  [📋 Evidence (25)]  [📄 Brief]│
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─ TAB CONTENT (full width, scrollable) ───────────────────────────┐│
│  │                                                                  ││
│  │                                                                  ││
│  │            (Content based on selected tab)                       ││
│  │                                                                  ││
│  │                                                                  ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ FOOTER (minimal - NSIC branding)                                     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Progress Indicator (Redesigned)

**During Analysis:**
```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ANALYZING YOUR QUESTION                                         │
│  ════════════════════════════════════════════════════════════   │
│                                                                  │
│  ✓ Classification        ✓ Data Extraction      ✓ Scenarios     │
│  ● Engine B Computing    ○ Agent Debate         ○ Synthesis     │
│                                                                  │
│  ████████████████████████░░░░░░░░░░░░░░░  48%  (~2 min left)    │
│                                                                  │
│  Currently: Running Monte Carlo simulations for 6 scenarios...  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## New TypeScript Interfaces

```typescript
// types/engineB.ts

export interface EngineBResult {
  scenarioId: string
  scenarioName: string
  
  monteCarlo: {
    successRate: number           // 0-1
    meanOutcome: number
    stdDev: number
    simulations: number           // 10,000
    confidenceInterval: [number, number]
    distribution: number[]        // histogram bins
  }
  
  sensitivity: {
    driver: string
    contribution: number          // 0-1, percentage of variance
    direction: 'positive' | 'negative' | 'mixed'
  }[]
  
  forecast: {
    trend: 'increasing' | 'stable' | 'decreasing'
    projection: number
    horizon: string               // "2028"
  }
  
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
}

export interface CrossScenarioAnalysis {
  scenarios: EngineBResult[]
  
  robustness: {
    passedCount: number           // e.g., 4
    totalCount: number            // e.g., 6
    threshold: number             // e.g., 0.5 (50%)
  }
  
  vulnerabilities: {
    scenarioName: string
    successRate: number
    reason: string
  }[]
  
  bestCase: {
    scenarioName: string
    successRate: number
  }
  
  worstCase: {
    scenarioName: string
    successRate: number
  }
  
  overallSuccessRate: number      // weighted average
  overallConfidence: number
}

export interface DebateSummary {
  text: string                    // AI-generated summary
  consensusPoints: string[]
  activeDisagreements: string[]
  currentPhase: 'opening' | 'challenge' | 'deliberation' | 'consensus' | 'final'
  turnsCompleted: number
  totalTurns: number
}
```

---

## Files to Create/Modify

### New Files:
```
src/
├── components/
│   ├── verdict/
│   │   └── VerdictCard.tsx              ⭐ NEW
│   ├── scenarios/
│   │   ├── CrossScenarioTable.tsx       ⭐ NEW
│   │   └── ScenarioDetailCard.tsx       ⭐ NEW
│   ├── analysis/
│   │   ├── SensitivityChart.tsx         ⭐ NEW
│   │   └── MonteCarloDistribution.tsx   ⭐ NEW
│   ├── debate/
│   │   ├── LiveDebatePanel.tsx          ⭐ NEW (replaces DebatePanel)
│   │   ├── DebateSummary.tsx            ⭐ NEW
│   │   └── DebateConversation.tsx       (keep, enhance)
│   └── evidence/
│       └── EvidencePanel.tsx            ⭐ NEW (replaces ExtractedFacts)
├── types/
│   └── engineB.ts                       ⭐ NEW
└── App.tsx                              📝 MAJOR RESTRUCTURE
```

### Modify:
```
src/
├── hooks/
│   └── useWorkflowStream.ts             📝 Add Engine B result parsing
├── types/
│   └── workflow.ts                      📝 Add Engine B types
└── state/
    └── initialState.ts                  📝 Add Engine B state
```

---

## Implementation Order

### Phase 1: Core Engine B Display (Day 1)
1. Create `types/engineB.ts` with all interfaces
2. Update `useWorkflowStream.ts` to parse Engine B events
3. Create `VerdictCard.tsx` - the hero component
4. Create `CrossScenarioTable.tsx` - the centerpiece

### Phase 2: Tab Restructure (Day 1-2)
5. Restructure `App.tsx` with tab navigation
6. Create `ScenarioDetailCard.tsx`
7. Create `SensitivityChart.tsx`

### Phase 3: Enhanced Debate (Day 2)
8. Create `LiveDebatePanel.tsx` with summary
9. Create `DebateSummary.tsx`
10. Enhance `DebateConversation.tsx` with data references

### Phase 4: Polish (Day 2-3)
11. Create `EvidencePanel.tsx`
12. Add animations and transitions
13. Test responsive design
14. Accessibility audit

---

## Backend SSE Events Needed

The backend should emit these events for the frontend:

```json
// Engine B results per scenario
{
  "stage": "engine_b:scenario_0",
  "status": "complete",
  "payload": {
    "scenario_id": "base_case",
    "scenario_name": "Base Case",
    "monte_carlo": {
      "success_rate": 0.684,
      "mean_outcome": 0.357,
      "simulations": 10000,
      "confidence_interval": [0.62, 0.75]
    },
    "sensitivity": [
      { "driver": "training_pipeline", "contribution": 0.38 },
      { "driver": "policy_effectiveness", "contribution": 0.28 }
    ],
    "forecast": {
      "trend": "increasing",
      "projection": 0.72
    },
    "risk_level": "medium"
  }
}

// Cross-scenario summary
{
  "stage": "engine_b:summary",
  "status": "complete",
  "payload": {
    "robustness": { "passed": 4, "total": 6 },
    "overall_success_rate": 0.58,
    "vulnerabilities": ["Oil Crash", "GCC Mobility"],
    "best_case": { "name": "Pandemic 2.0", "rate": 0.783 },
    "worst_case": { "name": "GCC Mobility", "rate": 0.448 }
  }
}

// Debate summary (every 10 turns)
{
  "stage": "debate:summary",
  "status": "update",
  "payload": {
    "summary": "Experts agree that 20% is ambitious but achievable...",
    "consensus_points": ["15% more realistic", "Training critical"],
    "active_disagreements": ["Oil price assumptions"],
    "current_phase": "challenge",
    "turns_completed": 47
  }
}
```

---

## Success Criteria

1. **5-Second Test:** User can answer "Should I do this?" within 5 seconds of page load
2. **Wow Factor:** Engine B quantitative power is immediately visible
3. **Simplicity:** Despite 10,000 simulations, the UI feels effortless
4. **🔥 LIVE DEBATE IS THE STAR:**
   - User can WATCH agents debate in real-time
   - Full messages visible, not hidden behind "show more"
   - Typing indicators create anticipation
   - Challenges and responses clearly labeled
   - Engine B data citations in EVERY message
   - 150 turns is an EXPERIENCE, not a data dump
5. **Progressive Disclosure:** Summary optional, details available on demand
6. **Mobile Ready:** Core verdict visible on phone screens, debate scrollable

---

## Color Palette

```css
/* Verdict Colors */
--approve: linear-gradient(135deg, #10B981, #22C55E);
--caution: linear-gradient(135deg, #F59E0B, #FBBF24);
--reconsider: linear-gradient(135deg, #F97316, #FB923C);
--reject: linear-gradient(135deg, #EF4444, #F87171);

/* Success Rate Bar */
--success-high: #22C55E;    /* >70% */
--success-medium: #F59E0B;  /* 50-70% */
--success-low: #EF4444;     /* <50% */

/* Risk Levels */
--risk-low: #22C55E;
--risk-medium: #F59E0B;
--risk-high: #F97316;
--risk-critical: #EF4444;

/* Agent Colors (keep existing) */
/* ... from agentProfiles.ts ... */
```

---

## Responsive Breakpoints

```css
/* Mobile First */
@media (min-width: 640px) { /* sm: 2-column grid */ }
@media (min-width: 768px) { /* md: Side-by-side layout */ }
@media (min-width: 1024px) { /* lg: Full dashboard */ }
@media (min-width: 1280px) { /* xl: Expanded cards */ }
```

---

## Accessibility Checklist

- [ ] All interactive elements have focus states
- [ ] Color is not the only indicator (icons + labels)
- [ ] Charts have text alternatives
- [ ] Tab navigation works
- [ ] Screen reader announces live debate updates
- [ ] Contrast ratio ≥ 4.5:1 for text
- [ ] Touch targets ≥ 44x44px on mobile

---

## Notes for Tomorrow

1. **Start with `VerdictCard`** - This is the hero component that sells the system
2. **Backend may need updates** - Check if Engine B events are being emitted with full data
3. **🔥 THE DEBATE IS SACRED:**
   - NEVER hide the conversation
   - NEVER replace it with summaries
   - ALWAYS show full messages
   - ALWAYS show typing indicators
   - Summary is a BONUS, not a replacement
4. **Test with real query** - Use "20% Qatarization by 2028" as test case
5. **Don't break existing** - Tab structure should allow fallback to current layout
6. **The Magic Moment:** When a user sees Dr. Fatima typing, then her message appears, then Dr. Hassan responds with a CHALLENGE - that's when they understand they're watching something unprecedented

---

---

## 🔥 THE WOW FACTOR: Live Multi-Agent Debate

This is what makes visitors say "I've never seen anything like this":

### What They See

```
User submits: "Should Qatar accelerate Qatarization to 20%?"

5 seconds later...

┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Dr. Fatima (Microeconomics) is typing...                       │
│  ●●●                                                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

Then her message APPEARS:

┌─ Dr. Fatima 📊 ─ OPENING STATEMENT ──────────────────────────────┐
│                                                                  │
│  "Based on the Engine B analysis, the base case shows 68.4%     │
│  success rate. However, the cross-scenario table reveals a      │
│  critical vulnerability: in an oil crash, success drops to      │
│  just 45%. I recommend we discuss a more conservative target."  │
│                                                                  │
│  📊 [Base Case: 68.4%] [Oil Crash: 45.2%]                       │
└──────────────────────────────────────────────────────────────────┘

Immediately...

┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Dr. Hassan (Macroeconomics) is typing...                       │
│  ●●●                                                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

His response APPEARS:

┌─ Dr. Hassan 📈 ─ RESPONSE ───────────────────────────────────────┐
│                                                                  │
│  "Dr. Fatima raises a valid concern. But I'd like to add        │
│  another dimension: the Saudi Talent War scenario shows only    │
│  52% success. If we're being truly robust, we should prepare    │
│  for both oil volatility AND regional competition..."           │
│                                                                  │
│  📊 [Saudi Talent War: 52.1%] [Robustness: 4/6]                 │
└──────────────────────────────────────────────────────────────────┘

Then Dr. Khalid JUMPS IN...

┌─ Dr. Khalid 🏛️ ─ CHALLENGE ───────────────────────────────────────┐
│                                                                  │
│  "I must challenge both of you. Qatarization is not just an     │
│  economic calculation - it's a national mandate. The question   │
│  isn't WHETHER to pursue it, but HOW to make it resilient.      │
│  Have you considered a phased approach with checkpoints?"       │
│                                                                  │
│  📊 [Current Rate: 10.2%] [Target: 20%] [Gap: 9.8%]             │
└──────────────────────────────────────────────────────────────────┘

...and the conversation continues for 150 turns.

The user WATCHES real experts debate in real-time.
They see challenges. Responses. Concessions. Consensus building.
Each statement is GROUNDED in Engine B data.
It's like watching a PhD panel discussion, but on YOUR question.
```

### Why This is Magical

1. **It's REAL debate** - Not a summary, not a report, actual back-and-forth
2. **Named experts** - Dr. Fatima, Dr. Hassan feel like real people
3. **Visible conflict** - Challenges and disagreements are labeled
4. **Data-grounded** - Every claim links to Monte Carlo results
5. **Live typing** - Creates anticipation, feels responsive
6. **150 turns** - Deep analysis, not shallow chat
7. **Resolution** - Consensus emerges, user sees HOW they agreed

### The Emotional Journey

```
Turn 1-10:    "Wow, they're actually debating my question"
Turn 11-30:   "Oh interesting, Dr. Fatima disagrees with Dr. Hassan"
Turn 31-50:   "They're challenging each other with REAL data"
Turn 51-80:   "I see - the training pipeline is the key issue"
Turn 81-120:  "They're starting to find common ground..."
Turn 121-150: "They reached consensus on 15% with contingencies"

Final reaction: "I just watched 12 PhD economists analyze my policy for 20 minutes.
                 This would have taken McKinsey 3 months and $2 million."
```

---

## Summary

This redesign transforms the frontend from a **process display** to a **decision support tool**:

| Before | After |
|--------|-------|
| "Analysis is happening" | "58% chance of success" |
| "Agents are debating" | **WATCH them debate live** |
| "Here's 150 turns" | **Experience the 150 turns in real-time** |
| Engine B invisible | Engine B data cited in every turn |
| Static results | Living, breathing debate |

The user should leave thinking: 

> *"I just watched 12 PhD economists debate my policy question in real-time, 
> grounded in 10,000 Monte Carlo simulations across 6 scenarios. 
> This is the most powerful AND most engaging policy tool I've ever seen."*
