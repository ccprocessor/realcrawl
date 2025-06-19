from realcrawl.crawl.crawlers.auto_spider import AutoSpider
from realcrawl.crawl.utils import format_proxy
from realcrawl.log import logger


class OnePageSpider(AutoSpider):

    async def preview(self):
        await self.chrome.initialize(need_image=False, headless=True,
                                     proxy=format_proxy(self.config['proxy_list'], way='chrome'))
        try:
            async with self.lock:
                tab = await self.chrome.new_tab()
            task_data = {'url': self.start_url}
            await self.chrome.get(url=task_data['url'], tab=tab)
            page_response = await self.chrome.page_source(tab=tab)
            await self.extract_data(page_response, task_data)
        except Exception as e:
            logger.error(e)
            self.error_pages += 1
        self.signal_flag = False
