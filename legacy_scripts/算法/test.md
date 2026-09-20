以下是为你量身准备的**SQL 与 Python 笔试题合集**，涵盖基础、中高级内容，重点突出**函数解释、跨表联查**、**数据处理逻辑**，适合测试工程师/自动化测试/数据验证类岗位。

---

## ✅ 一、SQL 笔试题（含函数解释 + 跨表联查）

### **题目1：统计每位员工的入职天数**

```sql
SELECT 
  employee_id,
  name,
  DATEDIFF(CURDATE(), hire_date) AS days_on_job
FROM 
  employees;
```

* `DATEDIFF(date1, date2)`：计算两个日期之间的天数差。
* `CURDATE()`：获取当前日期。
* **考察点：** 日期函数使用、字段选择。

---

### **题目2：跨表联查：找出每个部门工资最高的员工**

```sql
SELECT 
  e.department_id,
  e.name,
  e.salary
FROM 
  employees e
JOIN (
  SELECT 
    department_id, 
    MAX(salary) AS max_salary
  FROM 
    employees
  GROUP BY department_id
) m 
ON e.department_id = m.department_id AND e.salary = m.max_salary;
```

* `MAX()`：聚合函数，求最大值。
* 子查询：获取每个部门的最高工资。
* 外层联表：筛选匹配最大工资的员工。
* **考察点：** 子查询 + 多条件联表。

---

### **题目3：统计每月注册用户数**

```sql
SELECT 
  DATE_FORMAT(register_time, '%Y-%m') AS month,
  COUNT(*) AS user_count
FROM 
  users
GROUP BY 
  DATE_FORMAT(register_time, '%Y-%m');
```

* `DATE_FORMAT()`：将日期格式化为"年-月"。
* `GROUP BY`：按月分组。
* **考察点：** 时间分组聚合、格式处理。

---

### **题目4：查询订单金额大于用户平均订单金额的订单**

```sql
SELECT 
  o.user_id, o.order_id, o.amount
FROM 
  orders o
JOIN (
  SELECT 
    user_id, 
    AVG(amount) AS avg_amount
  FROM 
    orders
  GROUP BY user_id
) a ON o.user_id = a.user_id
WHERE o.amount > a.avg_amount;
```

* `AVG()`：平均函数。
* **考察点：** 子查询 + 多表对比。

---

### **题目5：查找连续签到3天及以上的用户**

假设签到表 `checkin(user_id, checkin_date)`：

```sql
SELECT DISTINCT c1.user_id
FROM checkin c1
JOIN checkin c2 ON c1.user_id = c2.user_id AND DATEDIFF(c2.checkin_date, c1.checkin_date) = 1
JOIN checkin c3 ON c1.user_id = c3.user_id AND DATEDIFF(c3.checkin_date, c1.checkin_date) = 2;
```

* 利用自连接模拟连续3天签到。
* **考察点：** 日期差判断、自连接。

---

## ✅ 二、Python 笔试题（附详细解释）

### **题目1：统计字符串中每个字符出现次数**

```python
from collections import Counter

s = "hello world"
counter = Counter(s)
print(counter)
```

* `collections.Counter`：内置字典计数器，自动统计每个元素出现次数。

---

### **题目2：列表中找出前3大值**

```python
nums = [5, 2, 9, 1, 7, 6]
top3 = sorted(nums, reverse=True)[:3]
print(top3)
```

* `sorted(list, reverse=True)`：降序排列。
* 切片 `[:3]`：取前3名。

---

### **题目3：扁平化嵌套列表**

```python
nested = [[1, 2], [3, 4], [5]]
flat = [x for sublist in nested for x in sublist]
print(flat)
```

* 列表推导式，两个 for 实现展平二维列表。

---

### **题目4：找出两个列表中的交集元素**

```python
a = [1, 2, 3, 4]
b = [3, 4, 5, 6]
intersection = list(set(a) & set(b))
print(intersection)
```

* 利用集合运算 `&` 求交集。

---

### **题目5：用 Python 判断一个字符串是否是回文**

```python
def is_palindrome(s):
    return s == s[::-1]

print(is_palindrome("madam"))  # True
```

* `s[::-1]`：反转字符串。
* 回文即“正着读”和“反着读”相同。

---

### **题目6：读取 CSV 并计算某列平均值**

```python
import csv

with open("data.csv", newline='') as f:
    reader = csv.DictReader(f)
    values = [float(row["score"]) for row in reader]
    print(sum(values) / len(values))
```

* `csv.DictReader`：按列名读取。
* **适用于测试数据分析场景。**

---

### **题目7：异常处理**

```python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("除数不能为0")
```

* **考察点：** 异常捕获、错误类型识别。

---

如果你有偏向某方向（比如：更偏数据验证 / Web 自动化 / 数据库 / 多表联查），我可以进一步为你定制更多**模拟面试题 + 答案解析 + 场景套题**。

是否需要我整理成 Word 或 PDF 文件，方便打印或面试复习？
