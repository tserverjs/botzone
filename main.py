import os
import time
from PIL import Image, ImageDraw
import easyocr
from cloakbrowser import launch

USERNAME = os.getenv("BOTZONE_USER", "YOUR_USERNAME")
PASSWORD = os.getenv("BOTZONE_PASS", "YOUR_PASSWORD")

def debug_ocr_and_click():
    reader = easyocr.Reader(['en', 'fr'])
    browser = launch(headless=True, humanize=True)

    try:
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("[*] 打开页面并打开登录弹窗...")
        page.goto("https://botzone.fr", wait_until="domcontentloaded")
        time.sleep(2)
        page.click("button.btn.btn-ghost:has-text('Connexion')")
        time.sleep(1.5)

        # 填写登录凭据
        page.fill("#loginId", USERNAME)
        page.fill("#loginPw", PASSWORD)
        time.sleep(1)

        # 截图并使用 OCR 识别
        screenshot_path = "modal_screenshot.png"
        page.screenshot(path=screenshot_path)
        
        results = reader.readtext(screenshot_path)
        target_box = None

        for bbox, text, prob in results:
            if "verify you are human" in text.lower() or "verify" in text.lower():
                print(f"[OCR] 匹配到文本: '{text}' (置信度: {prob:.2f})")
                target_box = bbox
                break

        if target_box:
            # 获取识别到的文本框四角坐标
            x_min, y_min = target_box[0]
            x_max, y_max = target_box[2]
            
            # 计算目标点击位置（假设复选框在文本左侧约 30~40 像素）
            click_x = int(x_min - 35)
            click_y = int((y_min + y_max) / 2)
            
            print(f"[*] 拟点击坐标计算为: ({click_x}, {click_y})")

            # --- 可视化：在截图上绘制红色圆圈并保存 ---
            img = Image.open(screenshot_path)
            draw = ImageDraw.Draw(img)
            radius = 8
            draw.ellipse(
                (click_x - radius, click_y - radius, click_x + radius, click_y + radius),
                outline="red",
                width=3
            )
            debug_img_path = "click_target_debug.png"
            img.save(debug_img_path)
            print(f"[+] 标注点击位置的调试图已保存至: {debug_img_path}")

            # --- 标准 CDP 点击事件发送 (已修复 type 参数) ---
            cdp = context.new_cdp_session(page)
            
            # 移动鼠标至坐标
            cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved",
                "x": click_x,
                "y": click_y
            })
            time.sleep(0.1)

            # 按下鼠标
            cdp.send("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": click_x,
                "y": click_y,
                "button": "left",
                "clickCount": 1
            })
            time.sleep(0.1)

            # 释放鼠标 (修正 type 为 mouseReleased)
            cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": click_x,
                "y": click_y,
                "button": "left",
                "clickCount": 1
            })
        else:
            print("[-] 未在截图上识别到对应的验证文本")

        time.sleep(3)
        page.click("#loginBtn")
        time.sleep(3)

    finally:
        browser.close()

if __name__ == "__main__":
    debug_ocr_and_click()
