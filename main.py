import os
import time
import random
import easyocr
from cloakbrowser import launch

# 优先从环境变量获取凭据（适用于 GitHub Actions）
USERNAME = os.getenv("BOTZONE_USER", "YOUR_USERNAME")
PASSWORD = os.getenv("BOTZONE_PASS", "YOUR_PASSWORD")


def run_cloak_automation():
    reader = easyocr.Reader(["en", "fr"])

    print("[*] 正在启动 CloakBrowser 防关联隐形浏览器...")
    browser = launch(headless=True, humanize=True)

    try:
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir="recordings/",
            record_video_size={"width": 1280, "height": 800},
        )

        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        print("[*] 正在打开 Botzone 首页...")
        page.goto("https://botzone.fr", wait_until="domcontentloaded")
        time.sleep(2)

        # 1. 点击 Connexion 按钮触发登录弹窗
        print("[*] 点击 Connexion 按钮...")
        page.click("button.btn.btn-ghost:has-text('Connexion')")
        time.sleep(1.5)

        # 2. 填写用户名和密码（修正为正确的 ID 选择器 #loginId 与 #loginPw）
        print("[*] 填写登录凭据...")
        page.fill("#loginId", USERNAME)
        page.fill("#loginPw", PASSWORD)
        time.sleep(1)

        # 3. 截取弹窗屏幕并使用 OCR 识别复选框
        print("[*] 截图并识别验证码文字位置...")
        screenshot_path = "modal_screenshot.png"
        page.screenshot(path=screenshot_path)

        results = reader.readtext(screenshot_path)
        target_box = None

        for bbox, text, prob in results:
            print(f"[OCR] 识别到的文本: '{text}' (置信度: {prob:.2f})")
            if any(
                kw in text.lower()
                for kw in ["human", "verify", "robot", "turnstile", "vérifier"]
            ):
                target_box = bbox
                break

        # 4. CDP 底层模拟点击
        cdp = context.new_cdp_session(page)

        if target_box:
            x_min, y_min = target_box[0]
            x_max, y_max = target_box[2]

            click_x = max(10, int(x_min - 25))
            click_y = int((y_min + y_max) / 2)

            print(f"[*] 计算得到复选框点击坐标: ({click_x}, {click_y})")

            cdp.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mousePressed",
                    "x": click_x,
                    "y": click_y,
                    "button": "left",
                    "clickCount": 1,
                },
            )
            time.sleep(random.uniform(0.05, 0.15))
            cdp.send(
                "Input.dispatchMouseReleased",
                {
                    "type": "mouseReleased",
                    "x": click_x,
                    "y": click_y,
                    "button": "left",
                    "clickCount": 1,
                },
            )
        else:
            print("[!] OCR 未能准确定位文本，尝试常规 iframe 元素定位...")
            captcha_frame = page.frame_locator(
                "iframe[src*='challenges.cloudflare.com']"
            ).first
            if captcha_frame.count() > 0:
                captcha_frame.locator("body").click()

        time.sleep(3)

        # 5. 点击提交登录按钮
        print("[*] 点击 Se connecter 按钮...")
        page.click("#loginBtn")
        time.sleep(5)

        context.tracing.stop(path="trace.zip")
        context.close()
        print("[+] 脚本执行完成，视频与轨迹已保存。")

    except Exception as e:
        print(f"[-] 运行过程中发生错误: {e}")
        raise e
    finally:
        browser.close()


if __name__ == "__main__":
    run_cloak_automation()
