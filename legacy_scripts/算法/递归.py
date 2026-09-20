# 计算阶乘 示例1：计算阶乘
# 计算一个数的阶乘是理解递归的一个很好的起点。阶乘定义为：
# $$ n! = n \times (n-1) \times (n-2) \times \ldots \times 1 $$
# 当 $ n = 0 $ 或 $ n = 1 $ 时，$ n! = 1 $。
def factorial(n):
    # 基本情形
    if n == 0 or n == 1:
        return 1
    # 递归步骤
    else:
        return n * factorial(n-1)

# 示例2：斐波那契数列
# 斐波那契数列是一个著名的递归例子，其中每个数字是前两个数字的和。数列定义为：
# $$ F(n) = \begin{cases} 0 & \text{if } n=0 \ 1 & \text{if } n=1 \ F(n-1) + F(n-2) & \text{if } n>1 \end{cases} $$
def min_cost_climbing_stairs(cost):
    a, b = 0, 0               # 初始 dp[-2], dp[-1]
    for c in cost:
        a, b = b, min(a, b) + c
    return min(a, b)          # 最后一步可选 1 或 2 阶

# 示例
print(min_cost_climbing_stairs([10, 15, 20]))     # 15




# 示例3：树的遍历（深度优先搜索）
# 假设我们有一个简单的树结构，我们可以使用递归来遍历这棵树。例如，使用二叉树：
class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None
def traverse_tree(node):
    # 基本情形：如果节点为空，返回空（或进行其他处理）
    if node is None:
        return []
    # 递归步骤：先处理左子树，然后是当前节点，最后是右子树
    return traverse_tree(node.left) + [node.value] + traverse_tree(node.right)


