---
problem_id: 15
title: "3Sum"
difficulty: "Medium"
slug: "3sum"
leetcode_url: "https://leetcode.com/problems/3sum/"
languages:
  - "C++"
leetcode_tags:
  - "Array"
  - "Two Pointers"
  - "Sorting"
primary_pattern: ""
solved_at: "2026-09-14"
submission_id: "runcode_1789366560.7309043_aKA9NvovoM"
runtime: "0 ms"
memory: "8.4 MB"
---

# 0015 — 3Sum

> Medium · LeetCode #15

## 🔗 Problem

[View on LeetCode](https://leetcode.com/problems/3sum/)

<!-- AUTOMATION_STATS_START -->
- **Languages**: C++
- **Runtime**: 0 ms
- **Memory**: 8.4 MB
- **Tags**: Array, Two Pointers, Sorting
<!-- AUTOMATION_STATS_END -->

<!-- AUTOMATION_PROBLEM_BODY_START -->
### Problem Statement
*(Problem statement indexed from LeetCode)*
<!-- AUTOMATION_PROBLEM_BODY_END -->

## 💡 Engineering Intuition

By moving pointers from opposite ends or in tandem, we avoid checking every O(N^2) combination.

## ⚙️ Approach

Uses Two Pointers to systematically eliminate possibilities and Sorting to group elements or enable monotonicity.

## 🧪 Edge Cases

- Empty data structures (`n == 0`)

## 📊 Complexity Analysis

- **Time Complexity**: $O(\dots)$
- **Space Complexity**: O(1) - Constant Space

## 📝 Lessons Learned

Key takeaway: Sorting is a powerful pre-processing step that often reduces search complexities.
