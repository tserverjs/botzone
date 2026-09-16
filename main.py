import os
import time
import random
import easyocr
from cloakbrowser import launch

# 优先从环境变量获取凭据（适用于 GitHub Actions），本地运行可替换默认值
USERNAME = os.getenv("BOTZONE_USER", "YOUR_USERNAME")
PASSWORD = os.getenv("BOTZONE_PASS", "YOUR_PASSWORD")


def run_cloak_automation():
    # 初始化 EasyOCR（支持英文与法文）
    reader = easyocr.Reader(["en", "fr"])

    print("[*] 正在启动 CloakBrowser 防关联隐形浏览器...")
    # 启动 CloakBrowser 内核（启用拟人化鼠标/键盘轨迹）
    browser = launch(headless=True, humanize=True)

    try:
        # 1. 创建 Context，配置录制视频尺寸
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir="recordings/",
            record_video_size={"width": 1280, "height": 800},
        )

        # 2. 开启 Trace 追踪功能
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        print("[*] 正在打开 Botzone 首页...")
        page.goto("https://botzone.fr", wait_until="domcontentloaded")
        time.sleep(2)

        # 3. 点击 Connexion 按钮触发登录弹窗
        print("[*] 点击 Connexion 按钮...")
        page.click("button.btn.btn-ghost:has-text('Connexion')")
        time.sleep(1.5)

        # 4. 填写用户名和密码
        print("[*] 填写登录凭据...")
        page.fill("input[name='username']", USERNAME)
        page.fill("input[name='password']", PASSWORD)
        time.sleep(1)

        # 5. 截取弹窗屏幕并使用 OCR 识别复选框
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

        # 6. CDP 底层模拟点击
        cdp = context.new_cdp_session(page)

        if target_box:
            x_min, y_min = target_box[0]
            x_max, y_max = target_box[2]

            # 计算文字框左侧复选框的大致点击坐标
            click_x = max(10, int(x_min - 25))
            click_y = int((y_min + y_max) / 2)

            print(f"[*] 计算得到复选框点击坐标: ({click_x}, {click_y})")

            # 模拟 MousePress / MouseRelease 事件
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

        # 等待人机验证响应
        time.sleep(3)

        # 7. 点击提交登录按钮
        print("[*] 点击 Se connecter 按钮...")
        page.click("#loginBtn")
        time.sleep(5)

        # 保存 Trace 日志
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
