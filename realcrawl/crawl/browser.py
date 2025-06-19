import os

from playwright.async_api import async_playwright


class ChromePageResponse:
    def __init__(self, html='', screen_img='', url='', status_code=200):
        self.html = html
        self.screen_img = screen_img
        self.url = url
        self.status_code = status_code


class Chrome:
    playwright_server = None
    browser = None
    context = None

    async def initialize(self, need_image=True, headless=False, proxy=None, cookie=None):
        """异步初始化 Playwright 和浏览器"""
        self.playwright_server = await async_playwright().start()
        flags = [
            '--disable-blink-features=AutomationControlled',  # 防止网站通过 navigator.webdriver 或其他特征检测到浏览器被自动化控制（如反爬虫机制）
            '--disable-infobars',  # 禁用信息栏（Infobar），例如“Chrome 正在被自动化控制”的提示
            '--disable-breakpad',  # 禁用 Breakpad（崩溃报告工具）
            '--disable-client-side-phishing-detection',  # 禁用客户端的钓鱼网站检测功能。
            '--disable-hang-monitor',  # 禁用浏览器的挂起监控（Hang Monitor）
            # '--disable-popup-blocking',  # 禁用弹出窗口拦截功能
            '--disable-prompt-on-repost',  # 禁用页面重新加载时的确认提示（例如表单数据丢失警告）
            '--no-first-run',  # 跳过浏览器的首次运行流程（如欢迎页面、默认设置等）
            '--disable-gpu',  # 禁用 GPU 硬件加速
            '--disable-gpu-compositing',  # 禁用 GPU 合成（Compositing）
            '--disable-software-rasterizer',  # 避免在 GPU 不可用时使用 CPU 进行渲染，减少 CPU 资源消耗。通常与 --disable-gpu 一起使用
            '--no-sandbox',  # 禁用沙箱（Sandbox）机制
            '--disable-dev-shm-usage',  # 禁用 /dev/shm 共享内存
            '-no-default-browser-check',  # 禁用检查默认浏览器的提示
            '--ignore-certificate-errors',  # 忽略 SSL/TLS 证书错误（如自签名证书）
            '--ignore-certificate-errors-spki-list',  # 忽略 SSL/TLS 证书错误（如自签名证书）
            '--disable-renderer-backgrounding',  # 确保后台标签页中的 JavaScript 执行不受限制
            '--disable-ipc-flooding-protection',  # 禁用 IPC（进程间通信）洪泛保护
            '--disable-background-timer-throttling',  # 禁用后台页面的定时器节流,
            '--test-type=webdriver',
            '--start-maximized'  # 窗口最大化
        ]
        if not need_image:
            flags.extend([
                '--blink-settings=imagesEnabled=false',  # 禁用 Blink 引擎的图片加载
                # '--disable-remote-fonts', # 禁用远程字体加载
                '--disable-images',  # 与 --blink-settings=imagesEnabled=false 类似，但更直接地阻止图片渲染
                # '--disable-javascript' # 禁用 JavaScript 执行

            ])

        self.browser = await self.playwright_server.chromium.launch(headless=headless,
                                                                    args=flags,
                                                                    ignore_default_args=[
                                                                        '--enable-automation'],
                                                                    proxy=proxy)
        self.context = await self.browser.new_context(no_viewport=True)
        cur_file = os.path.abspath(__file__)
        js_path = os.path.join(os.path.dirname(cur_file), 'stealth.min.js')
        await self.context.add_init_script(path=js_path)
        if cookie:
            await self.context.add_cookies(cookie)

    async def new_tab(self):
        return await self.context.new_page()

    async def get(self, url, tab, timeout=30, max_retries=3):
        err = None
        for retry in range(max_retries):
            try:
                await tab.goto(url=url, timeout=timeout * 1000, wait_until='networkidle')
                break
            except Exception as e:
                err = e
                if 'has been closed' in str(e):
                    raise e
        else:
            if err:
                raise err

    async def page_source(self, tab):
        return ChromePageResponse(
            html=await tab.content(),
            url=tab.url,
            status_code=await tab.evaluate('window.performance.getEntries()[0].responseStatus')
        )

    async def click(self, xpath, tab):
        await tab.locator(f'xpath={xpath}').click()

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright_server:
            await self.playwright_server.stop()
