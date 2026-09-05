---
problem_id: 167
title: "Two Sum II - Input Array Is Sorted"
difficulty: "Medium"
slug: "two-sum-ii-input-array-is-sorted"
leetcode_url: "https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/"
languages:
  - "C++"
leetcode_tags:
  - "Array"
  - "Two Pointers"
  - "Binary Search"
primary_pattern: ""
solved_at: "2026-09-05"
submission_id: "2131573667"
runtime: "0 ms"
memory: "19.6 MB"
---

# 0167 — Two Sum II - Input Array Is Sorted

> Medium · LeetCode #167

## 🔗 Problem

[View on LeetCode](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/)

<!-- AUTOMATION_STATS_START -->
- **Languages**: C++
- **Runtime**: 0 ms
- **Memory**: 19.6 MB
- **Tags**: Array, Two Pointers, Binary Search
<!-- AUTOMATION_STATS_END -->

<!-- AUTOMATION_PROBLEM_BODY_START -->
### Problem Statement
*(Problem statement indexed from LeetCode)*
<!-- AUTOMATION_PROBLEM_BODY_END -->

## 💡 Engineering Intuition

By moving pointers from opposite ends or in tandem, we avoid checking every O(N^2) combination.

## ⚙️ Approach

Uses Two Pointers to systematically eliminate possibilities.

## 🧪 Edge Cases

- Empty data structures (`n == 0`)

## 📊 Complexity Analysis

- **Time Complexity**: O(N) - Linear Scan
- **Space Complexity**: O(1) - Constant Space

## 📝 Lessons Learned

Key takeaway: Two pointers optimally navigate bounded monotonic sequences without O(N^2) pairs.
