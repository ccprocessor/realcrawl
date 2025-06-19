import asyncio
import json
import os
import time
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import aiofiles
from lxml import html

from realcrawl.crawl.browser import Chrome
from realcrawl.crawl.dupfilter import Dupfilter
from realcrawl.crawl.network import RobotsChecker, http_request
from realcrawl.crawl.queue import Queue
from realcrawl.crawl.utils import (calc_resp_id, convert_str_cookie,
                                   filter_media_urls, format_proxy, format_url,
                                   generate_sha256, generate_timestamp,
                                   generate_track_id, get_base_url, get_domain)
from realcrawl.log import logger


class AutoSpider:
    signal_flag = True
    crawled_pages = 0
    error_pages = 0
    proj_dir = None
    save_file = None
    limit_domain = None

    def __init__(self, config, start_url):
        self.loop = asyncio.get_event_loop()
        self.lock = asyncio.Lock()
        self.start_url = start_url
        self.config = config
        self.set_default_value()
        self.chrome = Chrome()
        self.queue = Queue(path=self.proj_dir + '/.cache')
        self.df = Dupfilter(path=self.proj_dir + '/.cache')
        self.robots_checker = RobotsChecker()

    def set_default_value(self):
        if not self.config.get('download_delay', None):
            self.config['download_delay'] = 3
        if not self.config.get('max_workers', None):
            self.config['max_workers'] = 3
        if not self.config.get('max_crawl_depth', None):
            self.config['max_crawl_depth'] = 10
        if not self.config.get('include_urls', None):
            self.config['include_urls'] = []
        if not self.config.get('exclude_urls', None):
            self.config['exclude_urls'] = []
        self.config['exclude_urls'].extend(
            ['/login', '/signup', '/signin', 'UserLogin', '/sign-in', '/sign-up', '/signout'])
        if not self.config.get('timeout', None):
            self.config['timeout'] = 30
        if not self.config.get('max_pages', None):
            self.config['max_pages'] = 100 * 10000
        if not self.config.get('proxy_list', None):
            self.config['proxy_list'] = None
        if not self.config.get('max_retries', None):
            self.config['max_retries'] = 3
        if 'ignore_sitemap' not in self.config:
            self.config['ignore_sitemap'] = True
        if 'ignore_robots' not in self.config:
            self.config['ignore_robots'] = False
        if 'require_login' not in self.config:
            self.config['require_login'] = False
        if 'allow_backwards_links' not in self.config:
            self.config['allow_backwards_links'] = False
        if self.config.get('cookie', None):
            self.config['cookie'] = convert_str_cookie(self.config['cookie'], self.start_url)

        self.limit_domain = get_domain(self.start_url, self.config['allow_backwards_links'])
        self.proj_dir = self.config['data_storage_path'].rstrip('/')
        os.makedirs(self.proj_dir + '/.cache', exist_ok=True)

    @property
    def queue_size(self):
        return self.queue.qsize()

    async def parse_sitemap(self, sitemap_url):
        try:
            if '.xml' not in sitemap_url.lower():
                parse_result = urlparse(sitemap_url)
                sitemap_url = parse_result.scheme + '://' + parse_result.netloc + '/sitemap.xml'
            response = await http_request(sitemap_url, timeout=30, proxy=format_proxy(self.config['proxy_list']))
            root = ET.fromstring(response.content)
            if root.tag.endswith('sitemapindex'):
                for sitemap in root.findall('.//{*}sitemap'):
                    loc = sitemap.find('{*}loc').text.strip()
                    await self.parse_sitemap(loc)
            elif root.tag.endswith('urlset'):
                for url in root.findall('.//{*}url'):
                    loc = url.find('{*}loc').text.strip()
                    if not await self.add_df(generate_sha256(loc)):
                        self.add_queue({'url': loc, 'crawl_depth': 2})
        except Exception as e:
            logger.error(e)

    async def save_data(self, data):
        async with self.lock:
            if self.crawled_pages - self.config['max_pages'] >= 0:
                self.signal_flag = False
                return
            await self.save_file.write(json.dumps(data, ensure_ascii=False) + '\n')
            self.crawled_pages += 1

    def exclude_urls(self, url):
        if self.config['exclude_urls']:
            if any(filter_item in url for filter_item in self.config['exclude_urls']):
                return True
            else:
                return False
        return False

    def include_urls(self, url):
        if self.config['include_urls']:
            if any(filter_item in url for filter_item in self.config['include_urls']):
                return True
            else:
                return False
        return True

    def add_queue(self, data):
        if 'crawl_depth' not in data:
            data['crawl_depth'] = 1
        if data['crawl_depth'] > self.config['max_crawl_depth']:
            return
        self.queue.put_nowait(data)

    async def add_df(self, data):
        async with self.lock:
            return self.df.is_crawled(data)

    async def preview(self):
        await self.chrome.initialize(need_image=False, headless=True,
                                     proxy=format_proxy(self.config['proxy_list'], way='chrome'),
                                     cookie=self.config.get('cookie', None))
        if not self.config['ignore_robots']:
            await self.robots_checker.fetch_robots_txt(base_url=self.start_url,
                                                       proxy=format_proxy(self.config['proxy_list']))

    async def start(self):
        try:
            self.save_file = await aiofiles.open(self.proj_dir + '/datas.jsonl', mode='a', encoding='utf-8')
            await self.preview()
            if self.signal_flag:
                tasks = [
                    self.loop.create_task(self.attach()),
                    self.loop.create_task(self.watch()),
                    *[self.loop.create_task(self.crawl()) for _ in range(self.config['max_workers'])]
                ]
                for task in tasks:
                    try:
                        await task
                    except Exception as e:
                        logger.error(f'child err, {str(e)}')
        except Exception as e:
            logger.error(f'{str(e)}')
        await self.clean()

    async def find_more_urls(self, page_response, task_data, shtml):
        base_href = get_base_url(shtml, page_response.url)
        current_crawl_depth = task_data.get('crawl_depth', 1)
        for new_url in list(set(shtml.xpath('//a/@href'))):
            new_url = format_url(base_href, new_url)
            if not new_url:
                continue
            if not self.robots_checker.can_fetch(new_url):
                continue
            if self.exclude_urls(new_url):
                continue
            if not self.include_urls(new_url):
                continue
            if filter_media_urls(new_url):
                continue
            if get_domain(new_url, self.config['allow_backwards_links']) == self.limit_domain and not await self.add_df(
                    generate_sha256(new_url)):
                new_task_data = {
                    'url': new_url, 'crawl_depth': current_crawl_depth + 1
                }
                self.add_queue(new_task_data)

    async def attach(self):
        if not self.config['ignore_sitemap']:
            await self.parse_sitemap(self.start_url)
        self.add_queue({
            'url': self.start_url
        })

    async def watch(self):
        tmp_time = 0
        tmp_crawled_pages = self.crawled_pages
        tmp_error_pages = self.error_pages
        while self.signal_flag:
            await asyncio.sleep(60)
            if not tmp_time:
                tmp_time = int(time.time())
                continue
            current_time = int(time.time())
            current_crawled_pages = self.crawled_pages
            current_error_pages = self.error_pages
            if current_crawled_pages + current_error_pages == 0:
                continue
            logger.info(
                f'success pages {current_crawled_pages}, error pages {current_error_pages},'
                f' success rate {round((current_crawled_pages) / (current_crawled_pages + current_error_pages) * 100, 1)}%,'
                f' speed {int((current_crawled_pages + current_error_pages - tmp_crawled_pages - tmp_error_pages) / (current_time - tmp_time) * 60)}/min,'
                f' remaining queue count {self.queue_size}, max pages limit {self.config["max_pages"]}')
            tmp_time = current_time
            tmp_crawled_pages = current_crawled_pages
            tmp_error_pages = current_error_pages

    async def extract_data(self, page_response, task_data):
        res = {}
        res['html'] = page_response.html
        res['track_id'] = generate_track_id()
        res['crawl_time'] = generate_timestamp()
        res['url'] = task_data['url']
        res['response_url'] = page_response.url
        res['status'] = page_response.status_code
        await self.save_data(res)

    async def crawl(self):
        wait_num = 20
        tab = None
        while self.signal_flag:
            try:
                task_data = self.queue.get_nowait()
                wait_num = 20
                if self.crawled_pages - self.config['max_pages'] >= 0:
                    self.signal_flag = False
                    break
            except Exception:
                wait_num -= 1
                await asyncio.sleep(5)
                if wait_num < 0:
                    self.signal_flag = False
                    break
                else:
                    continue
            try:
                if not tab:
                    async with self.lock:
                        tab = await self.chrome.new_tab()

                await self.chrome.get(url=task_data['url'], tab=tab)
                page_response = await self.chrome.page_source(tab=tab)
                shtml = html.fromstring(page_response.html)

                if task_data['url'] != self.start_url:
                    # resp url&domain filter
                    if task_data['url'] != page_response.url:
                        if await self.add_df(generate_sha256(page_response.url)):
                            continue
                    if get_domain(page_response.url, self.config['allow_backwards_links']) != self.limit_domain:
                        continue

                    # response html sha256 filter
                    if await self.add_df(calc_resp_id(page_response.url, shtml)):
                        continue
                else:
                    await self.add_df(generate_sha256(self.start_url))

                await self.find_more_urls(page_response, task_data, shtml)

                await self.extract_data(page_response, task_data)

                await asyncio.sleep(self.config['download_delay'])

            except Exception as e:
                if 'has been closed' in str(e):
                    self.signal_flag = False
                logger.error(e)
                self.error_pages += 1

    def close(self, signum, frame):
        self.signal_flag = False

    async def clean(self):
        if self.save_file:
            await self.save_file.close()
        if self.chrome:
            await self.chrome.close()
            self.chrome = None
        if self.queue:
            self.queue.close()
            self.queue = None
        if self.df:
            self.df.close()
            self.df = None
