import requests
from lxml import html
from lib import YDM
import json
import logging
import logging.handlers
import shutil
import time
import config

session = requests.session()
loginTimes = 3
orderTimes = 3
captchaFile = 'captcha.png'

# 默认的logging使用GBK
# logging.basicConfig(format='%(levelname)s[%(asctime)s]:%(message)s', level=logging.DEBUG, filename='log/yfd.log')
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler('log/yfd.log', encoding='utf-8')
handler.setFormatter(logging.Formatter('%(levelname)s[%(asctime)s][%(name)s]:%(message)s'))
root_logger.addHandler(handler)


def get_login_csrf():
    """
    生成登录 csrf
    :return: string
    """
    r = session.get('https://e.efunds.com.cn/')
    tree = html.fromstring(r.content)
    csrf = tree.xpath("//input[@name='_csrf']/@value")
    return csrf.pop()


def get_login_captcha():
    """
    获取验证码并在线打码
    :return: list
    """
    filename = 'captcha.png'
    r = session.get('https://e.efunds.com.cn/security/captcha?type=LOGIN&time=' + str(time.time()), stream=True)
    with open(filename, 'wb') as f:
        for chunk in r:
            f.write(chunk)
    logging.debug('识别验证码')
    return YDM.get_captcha(filename)


def login(csrf, captcha=None, count=1):
    """
    自动登录
    :param csrf:
    :param captcha:
    :param count:
    :return: bool
    """
    if count > 3:
        logging.error('登录错误次数超过：' + str(count))
        return False
    data = {'_csrf': csrf, 'isSecured': 'false', 'certType': '0',
            'certID': config.yfd_username, 'password': config.yfd_password}
    if captcha is not None:
        data['captcha'] = captcha[1]
    r = session.post('https://e.efunds.com.cn/loginasync', data=data)
    result = json.loads(r.text.strip())
    if result['status'] == 'SUCCESS':
        return True
    elif result['status'] == 'CAPTCHA_EXCEPTION':
        if captcha is not None:
            logging.debug('打码错误' + captcha[0])
            shutil.copyfile(captchaFile, 'error_captcha/' + captcha[0] + '_' + captcha[1] + '.png')
        return login(csrf, get_login_captcha(), ++count)
    else:
        logging.debug('登录错误：' + json.dumps(result))
        if captcha is not None:
            return login(csrf, get_login_captcha(), ++count)
        else:
            return login(csrf, None, ++count)


def get_order_crsf(code):
    r = session.get('https://e.efunds.com.cn/cart/subscriptions?form&fundCode=' + code)
    tree = html.fromstring(r.content)
    csrf = tree.xpath("//input[@id='csrf']/@value")
    return csrf.pop()


def order(csrf, fund):
    data = {'_csrf': csrf, 'fundCode': fund['code'], 'currency': '156', 'amount': fund['money']}
    r = session.post('https://e.efunds.com.cn/order/subscriptions', data=data)
    tree = html.fromstring(r.content)
    trade_account = tree.xpath("//input[@class='fastBankRadio']/@value")
    if not trade_account:  # 为空
        logging.error('生成订单失败')
        return False
    trade_account = trade_account.pop()
    form = tree.forms[0]
    data = {}
    for i in form.inputs:
        try:
            if i.name is not None and i.value is not None:
                if i.name == 'isOneClick':
                    i.value = 'true'
                elif i.name == 'tradePassword':
                    i.value = config.yfd_password
                elif i.name == 'tradeAccount':
                    i.value = trade_account
                data[i.name] = i.value
        except:
            continue
    r = session.post('https://e.efunds.com.cn/payment/expresspayments', data=data)
    if "订单提交中" in r.text:
        return True
    else:
        # todo 可以查询订单判断是否成功
        logging.error('订单可能失败' + r.text)
        return True  # 防止重复提交


def is_holiday():
    """
    判断当前日是否为节假日
    :return: bool
    """
    date = time.strftime('%Y%m%d', time.localtime())
    # 节假日接口
    server_url = "http://api.goseek.cn/Tools/holiday?date="
    r = requests.get(server_url + date)
    data = json.loads(r.text)
    return data['data'] > 0


def main():
    # if is_holiday():
    #     return 0

    flag = False
    csrf = get_login_csrf()
    for i in range(3):
        try:
            if login(csrf):
                flag = True
                break
        except Exception as e:
            logging.exception('登录出错')
            time.sleep(5)
    if not flag:
        logging.error('登录失败')
        return 0

    # with open('cookie.pkl', 'wb') as f:
    #     pickle.dump(session.cookies, f)

    # with open('cookie.pkl', 'rb') as file:
    #     o = pickle.load(file)
    #     session.cookies.update(o)

    for fund in config.yfd:
        flag = False
        csrf = get_order_crsf(fund['code'])
        for i in range(3):
            try:
                if order(csrf, fund):
                    flag = True
                    break
            except Exception as e:
                logging.exception('购买出错')
                time.sleep(5)

        if flag:
            logging.debug('购买成功: ' + fund['code'] + ' ' + fund['money'])
        else:
            logging.error('购买失败: ' + fund['code'] + ' ' + fund['money'])


main()






