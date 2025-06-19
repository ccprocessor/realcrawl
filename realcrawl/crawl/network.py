from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

DEFAULT_HEADER = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
}


async def http_request(url, method='get', data=None, params=None, json=None, headers=DEFAULT_HEADER, timeout=10,
                       max_retries=3, proxy=None):
    for i in range(max_retries):
        try:
            async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=timeout,
                                         headers=headers, proxy=proxy) as client:
                if method == 'get':
                    response = await client.get(url, params=params)
                else:
                    response = await client.post(url, data=data, json=json)
            response.raise_for_status()
            return response
        except Exception:
            pass
    else:
        raise Exception('http_request max retry')


class RobotsChecker:
    have_robots = False

    def __init__(self):
        self.rp = RobotFileParser()

    async def fetch_robots_txt(self, base_url, proxy=None):
        parse_result = urlparse(base_url)
        robots_url = parse_result.scheme + '://' + parse_result.netloc + '/robots.txt'
        try:
            rules = await http_request(robots_url, proxy=proxy)
            self.rp.parse(rules.text.splitlines())
        except Exception:
            return
        self.have_robots = True

    def can_fetch(self, url, user_agent='*'):
        if not self.have_robots:
            return True
        return self.rp.can_fetch(user_agent, url)
