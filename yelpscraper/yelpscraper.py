"""
Scrapping yelp reviews in zipcode.

ist558 project
"""
from urllib2 import urlopen
import re
import time
import random
import argparse
from bs4 import BeautifulSoup
#from utils.networker import *
from collections import deque
import os
import pandas as pd
import numpy as np


def get_yelp(zipcode, page_num):
    """get yelp address for given zipcode and page number."""
    return 'https://www.yelp.com/search?find_loc={}&start={}&cflt=restaurants'.format(
        zipcode, page_num)


def get_resturants(zipcode, page_num, tor=False):
    """get resturant names and web page."""
    if tor:
        try:
            page_url = get_yelp(zipcode, page_num)
            soup = BeautifulSoup(get(page_url).text, 'html.parser')
        except:
            print('tor, get_resturant failed')
            return [], False
    else:
        try:
            page_url = get_yelp(zipcode, page_num)
            soup = BeautifulSoup(urlopen(page_url).read(), 'html.parser')
        except:
            print('get_resturant failed')
            return [], False

    resturants = soup.findAll(
        'div',
        attrs={'class': re.compile(r'^search-result natural-search-result')})
    extracted = {}
    for resturant in resturants:
        name = resturant.find('a', {'class': 'biz-name'}).getText()
        address = 'https://www.yelp.com/' + resturant.find(
            'a', {'class': 'biz-name'})['href']
        extracted[name] = address

    return extracted, len(extracted) > 0


def get_review(address, tor=False):
    """get yelp review from web page."""
    if tor:
        soup = BeautifulSoup(get(address).text)
    else:
        soup = BeautifulSoup(urlopen(address).read(), 'html.parser')
    try:
        review = soup('script', {'type': "application/ld+json"})
        for tag in soup.find_all('meta'):
            try:
                if tag.attrs['name'] == 'yelp-biz-id':
                    biz_id = tag.attrs['content']
                    return biz_id, review
            except:
                pass
    except:
        print("failed to get reviews")
        return '', []


def get_attribute(address, tor=False):
    """get resturant parameters."""
    try:
        if tor:
            soup = BeautifulSoup(get(address).text)
        else:
            soup = BeautifulSoup(urlopen(address).read(), 'html.parser')
    except:
        print('get_attribute failed')
    my_dict = {}

    try:
        review_count = soup.find('span',
                                 {'itemprop': 'reviewCount'}).get_text()
        rating_value = soup.find('meta', {'itemprop':
                                          'ratingValue'}).attrs['content']
    except:
        review_count = ''
        rating_value = ''
    try:
        zipcode = soup.find('span', {'itemprop': 'postalCode'}).get_text()
    except:
        zipcode = ''
    my_dict['ratingValue'] = rating_value
    my_dict['ratingCount'] = review_count
    my_dict['zipcode'] = zipcode
    for tag in soup.find_all('script'):
        if tag.find(string=re.compile("longitude")):
            text = tag.contents[0].splitlines()[-3].strip()
            text = text[text.find('{') + 1:-3]
            for word in text.split(','):
                if len(word) == 1:
                    my_dict['state'] = word
                if len(word.split(':')) == 2:

                    key, value = word.replace("\"", "").split(':')
                    my_dict[key] = value
    return my_dict


def get_zipcode():
    """read zipcodes from file."""
    with open('./data/zipcodes.csv', 'r+') as file:
        zipcodes = [
            (zipcode.strip()) for zipcode in file.read().split('\n')
            if zipcode.strip()
        ]
    return zipcodes


def get_scraped_biz(zipcode):
    "get the biz_id and resturant names that are already scrape"
    try:
        files = os.listdir('./data/')
    except:
        print('No scraped resturants')
        return [], []
    attr_files = [
        file for file in files if str(zipcode) + '_attributes' in file
    ]
    biz_id = np.array([])
    biz_name = np.array([])
    for file in attr_files:
        dat = pd.read_csv('./data/' + file)
        biz_id = np.append(biz_id, dat[' biz_id'].values)
        biz_name = np.append(biz_name, dat[' biz_name'].values)
    biz_name = map(unicode, list(biz_name))
    biz_id = map(unicode, list(biz_id))
    biz_name = [name.lstrip() for name in biz_name]
    biz_id = [id.lstrip() for id in biz_id]
    return biz_name, biz_id


def crawl(zipcodes=None, tor=False, sleep_time=10, start_page=0):
    """crawl through li.st of zipcodes."""
    if tor:
        ip_address = get_current_ip()
        set_new_ip()
        used_ips = deque()
        used_ips.append(get_current_ip())
    else:
        ip_address = urlopen('https://icanhazip.com/').read().replace('\n', '')
    request_count = 0
    flag = True
    header_flag = True
    zipcodes = [zipcodes] if zipcodes else get_zipcode()
    for zipcode in zipcodes:
        page = start_page
        request_count = 0
        flag = True
        out_of_zipcode_resturant = 0
        biz_names, biz_ids = get_scraped_biz(zipcode)
        answer = raw_input('Next zipcode? (y/n)')
        if answer == 'y':
            pass
        elif answer == 'n':
            break
        else:
            break
        while flag:
            if page > 500:
                break
            request_count += 1
            print('page {}, at zipcode {}'.format(page, zipcode))
            resturants, flag = get_resturants(zipcode, page, tor)
           # import pdb; pdb.set_trace()
            for resturant in resturants:
                if resturant in biz_names:
                    print('repeated biz_name: ', resturant)
                    continue
                if request_count % 50 == 0 and tor:
                    ensure_new_ip(used_ips)
                    request_count = 0
                    print('reached 50 requests, change ip address')
                if request_count % 50 == 0 and not tor:
                    print('reached 50 request, going to sleep {} minutes'.
                          format(sleep_time))
                    time.sleep(60 * sleep_time)
                    request_count = 0
                request_count += 1
                biz_id, review = get_review(resturants[resturant], tor)
                if biz_id in biz_ids:
                    print('repeated biz_id:', resturant)
                    continue
                request_count += 1
                attr_dict = get_attribute(resturants[resturant], tor)
                if attr_dict['zipcode'] and \
                        attr_dict['zipcode'] != zipcode:
                    out_of_zipcode_resturant += 1
                    continue
                print('scraping returant:' + resturant + ', at zipcode:' +
                      attr_dict[
                          'zipcode'] + ', current IP address:' + ip_address)
                biz_ids.append(biz_id)
                with open('./data/' + str(zipcode) + '_attributes.csv',
                          'a') as file:
                    if header_flag:
                        file.write(','.join(list(attr_dict.keys())) + '\n')
                        header_flag = False
                    file.write(','.join(list(attr_dict.values())) + '\n')
                reviews = review.pop()
                reviews = reviews.get_text().split("\"description\"")
                for review in reviews[1:]:
                    try:
                        words = review.split("\"author\"")[0].\
                            replace("\\n", '').lower()
                        words = re.sub("[^a-zA-Z]", " ", words).split(" ")
                        words = [word for word in words if len(word) > 1]
                        if biz_id == '':
                            words.insert(0, resturant)
                        else:
                            words.insert(0, biz_id)
                        words.append('\n')
                        words = ','.join(words)
                    except:
                        print('skipped ' + resturant)
                    with open('./data/' + str(zipcode) + '_reviews.csv',
                              'a') as file:
                        file.write(words)

            page += 10
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extracts all yelp restaurant \
    data from a specified zip code (or all American zip codes if nothing \
    is provided)')
    parser.add_argument(
        '-z',
        '--zipcode',
        nargs='+',
        type=int,
        help='Enter a zip code \
    you\'t like to extract from.')
    parser.add_argument(
        '-t',
        '--tor',
        action='store_true',
        help='use tor to change ip address')
    args = parser.parse_args()
    crawl(zipcodes=args.zipcode, tor=args.tor, sleep_time=10)
