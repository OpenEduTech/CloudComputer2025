# [Expression Add Operators][title]

## Description

Given a string `num` that contains only digits and an integer `target`, return
_**all possibilities** to insert the binary operators _`'+'`_,_`'-'`_,
and/or_`'*'`_between the digits of_`num` _so that the resultant expression
evaluates to the_`target` _value_.

Note that operands in the returned expressions **should not** contain leading
zeros.

**Note** that a number can contain multiple digits.



**Example 1:**
            Input: num = "123", target = 6    Output: ["1*2*3","1+2+3"]    Explanation: Both "1*2*3" and "1+2+3" evaluate to 6.    

**Example 2:**
            Input: num = "232", target = 8    Output: ["2*3+2","2+3*2"]    Explanation: Both "2*3+2" and "2+3*2" evaluate to 8.    

**Example 3:**
            Input: num = "3456237490", target = 9191    Output: []    Explanation: There are no expressions that can be created from "3456237490" to evaluate to 9191.    



**Constraints:**

  * `1 <= num.length <= 10`
  * `num` consists of only digits.
  * `-231 <= target <= 231 - 1`


**Tags:** Math, String, Backtracking

**Difficulty:** Hard

## 思路

[title]: https://leetcode.com/problems/expression-add-operators
