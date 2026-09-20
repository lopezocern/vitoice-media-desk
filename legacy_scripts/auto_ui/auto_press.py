import pyautogui
import time

key = input('重复按键：')
for i in range(100):
    pyautogui.press(key)
    time.sleep(0.5)