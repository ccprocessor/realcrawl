import re
import time
import uuid
from hashlib import sha256
from urllib.parse import urljoin, urlparse

import tldextract
from lxml import html


def get_domain(url: str, allow_backwards_links=False) -> str:
    if allow_backwards_links:
        extracted = tldextract.extract(url)
        domain = '{}.{}'.format(extracted.domain, extracted.suffix)
        return domain
    else:
        parsed_url = urlparse(url)
        current_domain = parsed_url.netloc
        return current_domain


DISALLOW_EXT = [
    'jpg',
    'jpeg',
    'xml',
    'json',
    'rtf',
    'gif',
    'ico',
    'bmp',
    'tiff',
    'svs',
    'psd',
    'png',
    'svg',
    'webp',
    'mp3',
    'wav',
    'aac',
    'flac',
    'ogg',
    'mp4',
    'webm',
    'avi',
    'mov',
    'wmv',
    'flv',
    'mkv',
    'm4v',
    'opus',
    'm4a',
    'pdf',
    'doc',
    'docx',
    'xls',
    'xlsx',
    'ppt',
    'pptx',
    'txt',
    'apk',
    'tar',
    'gzip',
    'bin',
    'tgz',
    'xz',
    'gz',
    '7z',
    'rar',
    'exe',
    'zip',
    'swf',
    'wasm',
    'epub',
    'mobi',
    'woff',
    'woff2',
    'ttf',
    'otf',
    'eot',
    'css',
    'js'
]

DISALLOW_EXT_RE = r'\.' + r'$|\.'.join(DISALLOW_EXT) + '$'


def filter_media_urls(url: str) -> bool:
    link_path = urlparse(url).path
    if re.search(DISALLOW_EXT_RE, str(link_path).lower()):
        return True
    return False


def format_proxy(proxy_data, way='httpx'):
    if proxy_data:
        if way == 'httpx':
            proxy = f'{proxy_data["host"]}:{proxy_data["port"]}'
            if proxy_data.get('username', None):
                proxy = f'{proxy_data["username"]}:{proxy_data["password"]}@' + proxy
            proxy = proxy_data['type'] + '://' + proxy
            return proxy
        if way == 'chrome':
            '''
            proxy={"server": "http://proxy1.example.com:8080", "username": "user", "password": "pass"}
            '''
            proxy = {
                'server': proxy_data['type'] + '://' + f'{proxy_data["host"]}:{proxy_data["port"]}'
            }
            if proxy_data.get('username', None):
                proxy['username'] = proxy_data['username']
                proxy['password'] = proxy_data['password']
            return proxy
    return None


def generate_track_id():
    return str(uuid.uuid4())


def generate_timestamp():
    return int(time.time())


def generate_sha256(data):
    return sha256(data.encode('utf-8')).hexdigest()


def calc_resp_id(url, html_ele):
    parse_url = urlparse(url)
    prefix_url = parse_url.scheme + '://' + parse_url.netloc + parse_url.path
    feature_eles = []
    for tag_name in ['title', 'h1', 'h2', 'meta']:
        tags = html_ele.xpath('//' + tag_name)
        for tag in tags:
            if tag_name == 'meta':
                meta_property = tag.get('property', '')
                if meta_property and meta_property in ['og:image', 'og:release_date', 'og:title']:
                    feature_eles.append(tag)
                meta_name = tag.get('name', '')
                if meta_name and meta_name in ['description', 'keywords', 'author']:
                    feature_eles.append(tag)
            else:
                feature_eles.append(tag)
    feature_str = ''.join(
        [html.tostring(feature_ele, encoding=str, method='html') for feature_ele in feature_eles]).replace('\n',
                                                                                                           '')
    feature_str += ''.join(html_ele.xpath('//a//text()'))
    return generate_sha256(prefix_url.rstrip('/') + '/' + feature_str)


def get_base_url(html_ele, url):
    try:
        base_href = html_ele.xpath('//head/base/@href')
        if base_href:
            base_href = base_href[0].strip()
            if base_href and '#' not in base_href:
                base_href = urljoin(url, base_href)
                return base_href
    except Exception:
        pass
    return url


def format_url(root_url, url):
    url = url.strip()
    if url.startswith('#') or url.startswith('javascript:') or url.startswith('about:blank'):
        return
    if url:
        return urljoin(root_url, url)
    return


def convert_str_cookie(cookie_str: str, url):
    cookie_list = []
    if not cookie_str:
        return cookie_list
    for cookie in cookie_str.split(';'):
        cookie = cookie.strip()
        if not cookie:
            continue
        cookie_list_one = cookie.split('=')
        if len(cookie_list_one) != 2:
            continue
        cookie_list.append({'name': cookie_list_one[0], 'value': cookie_list_one[1], 'url': url
                            })
    return cookie_list
