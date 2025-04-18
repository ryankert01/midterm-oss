import time
import requests
from bs4 import BeautifulSoup as bs
import configparser
import os
import re
import json

class Auto:
    def __init__(self, info):
        # 儲存已選課程
        self.courseList = []
        # 帳號資訊
        self.account = info[0]
        self.password = info[1]
        self.token = info[2]
        # 所有開課系所代碼（固定清單）
        self.deptdb = ['300', '302', '303', '305', '309', '322', '323', '325', '329', '330', '352', '353', '355', '500', '505', '530', '531', '532', '554', '600', '601', '602', '603', '604', '608', '621', '622', '623', '624', '656', '700', '304', '701', '702',
                       '705', '721', '722', '723', '724', '725', '751', '754', '800', '310', '311', '312', '313', '331', '332', '333', '359', '360', '361', '301', '307', '308', '326', '327', '328', '356', '357', '358', 'A00', 'A21', '901', '903', '904', '906', '907']

        # 建立 session 並模擬 user-agent
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'

        # 系統基本路徑
        self.baseURL = "https://portalfun.yzu.edu.tw/cosSelect/"
        self.loginUrl = '{}login.aspx'.format(self.baseURL)
        self.captchaUrl = '{}ImageCode.aspx'.format(self.baseURL)
        self.indexURL = '{}index.aspx'.format(self.baseURL)

        # 登入需要的欄位，部分欄位待動態填入
        self.loginPayLoad = {
            '__VIEWSTATE': '',
            '__VIEWSTATEGENERATOR': '',
            '__EVENTVALIDATION': '',
            'uid': self.account,
            'pwd': self.password,
            'Code': '',
            'Button1': '登入'
        }

    def login(self):
        loginTimes = 0
        while loginTimes < 29:
            loginTimes += 1
            # 清除 cookies 確保 session 乾淨
            self.session.cookies.clear()
            # 取得驗證碼（在 cookie 內）
            with self.session.get(self.captchaUrl, stream=True, allow_redirects=False) as captchaHtml:
                captcha = captchaHtml.cookies['CheckCode']

            # 抓取登入頁面動態欄位
            loginHtml = self.session.get(self.loginUrl)
            parser = bs(loginHtml.text, 'html.parser')
            self.loginPayLoad['__VIEWSTATE'] = parser.select("#__VIEWSTATE")[0]['value']
            self.loginPayLoad['__VIEWSTATEGENERATOR'] = parser.select("#__VIEWSTATEGENERATOR")[0]['value']
            self.loginPayLoad['__EVENTVALIDATION'] = parser.select("#__EVENTVALIDATION")[0]['value']
            self.loginPayLoad['Code'] = captcha

            # 嘗試登入
            result = self.session.post(self.loginUrl, data=self.loginPayLoad)

            # 成功判斷
            if ("parent.location='index.aspx'" in result.text):
                self.Consolelog('Login Successful! {}'.format(captcha))
                break
            else:
                self.Consolelog("Login Failed, Re-try!")

    def Consolelog(self, msg):
        # 輸出時間戳 log
        temp = "{} {} ".format(time.strftime(
            "[%Y-%m-%d %H:%M:%S]", time.localtime()), msg)
        print(temp)
    #    self.LineNotifyLog(temp)

    def remove(self, item):
        # 從 courseList 移除指定課程
        if (item in self.courseList):
            self.courseList.remove(item)

    def exec(self, course_YR):
        resDic = {}
        loading = 1
        for cd in self.deptdb:
            courseDept = cd
            html = self.session.get(self.indexURL)
            # 檢查 session 是否過期
            if "login.aspx?Lang=TW" in html.text:
                self.login()

            # 第一次 POST，選擇系所
            html = self.session.get(self.indexURL)
            parser = bs(html.text, 'html.parser')
            PrePayLoad = {
                '__EVENTTARGET': 'DDL_Dept',
                '__EVENTARGUMENT': '',
                '__LASTFOCUS': '',
                '__VIEWSTATE':  parser.select("#__VIEWSTATE")[0]['value'],
                '__VIEWSTATEGENERATOR': parser.select("#__VIEWSTATEGENERATOR")[0]['value'],
                '__EVENTVALIDATION': parser.select("#__EVENTVALIDATION")[0]['value'],
                'Q': 'RadioButton1',
                'DDL_YM': parser.select('option')[0]['value'],
                'DDL_Dept': courseDept,
                'DDL_Degree': '1'
            }

            prePost = self.session.post(self.indexURL, data=PrePayLoad)
            parser = bs(prePost.text, 'html.parser')

            # 第二次 POST，查詢特定學期課程
            PostPayLoad = {
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                '__LASTFOCUS': '',
                '__VIEWSTATE':  parser.select("#__VIEWSTATE")[0]['value'],
                '__VIEWSTATEGENERATOR': parser.select("#__VIEWSTATEGENERATOR")[0]['value'],
                '__EVENTVALIDATION': parser.select("#__EVENTVALIDATION")[0]['value'],
                'Q': 'RadioButton1',
                'DDL_YM': course_YR,
                'DDL_Dept': courseDept,
                'DDL_Degree': '0',
                'Button1': '確定'
            }

            postPost = self.session.post(self.indexURL, data=PostPayLoad)
            result = bs(postPost.text, "html.parser")

            # 解析資料
            resDic[courseDept] = self.getCourseInfo(result)

            print(f"loading: {loading}/{len(self.deptdb)} ~~")
            loading += 1

        return resDic

    def getCourseInfo(self, soup):
        # 爬課程資訊
        result = soup.select("#Table1")[0].select("tr")
        num = 0
        courseInfo = []

        # 無資料時直接回傳空 list
        if soup.text.find("無課程資料") != -1:
            return []

        for i in result:
            num += 1
            if (num % 2 == 1):
                continue  # 奇數行是 header

            tds = i.select("td")

            # 抓取欄位內容
            courseURL = self.baseURL + tds[1].select_one('a')['href'][2:]
            courseID = tds[1].select_one('a').text
            courseYear = tds[2].text
            courseName = tds[3].select_one('a').text
            isEnglish = True if tds[3].text.find("英語授課") != -1 else False
            courseType = tds[4].select_one('span').text

            # 課程時間特殊格式處理
            child = tds[5].select_one('span').text.split()
            courseTime = []
            for j, s in enumerate(child):
                if j == 0:
                    courseTime.append(s)
                elif j == len(child)-1:
                    courseTime.append(s[1:])
                else:
                    courseTime.append(s[1:len(s)-3])
                    courseTime.append(s[len(s)-3:])

            courseTeacher = tds[6].select_one('a').text if tds[6].select_one('a') else tds[6].text

            tempInfo = {'courseURL': courseURL, 'courseID': courseID, 'courseYear': courseYear, 'courseName': courseName, 'isEnglish': isEnglish, 'courseType': courseType, 'courseTime': courseTime, 'courseTeacher': courseTeacher}

            courseInfo.append(tempInfo)

        return courseInfo


if __name__ == "__main__":
    # 指定查詢的學年
    course_YR = ['111,1  ', '111,2  ', '110,1  ', '110,2  ']

    # 從環境變數讀取帳密
    info = ['', '', '0']
    info[0] = os.environ['ACCOUNT_TOKEN']
    info[1] = os.environ['ACCESS_TOKEN']

    if info[0] != '':
        bot = Auto(info)
        bot.login()

        res = {}
        for yr in course_YR:
            res[yr] = bot.exec(course_YR=yr)

        # 輸出 json 檔案
        obj = json.dumps(res, ensure_ascii=False)
        with open("static.json", "w") as outfile:
            outfile.write(obj)
