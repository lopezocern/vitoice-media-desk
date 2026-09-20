import pysnooper

#冒泡排序
# @pysnooper.snoop()
def bubble(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j] , arr[j+1] = arr[j+1], arr[j]
    return arr

#快速排序
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)


arrr = [3,45,56,6,234,23,4,2]

print(bubble(arrr))

def bubble_sort(arr):
    x = len(arr)
    for i in range(x):
        for j in range(0, x-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

sql = """
    select e.name, e.phone, d.dept_name
    from emp e
    join dept d on e.id = d.id
    where e.time > dataformat('2025-08-20','%y-%m-%d')
    and d.dept_code like '%tte%'
"""