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
    # 调试时建议改成 headless=False，方便肉眼观察鼠标轨迹
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

        # 等待 Cloudflare Turnstile iframe 出现
        print("[*] 等待 Cloudflare Turnstile 加载...")
        try:
            page.wait_for_selector('iframe[src*="challenges.cloudflare.com"]', timeout=10000)
            time.sleep(1.5)  # 再等一下让复选框真正渲染完成
            print("[+] Turnstile iframe 已出现。")
        except Exception as e:
            print(f"[!] 等待 Turnstile iframe 超时，继续尝试 OCR: {e}")

        print("[*] 截图并执行 OCR 识别...")
        screenshot_path = "modal_screenshot.png"
        page.screenshot(path=screenshot_path)

        results = reader.readtext(screenshot_path)
        print(f"[OCR] 共识别到 {len(results)} 个文本块")

        # 收集所有可能匹配的框，取最左边的那个（最接近复选框）
        candidates = []
        for bbox, text, prob in results:
            print(f"[OCR] 识别到的文本: '{text}' (置信度: {prob:.2f})")
            if any(kw in text.lower() for kw in [
                "verify", "human", "robot", "turnstile", "vérifier", "you are"
            ]):
                candidates.append((bbox, text, prob))

        if candidates:
            # 按 x_min 排序，取最左边的匹配结果
            candidates.sort(key=lambda x: x[0][0][0])
            target_box, matched_text, prob = candidates[0]
            print(f"[+] 最终选用最左边匹配文本: '{matched_text}' (置信度 {prob:.2f})")

            x_min, y_min = target_box[0]
            x_max, y_max = target_box[2]

            # 动态计算偏移量（根据文字高度），比固定减 35 更稳
            text_height = max(20, y_max - y_min)
            click_x = max(10, int(x_min - text_height * 1.3))
            click_y = int((y_min + y_max) / 2)

            print(f"[*] 计算得到复选框点击坐标: ({click_x}, {click_y})")

            # 在截图上标注红色点击圆圈 + 蓝色文字框（方便调试）
            img = Image.open(screenshot_path)
            draw = ImageDraw.Draw(img)
            r = 10
            draw.ellipse(
                (click_x - r, click_y - r, click_x + r, click_y + r),
                outline="red", width=3
            )
            draw.rectangle([x_min, y_min, x_max, y_max], outline="blue", width=2)
            debug_img_path = "click_target_debug.png"
            img.save(debug_img_path)
            print(f"[+] 标记点击位置的调试图已保存至: {debug_img_path}")

            # 模拟人类轨迹点击
            print("[*] 模拟鼠标移动并点击目标位置...")
            page.mouse.move(
                click_x - random.randint(50, 100),
                click_y - random.randint(30, 60)
            )
            time.sleep(random.uniform(0.15, 0.3))
            page.mouse.move(click_x, click_y, steps=random.randint(12, 20))
            time.sleep(random.uniform(0.08, 0.18))
            page.mouse.down()
            time.sleep(random.uniform(0.07, 0.14))
            page.mouse.up()
            print("[+] 点击事件发送完成。")
        else:
            print("[!] 未能在截图上识别到验证码提示文本，尝试备用方案...")

        # 备用方案：尝试直接点 iframe 内部（有时有效）
        try:
            frame = page.frame_locator('iframe[src*="challenges.cloudflare.com"]')
            frame.locator('input[type="checkbox"], label, .ctp-checkbox-label').first.click(
                timeout=3000, force=True
            )
            print("[+] iframe 内点击成功（备用方案）")
        except Exception as e:
            print(f"[!] iframe 点击失败（正常，很多时候被跨域限制）: {e}")

        print("[*] 等待 5 秒观察响应...")
        time.sleep(5)

        print("[*] 点击 Se connecter 提交按钮...")
        page.click("#loginBtn")
        time.sleep(5)

        # 可选：简单判断是否登录成功（根据实际页面调整选择器）
        try:
            if page.locator("text=Déconnexion").count() > 0 or "dashboard" in page.url.lower():
                print("[+] 登录似乎成功！")
            else:
                print("[!] 登录后页面未检测到成功标志，请检查截图/视频")
        except:
            pass

        context.tracing.stop(path="trace.zip")
        print("[+] 追踪文件已保存: trace.zip")

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
