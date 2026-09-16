import os
import time
import random
import warnings
from PIL import Image, ImageDraw

# 屏蔽第三方库的 UserWarning 警告日志
warnings.filterwarnings("ignore", category=UserWarning)
import easyocr
from cloakbrowser import launch

USERNAME = os.getenv("BOTZONE_USER", "YOUR_USERNAME")
PASSWORD = os.getenv("BOTZONE_PASS", "YOUR_PASSWORD")


def run_cloak_automation():
    print("[*] 正在初始化 EasyOCR 模型（首次加载可能需要几十秒）...")
    reader = easyocr.Reader(['en', 'fr'], gpu=False)
    print("[+] EasyOCR 初始化成功。")

    print("[*] 正在启动 CloakBrowser 防关联隐形浏览器...")
    browser = launch(headless=True, humanize=True)
    context = None
    try:
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

        print("[*] 点击 Connexion 按钮...")
        page.click("button.btn.btn-ghost:has-text('Connexion')")
        time.sleep(1.5)

        print("[*] 填写登录凭据...")
        page.fill("#loginId", USERNAME)
        page.fill("#loginPw", PASSWORD)
        time.sleep(1)

        # ===================== Turnstile 验证模块【DOM优先 + OCR兜底】=====================
        try:
            print("[*] 等待 Cloudflare Turnstile iframe 加载...")
            # 等待Cloudflare验证iframe出现
            page.wait_for_selector("iframe[title*='Cloudflare security challenge']", timeout=8000)
            turnstile_frame = page.frame_locator("iframe[title*='Cloudflare security challenge']")
            checkbox_locator = turnstile_frame.locator("input[type='checkbox']")
            checkbox_locator.wait_for(timeout=5000)

            box = checkbox_locator.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                print(f"✅ DOM定位成功，复选框坐标 ({cx:.1f}, {cy:.1f})")

                # 模拟人类鼠标移动轨迹
                page.mouse.move(
                    cx - random.randint(40, 80),
                    cy - random.randint(20, 50)
                )
                time.sleep(random.uniform(0.15, 0.3))
                page.mouse.move(cx, cy, steps=random.randint(8, 15))
                time.sleep(random.uniform(0.06, 0.12))

                page.mouse.down()
                time.sleep(random.uniform(0.08, 0.16))
                page.mouse.up()
                print("[+] DOM模式点击复选框完成，等待验证响应")
                time.sleep(3)
        except Exception dom_err:
            print(f"⚠️ DOM定位失败，启用OCR兜底方案，错误信息：{dom_err}")
            print("[*] 截图并执行 OCR 识别...")
            screenshot_path = "modal_screenshot.png"
            page.screenshot(path=screenshot_path)
            results = reader.readtext(screenshot_path)
            target_box = None
            for bbox, text, prob in results:
                print(f"[OCR] 识别文本: '{text}' (置信度: {prob:.2f})")
                if any(kw in text.lower() for kw in ["verify", "human", "robot", "turnstile", "vérifier"]):
                    target_box = bbox
                    break

            if target_box:
                text_left, text_top = target_box[0]
                text_right, text_bottom = target_box[2]
                text_cy = (text_top + text_bottom) / 2
                # 复选框在文字左侧，动态偏移
                click_x = int(text_left - random.randint(55, 70))
                click_y = int(text_cy)
                click_x = max(10, click_x)

                print(f"[*] OCR得到复选框坐标: ({click_x}, {click_y})")
                # 在截图绘制红色圆圈标记点击位置，用于调试
                img = Image.open(screenshot_path)
                draw = ImageDraw.Draw(img)
                r = 8
                draw.ellipse(
                    (click_x - r, click_y - r, click_x + r, click_y + r),
                    outline="red",
                    width=3
                )
                debug_img_path = "click_target_debug.png"
                img.save(debug_img_path)
                print(f"[+] 调试图保存至 {debug_img_path}")

                # OCR模式下的人类鼠标移动+点击
                page.mouse.move(
                    click_x - random.randint(40, 80),
                    click_y - random.randint(20, 50)
                )
                time.sleep(0.2)
                page.mouse.move(click_x, click_y, steps=10)
                time.sleep(0.1)
                page.mouse.down()
                time.sleep(random.uniform(0.08, 0.15))
                page.mouse.up()
                print("[+] OCR兜底模式点击复选框完成")
                time.sleep(3)
            else:
                print("[!] OCR也未识别到验证文本，跳过复选框点击")
        # ==================================================================================

        print("[*] 等待 5 秒观察响应...")
        time.sleep(5)
        print("[*] 点击 Se connecter 提交按钮...")
        page.click("#loginBtn")
        time.sleep(5)

        context.tracing.stop(path="trace.zip")
    except Exception as e:
        print(f"[-] 运行报错: {e}")
        raise e
    finally:
        if context:
            print("[*] 保存视频录制并关闭上下文...")
            context.close()
        browser.close()
        print("[+] 浏览器已安全退出。")


if __name__ == "__main__":
    run_cloak_automation()
