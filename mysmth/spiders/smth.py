import scrapy
from scrapy import FormRequest
from datetime import datetime
from util import csv 
import jieba
import re 
import json 

account = ''
password = ''

class SmthSpider(scrapy.Spider):
    name = 'smth'
    url_prefix = "https://mysmth.net"
    allowed_domains = ['www.mysmth.net']
    start_urls = ['https://www.mysmth.net/nForum/board/Stock?p={}'.format(i) for i in range(1, 6)]
    login_url = 'https://www.mysmth.net/nForum/user/ajax_login.json'
    log_file = "./log/{}".format(datetime.now().strftime("%Y-%m-%d-%H:%M:%S"))
    all_stocks = [line.strip() for line in open("data/stocks.txt", "r")]
    skip_list = [line.strip() for line in open("data/skiplist.txt", "r")]
    exact_matches = {}
    multi_matches = {}
    articles = {}
    stock_pattern = re.compile(r"\d{6}")

    def login(self):
        # print("login")
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "sec-ch-ua": "\"Google Chrome\";v=\"89\", \"Chromium\";v=\"89\", \";Not A Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest"
        }
        data = {
            'id': account,
            'passwd': password,
             # 'rememberme': "forever",
             # 'wp-submit': "登录",
             # 'redirect_to': "http://www.haoduofuli.wang/wp-admin/",
             # 'testcookie': "1"
        }
        yield scrapy.FormRequest(self.login_url,formdata=data, headers=headers, callback=self.after_login)

    def start_requests(self):
        # print("start requests")
        self.prepare_log()
        jieba.load_userdict("data/stocks.txt")
        jieba.load_userdict("data/terms.txt")
        return self.login()

    def closed(self, reason):
        # print("quit for reason: ".format(reason))
        print("------------------------------------------匹配结果---------------------------------------------")
        for item in sorted(self.exact_matches.items(), key=lambda kv:(-kv[1], kv[0])):
           print("{}被提到{}次，对应链接为：".format(item[0], item[1]))
           for link in self.articles[item[0]]:
               print(self.url_prefix+link)
	
        print("-------------------------------------以下是无法精确匹配的股票----------------------------------")
        for seg, stocks in self.multi_matches.items():
           print('{}匹配到多只股票，分别为：{}，对应链接：'.format(seg, " ，".join(stocks)))
           for link in self.articles[seg]:
               print(self.url_prefix+link)

    def prepare_log(self):
        csv.write(self.log_file, ["title", "author", "time"])

    def after_login(self, response):
        if response.status != 200:
            print("invalid status: {}".format(response.status))
            return
        msg = json.loads(response.text)
        if msg["ajax_st"] != 1:
            print("invalid response: {}".format(msg["ajax_msg"]))
            return
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)


    def parse(self, response):
        # print("in parse")
        data = []
        articles = response.xpath('/html/body/section/section/div[@class="b-content"]/table/tbody/tr[not(@*)]')
        for a in articles:
            title = a.xpath('td[@class="title_9"]/a/text()').get()
            if not title:
                continue
            link = a.xpath('td[@class="title_9"]/a/@href').get()
            author = a.xpath('td[@class="title_12"]/a/text()').get()
            time = a.xpath('td[@class="title_10"]/a/text()').get()
            # print("title={title}, author={author}, time={time}".format(**{"title":title, "author":author, "time": time}))
            # util.writecsv(self.log_file, [title, link, author, time])
            data.append([title, link, author, time])
        # print(content) 
        self.analyse(data)

    def analyse(self, content):
        for line in content:
            title, link, author, time = line
            # print("title is {}".format(title))
            res = self.stock_pattern.findall(title)
            for r in res: 
               # print("{} matches {}".format(title, r))
               self.exact_matches.setdefault(r, 0)
               self.exact_matches[r] += 1
               self.articles.setdefault(r, [])
               self.articles[r].append(link)
            seg_list = jieba.cut(title)
            # print("Full Mode: " + "/ ".join(seg_list))
            for seg in seg_list:
                if len(seg) < 2:
                    continue
                if seg in self.skip_list:
                    continue
                matches = set() 
                for stock in self.all_stocks:
                    if seg in stock:
                        # print("seg {} match stock {}".format(seg, stock)) 
                        matches.add(stock)
                if not matches:
                    continue
                if len(matches) == 1:
                    s = list(matches)[0]
                    self.exact_matches.setdefault(s, 0)
                    self.exact_matches[s] += 1
                    self.articles.setdefault(s, [])
                    self.articles[s].append(link)
                else:
                    # print("seg {} match stocks {}".format(seg, matches)) 
                    self.multi_matches.setdefault(seg, set())
                    self.multi_matches[seg].update(matches)
                    self.articles.setdefault(seg, [])
                    self.articles[seg].append(link)
        # print(self.exact_matches)
