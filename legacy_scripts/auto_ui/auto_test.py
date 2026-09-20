import pyautogui
import time


def click(x,y):
    # time.sleep(1)
    pyautogui.click(x, y)

def button_1(x=1):
    for i in range(x):
        click(2171,1182)
def button_2(x=1):
    for i in range(x):
        click(2171,1207)
def button_3(x=1):
    for i in range(x):
        click(2171,1234)

def idol_manage(x):
    for i in range(x):
        click(1979,1325)
        button_1(2)
        button_2()
        button_3()
        button_2()
        button_1()
def thief():
    button_1(8)
def lover():
    button_1(3)
    button_2()
    button_3(2)
    button_1()
    # button_2()
    button_1()
def check():
    button_1()
    button_2()
    button_1(4)
def swim():
    click(2381,986)
    button_1(5)
    button_2(2)
    button_3()
    button_1(3)
    button_2(3)
    button_3(2)
    button_1()
    time.sleep(1)

# time.sleep(2)
# time.sleep(5)
currentMouseX, currentMouseY = pyautogui.position()
print(currentMouseX, currentMouseY)
# idol_manage(20)
# thief()
# lover()
# check()
for i in range(100):
    print(i)
    click(2165,1190)
