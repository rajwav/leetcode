# 📓 Engineering Journal & Learning Log

A technical journal capturing post-mortems, invariant analysis, algorithmic mental models, and lessons learned from non-obvious failure modes.

---

## 🎯 Post-Mortem & Reflection Schema

Use this structured entry template when documenting complex problem analyses and retrospectives:

```markdown
### 🗓 YYYY-MM-DD — [Problem Name or Core Architectural Theme]

- **Problem & Difficulty**: `[LeetCode #X - Problem Title](problems/<difficulty>/<0000-slug>/)` (`Easy` | `Medium` | `Hard`)
- **Primary Pattern / Invariant**: e.g., Sliding window with variable left pointer
- **Core Breakthrough**:
  - What invariant makes this problem solvable in optimal time?
- **Failure Modes & Edge Cases**:
  - What tripped up initial attempts? (e.g., negative integers, integer overflow, empty collections, off-by-one indices).
- **Complexity Analysis**:
  - Time Complexity: $O(\dots)$ — why can it not be faster?
  - Space Complexity: $O(\dots)$ — is auxiliary memory compressible?
- **Mental Model Rule**:
  - "When problem presents condition $X$, default to technique $Y$."
```

---

## 🧠 Algorithmic Mental Models & Rule of Thumb

A distilled reference of problem signals mapped to optimal algorithmic strategies:

| Problem Signal / Constraint | Primary Pattern | Key Invariant & Strategy |
| :--- | :--- | :--- |
| Sorted array + Target pair or triplet | **Two Pointers** | Move pointers inward based on monotonic sum behavior |
| Contiguous subarray + Min/max constraint | **Sliding Window** | Expand right pointer; contract left when condition breaks |
| Monotonic solution space (`min/max` answer) | **Binary Search on Answer** | Define binary predicate `check(mid)` across $[L, R]$ |
| Subarray sum equals $K$ | **Prefix Sum + Hash Map** | Store prefix sum frequencies: find `prefix_sum - K` in $O(1)$ |
| Shortest path in unweighted grid / graph | **Breadth-First Search** | Level-order queue traversal with state visited set |
| Search all valid configurations / combinations | **Backtracking / DFS** | Systematic tree search: Choose $\rightarrow$ Explore $\rightarrow$ Unchoose |
| Overlapping subproblems with optimal substructure | **Dynamic Programming** | Define state dimensions, base cases, and transition formula |
| Next greater or previous smaller element | **Monotonic Stack** | Maintain strictly increasing/decreasing stack elements |
| Running median or Top-$K$ elements | **Heaps / Priority Queues** | Maintain bounded heap of size $K$ or two balanced heaps |
| Disjoint connected components / Cycles | **Union-Find (DSU)** | Path compression + rank/size heuristics for near $O(1)$ ops |

---

## 📅 Chronological Journal

### 🗓 2026-08-28 — Laboratory Initialization

- **Context**: Repository foundation established with single canonical solution storage (`problems/{easy,medium,hard}/`).
- **Focus**: Setting up systematic, pattern-first problem taxonomy rather than ad-hoc problem grinding.
- **Key Principle**: Focus on identifying invariants, writing clean self-documenting solutions, and mastering spatial/temporal complexity analysis.
- **Next Objective**: Linear data structures (Arrays, Strings, Two Pointers).
