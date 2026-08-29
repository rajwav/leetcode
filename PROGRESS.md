# 📈 Progress & Problem Ledger

A structured ledger tracking problem-solving throughput, spatial/temporal performance, and spaced repetition retention.

---

## ⚙️ Tracking Architecture & Canonical Storage

To prevent file duplication and ensure maintainability:
- **Canonical Storage**: All actual code solutions and problem-specific writeups reside strictly inside `problems/{easy,medium,hard}/<problem-id>-<slug>/`.
- **Indexing Layers**: Guides in `patterns/`, `data-structures/`, and `algorithms/` link directly back to these canonical paths without duplicating solution files.
- **Automated Metadata**: Every solution includes standardized metadata enabling automated parsing into this ledger.

```yaml
<!--
id: 1
title: "Two Sum"
difficulty: "Easy"
patterns: ["Two Pointers", "Hash Map"]
data_structures: ["Array", "Hash Table"]
time_complexity: "O(N)"
space_complexity: "O(N)"
date_solved: "2026-08-28"
canonical_path: "problems/easy/0001-two-sum/"
status: "Mastered"
-->
```

---

## 📊 Category Telemetry

<!-- AUTOMATION_CATEGORY_TELEMETRY_START -->
| Category | Solved | Target | Easy | Medium | Hard | Progress |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Arrays & Strings** | 1 | 35 | 1 | 0 | 0 | `░░░░░░░░░░` 2% |
| **Linked Lists** | 0 | 15 | 0 | 0 | 0 | `░░░░░░░░░░` 0% |
| **Stacks & Queues** | 0 | 20 | 0 | 0 | 0 | `░░░░░░░░░░` 0% |
| **Trees & Binary Search Trees** | 0 | 25 | 0 | 0 | 0 | `░░░░░░░░░░` 0% |
| **Heaps & Priority Queues** | 0 | 15 | 0 | 0 | 0 | `░░░░░░░░░░` 0% |
| **Graphs & Disjoint Sets** | 0 | 25 | 0 | 0 | 0 | `░░░░░░░░░░` 0% |
| **Dynamic Programming** | 0 | 35 | 0 | 0 | 0 | `░░░░░░░░░░` 0% |
| **Backtracking & Greedy** | 0 | 20 | 0 | 0 | 0 | `░░░░░░░░░░` 0% |
<!-- AUTOMATION_CATEGORY_TELEMETRY_END -->

---

## 🗂 Master Problem Log

<!-- AUTOMATION_PROBLEM_LOG_START -->
| # | Problem Title | Difficulty | Primary Pattern | Data Structure | Time | Space | Canonical Solution | Review Status |
| :-: | :--- | :---: | :--- | :--- | :-: | :-: | :---: | :---: |
| 0009 | Palindrome Number | 🟢 Easy | — | Math | O(N) | O(1) | [`problems/easy/0009-palindrome-number/`](problems/easy/0009-palindrome-number/) | Solved |
| 0014 | Longest Common Prefix | 🟢 Easy | — | Array, String | O(N) | O(1) | [`problems/easy/0014-longest-common-prefix/`](problems/easy/0014-longest-common-prefix/) | Solved |
<!-- AUTOMATION_PROBLEM_LOG_END -->

---

## 🔄 Spaced Repetition & Retention Ledger

To transition solutions from working memory to long-term intuition, challenging problems are scheduled for revision across increasing time intervals.

### Review Cadence

- **+3 Days (Recall)**: Problems solved with hints, non-optimal complexity, or edge-case struggle.
- **+7 Days (Reinforcement)**: Standard pattern templates and core problem formulations.
- **+21 Days (Mastery)**: Multi-pattern synthesis, advanced DP, and hard graph problems.

### Active Revision Queue

| Problem | Solved Date | Next Review | Cadence | Key Focus / Struggle Point | Status |
| :--- | :---: | :---: | :---: | :--- | :---: |
| *Queue empty* | — | — | — | *Laboratory initialized* | — |
