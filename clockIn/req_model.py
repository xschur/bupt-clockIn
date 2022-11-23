import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)


class ClockIn:
    __username = ""
    __password = ""
    __session = ""
    __login_url = "https://auth.bupt.edu.cn/authserver/login"
    __upload_url = "https://app.bupt.edu.cn/ncov/wap/default/save"
    __old_info_url = "https://app.bupt.edu.cn/ncov/wap/default/index?history"
    __headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 "
                      "Safari/537.36"
    }

    def __init__(self, _username, _password):
        self.__username = _username
        self.__password = _password
        self.__session = requests.session()

    def __get_execution(self):
        res = self.__session.get(url=self.__login_url, headers=self.__headers)
        text = BeautifulSoup(res.text, "html.parser")
        try:
            execution = list(text.select("input"))[3]
        except:
            logging.error(" get execution failed")
            return ""
        pattern = re.compile(r"value=\"([^\"]*)\"", re.MULTILINE | re.DOTALL)
        return re.findall(pattern, str(execution))

    def __get_cookie(self):
        params = self.__get_execution()
        if params == "":
            return
        data = {
            "username": self.__username,
            "password": self.__password,
            "submit": "登录",
            "type": params[0],
            "execution": params[1],
            "_eventId": params[2]
        }
        self.__session.post(url=self.__login_url, headers=self.__headers, data=data, allow_redirects=False)

    def __get_html(self):
        self.__get_cookie()
        res = self.__session.get(url=self.__old_info_url, headers=self.__headers)
        if res.status_code == 200:
            return res.text
        else:
            return ""

    def __get_old_info(self):
        try:
            res = BeautifulSoup(self.__get_html(), "html.parser")
        except:
            logging.error(" parse old info failed")
            return ""
        script = list(res.select("script[type='text/javascript']"))[1]
        pattern = re.compile(r"oldInfo: {.*?},$", re.MULTILINE | re.DOTALL)
        try:
            s = json.loads(re.findall(pattern, str(script))[0][9:-1])
        except:
            return ""
        s["created"] = int(time.time())
        s["date"] = time.strftime("%Y%m%d")
        return s

    def save(self):
        jsonobj = self.__get_old_info()
        if jsonobj == "":
            return ""
        res = self.__session.post(url=self.__upload_url, headers=self.__headers, data=jsonobj)
        return res.text


def upload(username, password):
    clock_in = ClockIn(username, password)
    msg = clock_in.save()
    return msg


def wx_pusher(msg: str, js: json):
    wx_pusher_url = "http://wxpusher.zjiecode.com/api/send/message"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "appToken": js["appToken"],
        "content": msg,
        "contentType": 1,
        "uids": [js["uid"]],
    }
    if js["appToken"] == "" or js["uid"] == "":
        return
    res = requests.post(url=wx_pusher_url, headers=headers, json=data)
    return res


def server_push(msg: str, js: json):
    server_push_url = "https://sctapi.ftqq.com/{}.send?title={}".format(js["sendKey"], msg)
    headers = {
        'Content-type': 'application/x-www-form-urlencoded',
    }
    res = requests.post(url=server_push_url, headers=headers)
    try:
        params = json.loads(res.text)
        logging.info(" server push success ~")
    except:
        logging.error(" parse server push result failed ~")
    return res


def push_msg(msg: str, js: json):
    if "sendKey" in js and js["sendKey"] != "":
        return server_push(msg, js)
    if "appToken" in js and "uid" in js and js["appToken"] != "" and js["uid"] != "":
        return wx_pusher(msg, js)
