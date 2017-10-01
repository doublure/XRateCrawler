#! python2
# coding:utf-8

from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from email.header import Header


def get_rates(target_url):

    r = requests.get(target_url)
    r.encoding = 'utf-8'

    soup = BeautifulSoup(r.text, 'lxml')
    fx_info = soup.select('tr')

    update_time_info = fx_info[-2].get_text().strip()
    update_time_str = update_time_info.split(' ', 1)[1].replace('/', '-')
    update_time = datetime.strptime(update_time_str, '%Y-%m-%d %H:%M:%S')

    ex_rate_list = []
    for currency_detail in fx_info[2:-2]:
        ex_rate = currency_detail.select('td')
        ex_rate_dic = {

            'currency_name': ex_rate[0].string.strip(),
            'we_buy': ex_rate[1].string.strip(),
            'we_sell': ex_rate[2].string.strip(),
            'last_updated': update_time
        }
        ex_rate_list.append(ex_rate_dic)
    return ex_rate_list


def add_to_db(dic_list, collection_name):

    if not already_exists(dic_list[0]['last_updated'], collection_name):
        collection_name.insert_many(dic_list)


def already_exists(last_updated, collection_name):

    if collection_name.find({'last_updated': last_updated}).count():
        print 'Until now there is no new update'
        return True
    else:
        return False


def start_db():

    conn = MongoClient('localhost', 27017)
    ex_rate_db = conn['ex_rate_db']
    ex_rate = ex_rate_db['ex_rate']
    return ex_rate


def judge_value(currency_dic, collection_name):

    date_to_compare = currency_dic['last_updated'] - timedelta(30)
    ex_rate_list_we_buy = []
    ex_rate_list_we_sell = []
    for item in collection_name.find({
        '$and': [{'currency_name': currency_dic['currency_name']}, {'last_updated': {'$gt': date_to_compare}}]
    }):

        ex_rate_list_we_buy.append(item['we_buy'])
        ex_rate_list_we_sell.append(item['we_sell'])

    min_we_buy = min(ex_rate_list_we_buy)
    max_we_buy = max(ex_rate_list_we_buy)
    max_we_sell = max(ex_rate_list_we_sell)
    min_we_sell = min(ex_rate_list_we_sell)

    output_alert = ''

    if min_we_buy < currency_dic['we_buy'] < max_we_buy and min_we_sell < currency_dic['we_sell'] < max_we_sell:
        return None
    else:

        if currency_dic['we_buy'] == min_we_buy:
            output_alert += 'we buy value of ' + currency_dic['currency_name'] + ' reached lowest since 30 days\n'
        if currency_dic['we_buy'] == max_we_buy:
            output_alert += 'we buy value of ' + currency_dic['currency_name'] + ' reached highest since 30 days\n'

        if currency_dic['we_sell'] == min_we_sell:
            output_alert += 'we sell value of ' + currency_dic['currency_name'] + ' reached lowest since 30 days\n'
        if currency_dic['we_sell'] == max_we_sell:
            output_alert += 'we sell value of ' + currency_dic['currency_name'] + ' reached highest since 30 days\n'

        return output_alert


def send_email(content, receiver='song_chunpeng@163.com,'):

    sender = 'xxx@xxx.com' # input mail address of sender
    recipient = receiver
    subject = 'lowest FX Rate reached since 30 days'
    smtpserver = 'smtp.163.com' # 这里输入smtp地址
    username = 'xxx@xxx.com' # 这里输入用户名
    password = 'xxxxxxxx' # 这里输入密码

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['subject'] = Header(subject, 'utf-8')
    msg['from'] = sender
    msg['to'] = recipient

    smtp = smtplib.SMTP_SSL(smtpserver, 465) # 这里要根据情况调整端口
    print 'logging in'
    smtp.login(username, password)
    print 'logged in'
    smtp.sendmail(sender, recipient, msg.as_string())
    smtp.quit()
    print 'mail sent'

if __name__ == '__main__':

    url = '''
    https://www.bochk.com/whk/rates/exchangeRatesForCurrency/exchangeRatesForCurrency-input.action?lang=hk
    '''

    ex_rate_collection = start_db()
    print 'db connected'
    fx_rate_list = get_rates(url)
    print 'exchange rates list retrieved'
    add_to_db(fx_rate_list, ex_rate_collection)

    text_to_mail = ''
    for currency_to_check in fx_rate_list:
        text_alert = judge_value(currency_to_check, ex_rate_collection)
        if text_alert:
            text_to_mail += text_alert

    if text_to_mail:
        send_email(text_to_mail, 'xxxx@163.com')
