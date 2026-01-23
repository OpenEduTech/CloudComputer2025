# Recursion / 递归（课程笔记）

递归（recursion）是指一个定义或过程**在其自身的定义中引用自身**。在计算机科学中，递归通常表现为函数调用自身，通过**基例（base case）**终止，并在每一步把问题规模缩小。

相关概念：
- 递推关系（recurrence relation）：用自身先前项定义当前项。
- 数学归纳法（mathematical induction）：证明递推/递归定义性质的常用方法。
- 调用栈（call stack）：递归调用会不断压栈，可能导致栈溢出（stack overflow）。
- 分治（divide and conquer）：许多分治算法可以用递归实现（如归并排序）。

证据提示：在图谱证据 snippet 中，应同时提及 source/target 节点名称，便于 Check layer 通过。

