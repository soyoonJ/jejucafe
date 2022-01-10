import time
import random
from pymongo import MongoClient
from pyvirtualdisplay import Display
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
# import config


# 윈도우의 경우
client = MongoClient('localhost', 27017)

# Ubuntu의 경우
# client = MongoClient('mongodb://test:test@localhost', 27017)

db = client.dbsparta
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}

# 제주 카페 목록. Default
jeju_cafe_list = "https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd&pageSize=15&sortListType=reviewcnt&viewType=thumb"

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument("--single-process")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36")
# path = '/home/ubuntu/myoculusproject/driver/chromedriver'
path = './driver/chromedriver.exe'
driver = webdriver.Chrome(path, chrome_options=chrome_options)

jeju_cafe_lists = list()
jeju_cafe_lists = ['https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region1%3E11&pageSize=15&sortListType=reviewcnt&viewType=thumb', 'https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region2%3E21&pageSize=15&sortListType=reviewcnt&viewType=thumb', 'https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region2%3E17&pageSize=15&sortListType=reviewcnt&viewType=thumb', 'https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region1%3E12&pageSize=15&sortListType=reviewcnt&viewType=thumb']

for jeju_cafe_list in jeju_cafe_lists:
    if jeju_cafe_list == 'https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region1%3E11&pageSize=15&sortListType=reviewcnt&viewType=thumb':
        cafe_area = '제주시'
    elif jeju_cafe_list == 'https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region2%3E21&pageSize=15&sortListType=reviewcnt&viewType=thumb':
        cafe_area = '서귀포시'
    elif jeju_cafe_list == 'https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region2%3E17&pageSize=15&sortListType=reviewcnt&viewType=thumb':
        cafe_area = '성산읍'
    else:
        cafe_area = '애월읍'

    driver.get(jeju_cafe_list)
    # time.sleep(random.uniform(15, 20))
    time.sleep(random.uniform(15, 20))

    cafe_list_html = driver.page_source
    cafe_list_soup = BeautifulSoup(cafe_list_html, 'html.parser')

    cafe_list = list()
    cafe_common_url = 'https://www.visitjeju.net'

    for i in range(1, 16, 1):
        cafe_url = cafe_list_soup.select_one('#content > div > div.cont_wrap > div.recommend_area > ul > li:nth-child(' + str(i) + ') > dl > dt > a')['href']
        cafe_list.append(cafe_common_url + cafe_url)

    for link in cafe_list:
        driver.get(link)
        time.sleep(random.uniform(15, 20))
        cafe_html = driver.page_source
        cafe_soup = BeautifulSoup(cafe_html, 'html.parser')
        cafe_raw_url = cafe_soup.select_one('#content > div > div.sub_visual_wrap')
        if cafe_raw_url is not None:
            # 제주시 > 망고홀릭 제주본점 항목에 style, 제목값이 없어서 예외 처리 시도
            try:
                cafe_modified_url = cafe_raw_url['style']
                cafe_thumbnail_url = cafe_modified_url.split('background: url("')[1].split('")')[0]
                # print(cafe_thumbnail_url)
            except KeyError:
                cafe_thumbnail_url = "NoThumbnailUrl"
        cafe_raw_name = cafe_soup.select_one('#content > div > div.sub_visual_wrap > div.inner_wrap > div.sub_info_area > div.sub_info_title > h3')
        if cafe_raw_name is not None:
            cafe_name = cafe_raw_name.string.splitlines()[0]
        cafe_raw_address = cafe_soup.select_one('#content > div > div.sub_visual_wrap > div.inner_wrap > div.sub_info_area > div.basic_information > div:nth-child(2) > p.info_sub_cont')
        if cafe_raw_address is not None:
            cafe_address = cafe_raw_address.string

        # if cafe_name is not None:
        if cafe_thumbnail_url != "NoThumbnailUrl":
            print('카페 이름: ', cafe_name)
            print('카페 주소: ', cafe_address)
            print('카페 지역: ', cafe_area)
            print('카페 썸네일 주소: ', cafe_thumbnail_url)

            # 이미 카페 이름이 등록된 경우
            if db.jejucafedb.find_one({'cafe_name': cafe_name}) is not None:
                time.sleep(5)
                db.jejucafedb.update_many({'cafe_name': cafe_name},
                                              {'$set': {'cafe_address': cafe_address,
                                                        'cafe_thumbnail_url': cafe_thumbnail_url
                                                        }})
            # 카페 이름이 Database 내에 없고, 최초 등록 시
            else:
                cafe_info = {
                    'cafe_name': cafe_name,
                    'cafe_address': cafe_address,
                    'cafe_area': cafe_area,
                    'cafe_thumbnail_url': cafe_thumbnail_url,
                    'star_rate': 0,
                    'favorite_count': 0
                }
                db.jejucafedb.insert_one(cafe_info)

print("모든 URL 내용 확인 완료")
driver.close()
driver.quit()
        
