import os
import time
import random
import easyocr
# 引入 CloakBrowser 原生库
from cloakbrowser import launch

USERNAME = os.getenv("BOTZONE_USER", "YOUR_USERNAME")
PASSWORD = os.getenv("BOTZONE_PASS", "YOUR_PASSWORD")

def run_cloak_automation():
    reader = easyocr.Reader(['en', 'fr'])

    print("[*] 正在启动 CloakBrowser 防关联隐形浏览器...")
    # 启动 CloakBrowser 内核，开启拟人化操作 (humanize)
    browser = launch(
        headless=True,       # CI/CD 无头模式，配合 Xvfb 运行
        humanize=True        # 启用拟人化鼠标轨迹与输入延迟
    )

    # 创建上下文并配置视频录制
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        record_video_dir="recordings/"
    )
    
    # 开启操作轨迹追踪
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()

    print("[*] 打开 Botzone 首页...")
    page.goto("https://botzone.fr", wait_until="domcontentloaded")
    time.sleep(2)

    # 1. 点击 Connexion 按钮
    print("[*] 点击 Connexion 按钮...")
    page.click("button.btn.btn-ghost:has-text('Connexion')")
    time.sleep(1.5)

    # 2. 填写用户名和密码
    print("[*] 填写登录凭据...")
    page.fill("input[name='username']", USERNAME)
    page.fill("input[name='password']", PASSWORD)
    time.sleep(1)

    # 3. 截取弹窗并使用 OCR 识别复选框
    print("[*] 截图并识别验证码位置...")
    screenshot_path = "modal_screenshot.png"
    page.screenshot(path=screenshot_path)

    results = reader.readtext(screenshot_path)
    target_box = None
    for bbox, text, prob in results:
        if any(kw in text.lower() for kw in ["human", "verify", "robot", "turnstile", "vérifier"]):
            target_box = bbox
            break

    # 4. CDP 点击模拟
    cdp = context.new_cdp_session(page)
    if target_box:
        x_min, y_min = target_box[0]
        x_max, y_max = target_box[2]
        click_x = max(10, int(x_min - 25))
        click_y = int((y_min + y_max) / 2)
        
        print(f"[*] 模拟点击坐标: ({click_x}, {click_y})")
        cdp.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": click_x, "y": click_y, "button": "left", "clickCount": 1
        })
        time.sleep(random.uniform(0.05, 0.15))
        cdp.send("Input.dispatchMouseReleased", {
            "type": "mouseReleased", "x": click_x, "y": click_y, "button": "left", "clickCount": 1
        })
    else:
        print("[!] OCR 未找到标识，尝试直接点击 iframe...")
        captcha_frame = page.frame_locator("iframe[src*='challenges.cloudflare.com']").first
        if captcha_frame.count() > 0:
            captcha_frame.locator("body").click()

    time.sleep(3)

    # 5. 提交登录
    print("[*] 点击登录提交按钮...")
    page.click("#loginBtn")
    time.sleep(5)

    # 保存报告并退出
    context.tracing.stop(path="trace.zip")
    context.close()
    browser.close()
    print("[+] 流程执行完毕。")

if __name__ == "__main__":
    run_cloak_automation()
