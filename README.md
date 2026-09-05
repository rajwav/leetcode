# LeetCode Lab

> **A personal engineering laboratory for algorithmic mastery, pattern decomposition, and deliberate problem-solving.**

An archive of data structures and algorithms built from first principles. This repository uses a single canonical storage model for problem solutions with cross-referenced conceptual guides, tracking continuous problem-solving progression, core invariants, spatial/temporal tradeoffs, and pattern recognition over time.

---

## ⚡ Quick Setup — Zero-Friction Automation

```bash
./scripts/install_launchd.sh
```

After that: **Mac login → solve on LeetCode → commit + push happens automatically.**

Full documentation: [AUTOMATION.md](AUTOMATION.md)

---

## 📊 DSA Progress Dashboard

<!-- AUTOMATION_METRICS_START -->
| Metric | Solved | Distribution | Progress |
| :--- | :---: | :--- | :--- |
| **Total Solved** | **7** | `4 Easy` · `3 Medium` · `0 Hard` | `░░░░░░░░░░░░░░░░░░░░` 2% |
| 🟢 **Easy** | 4 | Foundational primitives & implementation | `█░░░░░░░░░░░░░░░░░░░` 4% |
| 🟡 **Medium** | 3 | Core patterns, graphs & dynamic programming | `░░░░░░░░░░░░░░░░░░░░` 2% |
| 🔴 **Hard** | 0 | Complex optimization & multi-pattern synthesis | `░░░░░░░░░░░░░░░░░░░░` 0% |

<br>

| Attribute | State | Details |
| :--- | :---: | :--- |
| **Current Streak** | `0 days` | Consistent daily problem-solving cycle |
| **Longest Streak** | `0 days` | Peak deliberate practice consistency |
| **Primary Languages** | `C++ (7)` | Standard technical interview & contest toolchains |
| **Active Objective** | `Phase 1` | Core linear structures & two-pointer mechanics |
<!-- AUTOMATION_METRICS_END -->

---

## 🗺️ Mastery Map

Theoretical guides, structural implementations, and indexed cross-references to canonical solutions.

| Data Structure / Domain | Target | Focus Areas | Index Directory |
| :--- | :---: | :--- | :--- |
| **Arrays** | 20 | Sliding windows, two pointers, prefix sums, in-place swaps | [`data-structures/arrays/`](data-structures/arrays/) |
| **Strings** | 15 | Hashing, sliding window, frequency vectors, palindromes | [`data-structures/strings/`](data-structures/strings/) |
| **Linked Lists** | 15 | Fast & slow pointers, reversals, cycle detection | [`data-structures/linked-list/`](data-structures/linked-list/) |
| **Stack & Queue** | 20 | Monotonic stack, circular queue, expression parsing | [`data-structures/stack/`](data-structures/stack/) / [`queue/`](data-structures/queue/) |
| **Trees & BST** | 25 | DFS traversals, BFS level-order, LCA, tree serialization | [`data-structures/trees/`](data-structures/trees/) |
| **Heaps / Priority Queue** | 15 | Top-$K$ elements, two-heap median finding, $K$-way merge | [`data-structures/heap/`](data-structures/heap/) |
| **Trie** | 10 | Prefix indexing, word search, bitwise XOR trees | [`data-structures/trie/`](data-structures/trie/) |
| **Graphs** | 25 | BFS/DFS, topological sort, Dijkstra, Union-Find (DSU) | [`data-structures/graphs/`](data-structures/graphs/) |
| **Dynamic Programming** | 35 | 1D/2D memoization, knapsack, LCS/LIS, state reduction | [`algorithms/dynamic-programming/`](algorithms/dynamic-programming/) |
| **Algorithms & Patterns** | 30 | Sorting, Greedy heuristics, Backtracking, Recursion | [`algorithms/`](algorithms/) |

---

## 🧩 Problem-Solving Patterns

Pattern guides, invariant blueprints, and indexed links to canonical solutions in `problems/`.

| Pattern | Target | Trigger / Invariant | Status | Reference Guide |
| :--- | :---: | :--- | :---: | :--- |
| **Two Pointers** | 25 | Sorted pairs, inward search, partitioning, cycle detection | 🟡 Queue | [`patterns/two-pointers/`](patterns/two-pointers/) |
| **Sliding Window** | 25 | Contiguous subarrays/substrings, min/max window with condition | 🟡 Queue | [`patterns/sliding-window/`](patterns/sliding-window/) |
| **Binary Search** | 20 | Monotonic search spaces, answer optimization, sorted search | 🟡 Queue | [`patterns/binary-search/`](patterns/binary-search/) |
| **Prefix Sum** | 15 | $O(1)$ range sum queries, subarray sums matching target | 🟡 Queue | [`patterns/prefix-sum/`](patterns/prefix-sum/) |
| **Breadth-First Search** | 25 | Shortest path in unweighted graphs, level-by-level state exploration | 🟡 Queue | [`patterns/bfs/`](patterns/bfs/) |
| **Depth-First Search** | 25 | Exhaustive path traversal, tree recursion, backtracking | 🟡 Queue | [`patterns/dfs/`](patterns/dfs/) |
| **Dynamic Programming** | 40 | Overlapping subproblems, optimal substructure, recurrence relations | 🟡 Queue | [`patterns/dynamic-programming/`](patterns/dynamic-programming/) |

---

## 🎯 DSA Roadmap

The laboratory follows a systematic 4-phase progression:

```text
[ Phase 1: Foundations ] ──► [ Phase 2: Non-Linear & Search ] ──► [ Phase 3: DP & Graphs ] ──► [ Phase 4: Hard & Contest ]
  Arrays, Strings, Pointers      Trees, Heaps, Binary Search        Advanced DP, DSU, Trie       Monotonic, Contest Speed
```

👉 Explore the full milestone roadmap in [ROADMAP.md](ROADMAP.md).

---

## 🕒 Recent Solves

<!-- AUTOMATION_RECENT_SOLVES_START -->
| # | Problem | Difficulty | Category / Pattern | Solution | Date |
| :-: | :--- | :---: | :--- | :---: | :---: |
| 167 | [Two Sum II - Input Array Is Sorted](problems/medium/0167-two-sum-ii-input-array-is-sorted/) | 🟡 Medium | Array | [`C++`](problems/medium/0167-two-sum-ii-input-array-is-sorted/) | 2026-09-05 |
| 21 | [Merge Two Sorted Lists](problems/easy/0021-merge-two-sorted-lists/) | 🟢 Easy | Linked List | [`C++`](problems/easy/0021-merge-two-sorted-lists/) | 2026-09-02 |
| 3 | [Longest Substring Without Repeating Characters](problems/medium/0003-longest-substring-without-repeating-characters/) | 🟡 Medium | Hash Table | [`C++`](problems/medium/0003-longest-substring-without-repeating-characters/) | 2026-09-01 |
| 2 | [Add Two Numbers](problems/medium/0002-add-two-numbers/) | 🟡 Medium | Linked List | [`C++`](problems/medium/0002-add-two-numbers/) | 2026-08-31 |
| 20 | [Valid Parentheses](problems/easy/0020-valid-parentheses/) | 🟢 Easy | String | [`C++`](problems/easy/0020-valid-parentheses/) | 2026-08-29 |
| 14 | [Longest Common Prefix](problems/easy/0014-longest-common-prefix/) | 🟢 Easy | Array | [`C++`](problems/easy/0014-longest-common-prefix/) | 2026-08-29 |
| 9 | [Palindrome Number](problems/easy/0009-palindrome-number/) | 🟢 Easy | Math | [`C++`](problems/easy/0009-palindrome-number/) | 2026-08-29 |
<!-- AUTOMATION_RECENT_SOLVES_END -->

---

## 📓 Learning Log & Retrospectives

Every solution is accompanied by an analysis of invariants, edge cases, and algorithmic complexity tradeoffs.

- 📖 **Problem Ledger & Spaced Repetition**: [PROGRESS.md](PROGRESS.md)
- 🧠 **Engineering Journal & Mental Models**: [LEARNING.md](LEARNING.md)
- 🤖 **Automation Architecture & Pipeline Spec**: [AUTOMATION.md](AUTOMATION.md)

---

## 🏆 Milestones

<!-- AUTOMATION_MILESTONES_START -->
- [ ] **10 Solved**: Initial laboratory baseline & environment validation
- [ ] **50 Solved**: Solidified mastery of linear data structures & pointer patterns
- [ ] **100 Solved**: Fluency in Trees, Binary Search, and standard BFS/DFS
- [ ] **250 Solved**: Comprehensive command of Dynamic Programming & Graph Theory
- [ ] **500 Solved**: Advanced multi-pattern synthesis & edge-case intuition
- [ ] **1000 Solved**: Complete algorithmic mastery & high-speed competitive readiness
<!-- AUTOMATION_MILESTONES_END -->

---

## 🗂 Repository Navigation

| Section | Role & Contents | Path |
| :--- | :--- | :--- |
| **Canonical Solutions** | **Single source of truth for problem code and solutions** | [`problems/`](problems/) (`easy/`, `medium/`, `hard/`) |
| **Patterns** | Pattern theory, templates, and canonical problem indexes | [`patterns/`](patterns/) |
| **Data Structures** | Custom DS implementations, notes, and problem indexes | [`data-structures/`](data-structures/) |
| **Algorithms** | Algorithmic domain guides (Sorting, Greedy, Backtracking, DP) | [`algorithms/`](algorithms/) |
| **Daily** | Chronological daily challenge references & streak logs | [`daily/2026/`](daily/2026/) |

---

<p align="center">
  <sub>LeetCode Lab · Built with discipline and intentional practice.</sub>
</p>
