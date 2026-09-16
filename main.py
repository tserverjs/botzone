import os
import time
import random
from PIL import Image, ImageDraw
import easyocr
from cloakbrowser import launch

USERNAME = os.getenv("BOTZONE_USER", "YOUR_USERNAME")
PASSWORD = os.getenv("BOTZONE_PASS", "YOUR_PASSWORD")

def run_cloak_automation():
    reader = easyocr.Reader(['en', 'fr'])

    print("[*] 正在启动 CloakBrowser 防关联隐形浏览器...")
    browser = launch(headless=True, humanize=True)

    # 声明 context 和 page 变量以便在 finally 中安全关闭
    context = None
    try:
        # 1. 配置上下文与视频录制
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir="recordings/",
            record_video_size={"width": 1280, "height": 800}
        )

        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        print("[*] 正在打开 Botzone 首页...")
        page.goto("https://botzone.fr", wait_until="domcontentloaded")
        time.sleep(2)

        # 2. 点击 Connexion 按钮
        print("[*] 点击 Connexion 按钮...")
        page.click("button.btn.btn-ghost:has-text('Connexion')")
        time.sleep(1.5)

        # 3. 填写用户名和密码
        print("[*] 填写登录凭据...")
        page.fill("#loginId", USERNAME)
        page.fill("#loginPw", PASSWORD)
        time.sleep(1)

        # 4. 截图并使用 OCR 识别
        screenshot_path = "modal_screenshot.png"
        page.screenshot(path=screenshot_path)

        results = reader.readtext(screenshot_path)
        target_box = None

        for bbox, text, prob in results:
            print(f"[OCR] 识别到的文本: '{text}' (置信度: {prob:.2f})")
            if any(kw in text.lower() for kw in ["verify", "human", "robot", "turnstile", "vérifier"]):
                target_box = bbox
                break

        if target_box:
            x_min, y_min = target_box[0]
            x_max, y_max = target_box[2]

            # 计算复选框坐标（在文本左侧约 35 像素）
            click_x = max(10, int(x_min - 35))
            click_y = int((y_min + y_max) / 2)

            print(f"[*] 计算得到复选框点击坐标: ({click_x}, {click_y})")

            # --- 可视化：绘制红色圆圈标记点击点 ---
            img = Image.open(screenshot_path)
            draw = ImageDraw.Draw(img)
            r = 8
            draw.ellipse((click_x - r, click_y - r, click_x + r, click_y + r), outline="red", width=3)
            debug_img_path = "click_target_debug.png"
            img.save(debug_img_path)
            print(f"[+] 标记点击位置的调试图已保存至: {debug_img_path}")

            # --- 模拟人类鼠标移动轨迹并点击 ---
            print("[*] 模拟鼠标平滑移动至目标点...")
            # 1) 先移动到偏离位置
            page.mouse.move(click_x - random.randint(50, 100), click_y - random.randint(30, 80))
            time.sleep(0.2)

            # 2) 移动到目标坐标
            page.mouse.move(click_x, click_y, steps=10)
            time.sleep(0.1)

            # 3) 执行按下与释放
            page.mouse.down()
            time.sleep(random.uniform(0.08, 0.15))
            page.mouse.up()
            print("[+] 鼠标点击完成")

        else:
            print("[!] OCR 未能准确定位文本，尝试回退定位...")
            captcha_frame = page.frame_locator("iframe[src*='challenges.cloudflare.com']").first
            if captcha_frame.count() > 0:
                captcha_frame.locator("body").click()

        # 5. 等待验证响应并提交
        print("[*] 等待 5 秒观察验证状态...")
        time.sleep(5)

        print("[*] 点击 Se connecter 按钮...")
        page.click("#loginBtn")
        time.sleep(5)

        # 停止 Trace 追踪
        context.tracing.stop(path="trace.zip")

    except Exception as e:
        print(f"[-] 运行过程中发生错误: {e}")
        raise e
    finally:
        # 必须显式关闭 context 才能保存录制的视频！
        if context:
            print("[*] 正在关闭 Context 并导出录制视频...")
            context.close()
        browser.close()
        print("[+] 浏览器已关闭。")

if __name__ == "__main__":
    run_cloak_automation()
