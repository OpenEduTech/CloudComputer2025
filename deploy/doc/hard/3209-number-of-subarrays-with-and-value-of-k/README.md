# [Number of Subarrays With AND Value of K][title]

## Description

Given an array of integers `nums` and an integer `k`, return the number of
subarrays of `nums` where the bitwise `AND` of the elements of the subarray
equals `k`.



**Example 1:**

Input: nums = [1,1,1], k = 1

Output: 6

Explanation:

All subarrays contain only 1's.

**Example 2:**

Input: nums = [1,1,2], k = 1

Output: 3

Explanation:

Subarrays having an `AND` value of 1 are: `[_**1**_ ,1,2]`, `[1,_**1**_ ,2]`,
`[_**1,1**_ ,2]`.

**Example 3:**

Input: nums = [1,2,3], k = 2

Output: 2

Explanation:

Subarrays having an `AND` value of 2 are: `[1,**_2_** ,3]`, `[1,_**2,3**_]`.



**Constraints:**

  * `1 <= nums.length <= 105`
  * `0 <= nums[i], k <= 109`


**Tags:** Array, Binary Search, Bit Manipulation, Segment Tree

**Difficulty:** Hard

## 思路

[title]: https://leetcode.com/problems/number-of-subarrays-with-and-value-of-k
