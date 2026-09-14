---
problem_id: 16
title: "3Sum Closest"
difficulty: "Medium"
slug: "3sum-closest"
leetcode_url: "https://leetcode.com/problems/3sum-closest/"
languages:
  - "C++"
leetcode_tags:
  - "Array"
  - "Two Pointers"
  - "Sorting"
primary_pattern: ""
solved_at: "2026-09-14"
submission_id: "runcode_1789368470.5657313_0Tdf2El30t"
runtime: "0 ms"
memory: "8.3 MB"
---

# 0016 — 3Sum Closest

> Medium · LeetCode #16

## 🔗 Problem

[View on LeetCode](https://leetcode.com/problems/3sum-closest/)

<!-- AUTOMATION_STATS_START -->
- **Languages**: C++
- **Runtime**: 0 ms
- **Memory**: 8.3 MB
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
