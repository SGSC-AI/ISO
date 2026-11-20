import os
import logging
import traceback
from io import TextIOWrapper

import urllib3
import requests
from bs4 import BeautifulSoup


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FILE_CACHE: dict[str, TextIOWrapper] = {}
ID_CACHE: dict[str, list[str]] = {}
FNAME = 'out/twcert-%s%s.csv'
BASE_URL = 'https://www.twcert.org.tw/tw/lp-169-1-%d-%d.html'
HEADERS = {
    'Accept': 'text/html',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en,en-US;q=0.9,zh-TW;q=0.8,zh;q=0.7',
    # 'Cache-Control': 'max-age=0',
    # 'Connection': 'keep-alive',
    # 'Host': 'www.twcert.org.tw',
    # 'Referer': 'https://www.twcert.org.tw/tw/lp-169-1-1-20.html',
    # 'Sec-Fetch-Dest': 'document',
    # 'Sec-Fetch-Mode': 'navigate',
    # 'Sec-Fetch-Site': 'same-origin',
    # 'Sec-Fetch-User': '?1',
    # 'Upgrade-Insecure-Requests': '1',
}


def fetch_url(number_per_page: int = 20, max_pages: int = 10, old_to_new: bool = True):
    for i in (range(max_pages, 0, -1) if old_to_new else range(1, max_pages+1)):
        url = BASE_URL % (i, number_per_page)
        resp = requests.get(url, headers=HEADERS, verify=False)
        if resp.status_code == 200:
            yield resp.content


def parse_id(href: str) -> str:
    """
    href: /tw/cp-169-7755-88823-1.html
    """
    return os.path.splitext(href)[0].split('/')[-1]


def read_ids(fname: str) -> list[str]:
    if not os.path.isfile(fname):
        return []
    try:
        with open(fname, 'r') as fp:
            # read first item of the first comma splits
            fp.readline(1) # title
            return [line.split(',')[0] for line in fp.readlines()]
    except Exception as e:
        print('Fail to read id from file, SKIP. Message:', str(e))
        logging.debug(traceback.format_exc())
        return []


def collect_data(old_to_new: bool = True, **kwargs):
    rows = []
    for html in fetch_url(**kwargs):
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('section.lp li a')
        rows.extend([
            {
                'id': parse_id(item.attrs.get('href')),
                'title': list(item.children)[1],
                'time': item.select_one('time').text, # type: ignore
            }
            for item in items
            if item.select_one('time') and list(item.children)[1] and item.attrs.get('href')
        ])
    return sorted(rows, key=lambda row: row['time'], reverse=not old_to_new)


def write_file(record: dict) -> bool:
    """
    record: (dict) title: str; time: yyyy-mm-dd
    """
    year, month, day = record['time'].split('-')
    fname = FNAME % (year, month)
    if fname not in FILE_CACHE:
        for _fp in FILE_CACHE.values():
            _fp.close()
        FILE_CACHE.clear()
        if os.path.isfile(fname):
            FILE_CACHE[fname] = open(fname, 'a')
            ID_CACHE[fname] = read_ids(fname)
        else:
            _fp = open(fname, 'w')
            FILE_CACHE[fname] = _fp
            _fp.write('id,title,date\n')
    fp = FILE_CACHE[fname]
    if record['id'] in ID_CACHE.get(fname, []):
        return False
    fp.write('%s,%s,%s\n'%(record['id'], record['title'], record['time']))
    return True


def main():
    os.makedirs(os.path.dirname(FNAME), exist_ok=True)
    # collect data
    old_to_new = True
    for record in collect_data(old_to_new=old_to_new):
        write_file(record)


if __name__ == "__main__":
    main()
