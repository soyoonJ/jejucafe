import time
import random
from pymongo import MongoClient
# from pyvirtualdisplay import Display
from bs4 import BeautifulSoup
from selenium import webdriver
# from selenium.webdriver.chrome.service import Service

# 윈도우의 경우
# client = MongoClient('localhost', 27017)

# Ubuntu의 경우
client = MongoClient('mongodb://test:test@localhost', 27017)

db = client.dbsparta
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}

# EC2 내 Ubuntu 에서 수행 시 Display가 없는 형태로 실행하되, 일반 Chrome 브라우저 인 것처럼 접근하도록 위장.
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument("--single-process")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument(
    "User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36")
# Ubuntu 의 경우
path = '/home/ubuntu/jejucafe/driver/chromedriver'
# path = './driver/chromedriver.exe'
driver = webdriver.Chrome(path, chrome_options=chrome_options)

# 제주 구역 중 제주시, 서귀포시, 성산읍, 애월읍의 카페를 조회할 수 있는 URL을 문자열 list 형태로 저장.
# 한 페이지에 최대 15개의 카페 조회 가능.
jeju_cafe_lists = list()
jeju_cafe_lists = ['https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region1%3E11&pageSize=15&sortListType=reviewcnt&viewType=thumb','https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region2%3E21&pageSize=15&sortListType=reviewcnt&viewType=thumb','https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region2%3E17&pageSize=15&sortListType=reviewcnt&viewType=thumb','https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region1%3E12&pageSize=15&sortListType=reviewcnt&viewType=thumb']

for jeju_cafe_list in jeju_cafe_lists:
    if jeju_cafe_list == 'https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region1%3E11&pageSize=15&sortListType=reviewcnt&viewType=thumb':
        cafe_area = '제주시'
        cafe_id_area = 100000
    elif jeju_cafe_list == 'https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region2%3E21&pageSize=15&sortListType=reviewcnt&viewType=thumb':
        cafe_area = '서귀포시'
        cafe_id_area = 200000
    elif jeju_cafe_list == 'https://www.visitjeju.net/kr/detail/list?menuId=DOM_000001719008000000&cate1cd=cate0000000005&cate2cd=cate0000001272#p1&region2cd=region2%3E17&pageSize=15&sortListType=reviewcnt&viewType=thumb':
        cafe_area = '성산읍'
        cafe_id_area = 300000
    else:
        cafe_area = '애월읍'
        cafe_id_area = 400000

    driver.get(jeju_cafe_list)

    # 사이트 내용을 불러오는데 로딩되는 시간이 다소 걸려 15~20초 사이를 랜덤하게 대기.
    time.sleep(random.uniform(15, 20))
    cafe_list_html = driver.page_source
    cafe_list_soup = BeautifulSoup(cafe_list_html, 'html.parser')
    cafe_list = list()
    cafe_common_url = 'https://www.visitjeju.net'

    # for 문을 돌며 해당 지역의 카페 개별 항목의 URL을 리스트로 변환.
    for i in range(1, 16, 1):
        cafe_url = cafe_list_soup.select_one('#content > div > div.cont_wrap > div.recommend_area > ul > li:nth-child(' + str(i) + ') > dl > dt > a')['href']
        cafe_list.append(cafe_common_url + cafe_url)

    # 지역별 카페들의 정보를 조회하고 가공하여 데이터베이스에 저장.

    for link in cafe_list:
        cafe_id_num = random.randint(1, 99999)
        driver.get(link)
        time.sleep(random.uniform(15, 20))
        cafe_html = driver.page_source
        cafe_soup = BeautifulSoup(cafe_html, 'html.parser')
        cafe_raw_url = cafe_soup.select_one('#content > div > div.sub_visual_wrap')
        if cafe_raw_url is not None:
            # 제주시 > 망고홀릭 제주본점 과 같은 항목에 썸네일 URL 또는 제목이 없어 오류 발생 가능.
            try:
                cafe_modified_url = cafe_raw_url['style']
                cafe_thumbnail_url = cafe_modified_url.split('background: url("')[1].split('")')[0]
            except KeyError:
                # KeyError 가 발생하는 경우는 실제로 지역의 카페 항목 내에 썸네일 URL 또는 제목이 없는 경우.
                cafe_thumbnail_url = "NoThumbnailUrl"
        cafe_raw_name = cafe_soup.select_one(
            '#content > div > div.sub_visual_wrap > div.inner_wrap > div.sub_info_area > div.sub_info_title > h3')
        if cafe_raw_name is not None:
            cafe_name = cafe_raw_name.string.splitlines()[0]
        cafe_raw_address = cafe_soup.select_one('#content > div > div.sub_visual_wrap > div.inner_wrap > div.sub_info_area > div.basic_information > div:nth-child(2) > p.info_sub_cont')
        if cafe_raw_address is not None:
            cafe_address = cafe_raw_address.string

        cafe_id = cafe_id_area + cafe_id_num
        # 지역 내 카페 정보가 잘 들어있는 경우, 데이터베이스에 이름이 같은 경우 Update, 또는 Insert.
        if cafe_thumbnail_url != "NoThumbnailUrl":
            print('카페 ID: ', cafe_id)
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
                    'cafe_id': cafe_id,
                    'cafe_name': cafe_name,
                    'cafe_address': cafe_address,
                    'cafe_area': cafe_area,
                    'cafe_thumbnail_url': cafe_thumbnail_url,
                    'star_rate': 0,
                    'favorite_count': 0
                }
                db.jejucafedb.insert_one(cafe_info)

print("모든 URL 내용 확인 완료")

# 스크래핑에 사용하였던 Chromedriver를 사용 종료
driver.close()
driver.quit()

