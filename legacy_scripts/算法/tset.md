下面给你一份「SQL 笔试题」小合集，难度从 **基础 → 中级 → 高阶**，覆盖单表查询、多表关联、窗口函数、递归、性能调优等常见考点。每题都给出 **场景描述 + 建表语句 + 问题 + 期望输出示例**，方便直接落地笔试或面试实战。

---

### 0️⃣ 通用建表与数据
```sql
-- 部门表
CREATE TABLE dept (
  dept_id   INT PRIMARY KEY,
  dept_name VARCHAR(50)
);

-- 员工表
CREATE TABLE emp (
  emp_id   INT PRIMARY KEY,
  emp_name VARCHAR(50),
  dept_id  INT,
  salary   DECIMAL(10,2),
  hire_date DATE,
  mgr_id   INT,
  FOREIGN KEY (dept_id) REFERENCES dept(dept_id),
  FOREIGN KEY (mgr_id)   REFERENCES emp(emp_id)
);

-- 示例数据
INSERT INTO dept VALUES
(10,'人事部'),(20,'研发部'),(30,'销售部');

INSERT INTO emp VALUES
(1001,'Alice',10, 8000,'2020-01-01',NULL),
(1002,'Bob'  ,20,12000,'2019-03-15',1005),
(1003,'Cindy',20,15000,'2020-07-20',1005),
(1004,'David',20,15000,'2021-05-10',1005),
(1005,'Eric' ,20,25000,'2018-02-01',NULL),
(1006,'Frank',30,10000,'2022-03-12',NULL);
```

---

### 1️⃣ 基础题（单表过滤、排序、聚合）
**Q1** 查询 2020 年及以后入职，薪资高于 10000 的员工姓名和入职日期，按薪资降序排列。  
<details>
<summary>参考SQL</summary>

```sql
SELECT emp_name, hire_date
FROM   emp
WHERE  hire_date >= '2020-01-01'
  AND  salary > 10000
ORDER BY salary DESC;
```
</details>

---

### 2️⃣ 中级题（多表 JOIN、分组聚合）
**Q2** 统计每个部门的平均薪资，显示部门名称和平均薪资，过滤掉平均薪资低于 10000 的部门。  
<details>
<summary>参考SQL</summary>

```sql
SELECT d.dept_name, AVG(e.salary) AS avg_sal
FROM   dept d
JOIN   emp  e ON d.dept_id = e.dept_id
GROUP  BY d.dept_name
HAVING AVG(e.salary) >= 10000;
```
</details>

---

### 3️⃣ 中级题（子查询 + EXISTS）
**Q3** 找出“没有任何下属”的员工（即不是任何人的 mgr_id）。  
<details>
<summary>参考SQL</summary>

```sql
SELECT *
FROM   emp e
WHERE  NOT EXISTS (
        SELECT 1
        FROM   emp sub
        WHERE  sub.mgr_id = e.emp_id
      );
```
</details>

---

### 4️⃣ 高阶题（窗口函数）
**Q4** 在每个部门内，按薪资从高到低给员工排名，输出员工姓名、部门名称、薪资、排名。  
<details>
<summary>参考SQL</summary>

```sql
SELECT emp_name,
       dept_name,
       salary,
       RANK() OVER (PARTITION BY e.dept_id ORDER BY salary DESC) AS rnk
FROM   emp e
JOIN   dept d ON e.dept_id = d.dept_id;
```
</details>

---

### 5️⃣ 高阶题（递归 CTE 组织树）
**Q5** 给定 emp 表的层级关系，查询以 Eric(1005) 为根的所有下属（多级）及其层级深度。  
<details>
<summary>参考SQL（MySQL 8.0+ / PostgreSQL）</summary>

```sql
WITH RECURSIVE sub AS (
    SELECT emp_id, emp_name, 0 AS depth
    FROM   emp
    WHERE  emp_id = 1005
    UNION ALL
    SELECT e.emp_id, e.emp_name, s.depth + 1
    FROM   emp e
    JOIN   sub s ON e.mgr_id = s.emp_id
)
SELECT * FROM sub;
```
</details>

---

### 6️⃣ 性能调优题（索引 & 执行计划）
**场景**  
`orders` 表 5000 万行，结构如下：
```sql
CREATE TABLE orders (
  order_id   BIGINT PRIMARY KEY,
  user_id    BIGINT,
  product_id BIGINT,
  amount     DECIMAL(10,2),
  order_date DATE,
  KEY idx_user (user_id)
);
```
**Q6** 写一条 SQL：查询最近 30 天指定 user_id 的订单总额，并说明如何优化索引。  
<details>
<summary>参考SQL + 优化思路</summary>

```sql
SELECT SUM(amount)
FROM   orders
WHERE  user_id = 123456
  AND  order_date >= CURDATE() - INTERVAL 30 DAY;
```
**优化**：  
1. 现有单列索引 `idx_user(user_id)` 过滤后仍要回表按日期再过滤 → 回表量大。  
2. 建立 **复合索引** `(user_id, order_date)` 或 `(user_id, order_date, amount)`，形成覆盖索引即可避免回表，显著减少 IO。  
3. 执行计划：看 `EXPLAIN` 是否出现 `Using index condition` + `Using where` → 理想情况下应看到 `range` 访问 + `covering index`。
</details>

---

### 7️⃣ 实战综合题（留作练习）
**场景**  
电商活动表 `promotion`（promo_id, start_dt, end_dt, discount_rate）  
订单表 `orders`（order_id, user_id, order_dt, promo_id, orig_amt, pay_amt）  
**Q7** 找出 **每笔订单** 参加的活动名称、活动折扣率、以及该订单是否享受了折扣（即支付金额 < 原价）。  
要求：  
- 输出列：order_id, promo_name, discount_rate, is_discounted  
- 未参加活动的订单 promo_name 显示 NULL  

（可自写建表脚本与测试数据，再给出 SQL。）

---

### 使用建议
- 笔试限时 60 分钟：选 1️⃣2️⃣3️⃣4️⃣6️⃣即可。  
- 面试手撕：现场电脑或白板，重点看 4️⃣5️⃣6️⃣，并追问执行计划。  
- 出题方：可把表名/字段翻译成英文，避免泄露原业务。