# [Split Array With Minimum Difference][title]

## Description

You are given an integer array `nums`.

Split the array into **exactly** two subarrays, `left` and `right`, such that
`left` is **strictly increasing ** and `right` is **strictly decreasing**.

Return the **minimum possible absolute difference** between the sums of `left`
and `right`. If no valid split exists, return `-1`.



**Example 1:**

Input: nums = [1,3,2]

Output: 2

Explanation:

`i` | `left` | `right` | Validity | `left` sum | `right` sum | Absolute difference  
---|---|---|---|---|---|---  
0 | [1] | [3, 2] | Yes | 1 | 5 | `|1 - 5| = 4`  
1 | [1, 3] | [2] | Yes | 4 | 2 | `|4 - 2| = 2`  
  
Thus, the minimum absolute difference is 2.

**Example 2:**

Input: nums = [1,2,4,3]

Output: 4

Explanation:

`i` | `left` | `right` | Validity | `left` sum | `right` sum | Absolute difference  
---|---|---|---|---|---|---  
0 | [1] | [2, 4, 3] | No | 1 | 9 | -  
1 | [1, 2] | [4, 3] | Yes | 3 | 7 | `|3 - 7| = 4`  
2 | [1, 2, 4] | [3] | Yes | 7 | 3 | `|7 - 3| = 4`  
  
Thus, the minimum absolute difference is 4.

**Example 3:**

Input: nums = [3,1,2]

Output: -1

Explanation:

No valid split exists, so the answer is -1.



**Constraints:**

  * `2 <= nums.length <= 105`
  * `1 <= nums[i] <= 105`


**Tags:** Array, Prefix Sum

**Difficulty:** Medium

## 思路

[title]: https://leetcode.com/problems/split-array-with-minimum-difference
