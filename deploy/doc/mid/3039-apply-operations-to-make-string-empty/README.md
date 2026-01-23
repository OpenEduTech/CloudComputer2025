# [Apply Operations to Make String Empty][title]

## Description

You are given a string `s`.

Consider performing the following operation until `s` becomes **empty** :

  * For **every** alphabet character from `'a'` to `'z'`, remove the **first** occurrence of that character in `s` (if it exists).

For example, let initially `s = "aabcbbca"`. We do the following operations:

  * Remove the underlined characters `s = "_**a**_ a** _bc_** bbca"`. The resulting string is `s = "abbca"`.
  * Remove the underlined characters `s = "_**ab**_ b _**c**_ a"`. The resulting string is `s = "ba"`.
  * Remove the underlined characters `s = "_**ba**_ "`. The resulting string is `s = ""`.

Return _the value of the string_`s` _right**before** applying the **last**
operation_. In the example above, answer is `"ba"`.



**Example 1:**
            Input: s = "aabcbbca"    Output: "ba"    Explanation: Explained in the statement.    

**Example 2:**
            Input: s = "abcd"    Output: "abcd"    Explanation: We do the following operation:    - Remove the underlined characters s = "_**abcd**_ ". The resulting string is s = "".    The string just before the last operation is "abcd".    



**Constraints:**

  * `1 <= s.length <= 5 * 105`
  * `s` consists only of lowercase English letters.


**Tags:** Array, Hash Table, Sorting, Counting

**Difficulty:** Medium

## 思路

[title]: https://leetcode.com/problems/apply-operations-to-make-string-empty
