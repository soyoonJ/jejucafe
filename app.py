from flask import Flask, render_template, jsonify, request, redirect, url_for

app = Flask(__name__)
import jwt
import datetime
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import requests
import re

from pymongo import MongoClient

# Ubuntu 환경의 경우
# client = MongoClient('mongodb://test:test@localhost', 27017)
client = MongoClient('13.209.87.246', 27017, username="test", password="test")
db = client.dbsparta

SECRET_KEY = 'JEJU'

# 첫 페이지 HTML 렌더링 및 로그인 확인
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        # 로그인된 jwt 토큰을 받아 디코드하여 payload 저장
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        # payload 내 ID 정보로 user_info 저장
        user_info = db.users.find_one({"username": payload["id"]})

        # db 내 전체 cafe_list 불러오기
        cafe_lists = list(db.jejucafedb.find({}, {"_id": False}))

        # index.html 렌더링 및 user_info, cafe_lists 웹으로 전달달
        return render_template('index.html', user_info=user_info, cafe_lists=cafe_lists)

    # jwt 토큰 유효기간 만료 시 msg 전달 및 login.html 페이지로 이동
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    # jwt 토큰 decode Error 발생 시 (로그인 정보가 없을때) msg 전달 및 login.html 페이지로 이동
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# 로그인 페이지 HTML 렌더링
@app.route('/login')
def login():
    return render_template('login.html')


# 로그인 API
@app.route('/api/login', methods=['POST'])
def sign_in():
    # username, password 값 받아오기
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    # 받아온 password 값을 hashlib 모듈 이용하여 sha256 문자열 방식으로 해싱하여 16진수로 변환
    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()

    # username , 해싱된 pw 값 대조
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    # result 값 있을때
    if result is not None:
        # payload 내 id, 유효기간 지정
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }
        # 상기 payload 사용하여 jwt 인코딩
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        # token 으로 html로 전송
        return jsonify({'result': 'success', 'token': token})
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


# 회원가입 API
@app.route('/api/signup', methods=['POST'])
def sign_up():
    # username, password, nickname 값 받아오기
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    nickname_receive = request.form['nickname_give']

    # 받아온 password 값을 hashlib 모듈 이용하여 sha256 문자열 방식으로 해싱하여 16진수로 변환
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()

    # db 상 username, password, nickname, like(찜 기능) 항목으로 저장
    doc = {
        "username": username_receive,
        "password": password_hash,
        "nickname": nickname_receive,
        "like": []
    }

    db.users.insert_one(doc)

    return jsonify({'result': 'success'})


# ID 중복확인 API
@app.route('/api/check_id', methods=['POST'])
def check_id():
    # username 받아오기
    username_receive = request.form['username_give']

    # 받아온 username 이 db상 있는지 확인.
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


# 닉네임 중복확인 API
@app.route('/api/check_nickname', methods=['POST'])
def check_nickname():
    # nickname 받아오기
    nickname_receive = request.form['nickname_give']

    # 받아온 nickname 이 db상 있는지 확인.
    exists = bool(db.users.find_one({"nickname": nickname_receive}))

    return jsonify({'result': 'success', 'exists': exists})


@app.route('/api/posts/', methods=['GET'])
def show_cafe_lists():
    # DB에서 저장된 카페 목록 찾아서 HTML에 나타내기
    cafe_area = request.args.get('area')
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        # area 값이 포함되어 접근했을 경우
        if cafe_area in ["제주시", "서귀포시", "성산읍", "애월읍"]:
            cafe_lists = list(db.jejucafedb.find({"cafe_area": cafe_area}, {"_id": False}))
        else:
            cafe_lists = list(db.jejucafedb.find({}, {"_id": False}))
        return render_template('index.html', user_info=user_info, cafe_lists=cafe_lists)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/api/mycafe/', methods=['GET'])
def show_mycafe_lists():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        # user_info 내 'like' 는 찜한 카페 이름 list로, 내부 값으로 '카페 이름' 만 가지고 있음
        cafe_name_lists = user_info['like']

        cafe_lists = list()
        # user_info['like']에 저장된 사용자별 찜한 가게 숫자만큼, for 문을 돌며 query 실행됨. -> 성능 저하 발생 가능성
        for cafe_name in cafe_name_lists:
            # cafe_name 변수를 사용해 jejucafedb 내에 있는 카페 정보들을 dictionary 형태로 받아와 cafe_info에 저장
            cafe_info = db.jejucafedb.find_one({'cafe_name': cafe_name})
            # 각 dictionary 를 cafe_lists 에 저장.
            cafe_lists.append(cafe_info)
        return render_template('index.html', user_info=user_info, cafe_lists=cafe_lists)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# # 상단의 show_mycafe_lists() 와 다른 점은, 상단은 찜한 갯수 만큼 for문을 돌며
# # find_one query 를 실행해야 하기때문에 찜한 갯수가 많아질 수록 query를 실행해야 횟수가 많아지므로,
# # 만약 사용자가 수천개의 찜한 목록을 가지고 있을 경우 DB쪽에서 성능저하가 발생할 수 있음.
# # 찜한 목록이 10개라면 상단의 구현 방식은 총 11번의 query가 발생하지만 (user 정보, 카페 이름으로 일치하는 카페 정보 찾아오기)
# # 이 방식은 총 2번의 query로 해결할 수 있음. 상세 내용은 주석 참조.
#
# @app.route('/api/mycafe/', methods=['GET'])
# def show_mycafe_lists():
#     token_receive = request.cookies.get('mytoken')
#     try:
#         # 현재 로그인한 사용자의 jwt 토큰을 decode 하여 payload 에 저장
#         payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
#
#         # payload를 사용해 일치하는 유저의 정보를 user_info에 저장
#         user_info = db.users.find_one({"username": payload["id"]})
#
#         # pipeline .. 사용자가 읽기 힘든 긴 내용의 query문을 pipeline 이라는 string에 미리 저장.
#         # $unwind .. $like 에 있는 리스트 내용을 기준으로 하나의 도큐먼트를 복제.
#         # $like = ['카페 도두', '방듸', '망고봉봉'] 리스트형 자료
#         # 예) db.users.find_one({"username": 'shjin'})
#         # 출력 -> {'username': 'shjin', 'password': '...', 'nickname': '상혁', 'like': ['카페 도두', '방듸', '망고봉봉']}
#         # db.users.aggregate([{"$unwind":"$like"},{"$match":{"username": 'shjin'}})
#         # 출력 -> {'username': 'shjin', 'password': '...', 'nickname': '상혁', 'like': '카페 도두'}
#                 # {'username': 'shjin', 'password': '...', 'nickname': '상혁', 'like': '방듸'}
#                 # {'username': 'shjin', 'password': '...', 'nickname': '상혁', 'like': '망고봉봉'}
#
#         # $lookup .. "from" 으로 선택한 collection 과 묶어줘
#         # "from" : %Collection_이름% .. 현재 query를 수행한 collection(이 예제에서는 users) 과 묶을 다른 collection 을 지정.
#         # "localField" : %field명% .. users 내에 있는 필드명을 지정
#         # "foreignField" : %field명% .. "from".. 에서 지정한 collection(이 예제에서는 jejucafedb) 내에 있는 필드명을 지정
#         # "as": %field명% .. 새로 생성할 field의 이름을 지정.
#         # "match": %입력값% .. 입력값에 해당하는 도큐먼트만 가져올게.
#
#         pipeline = [{"$unwind": "$like"}, {
#             "$lookup": {
#                         "from": "jejucafedb",
#                         "localField": "like",
#                         "foreignField": "cafe_name",
#                         "as": "like_cafe_list"}},
#                     {"$match":
#                          {'username': user_info['username']}}]
#         # cafe_like_list 값에는 users 내에 like 리스트 내 도큐먼트가 개별적으로 분리되고, like_cafe_list 라는 카페 정보가 담긴 list 형 자료가 포함됨.
#         cafe_like_list = list(db.users.aggregate(pipeline))
#         # like_number .. 사용자가 찜한 갯수
#         like_number = 0
#         # index.html에게 카페 목록을 넘겨주기 위해 별도로 list형 자료로 선언
#         cafe_lists = list()
#         for cafe_like in cafe_like_list:
#             # cafe_lists 리스트형 자료에 cafe_like_list[like_number]['like_cafe_list'][0] 의 dictionary 를 하나씩 추가
#             cafe_lists.append(cafe_like_list[like_number]['like_cafe_list'][0])
#             # 다음 리스트 항목으로 이동하기 위해 다음 찜한 항목으로 이동
#             like_number = like_number + 1
#         # shjin 유저가 찜한 목록의 카페 정보를 모두 담은 cafe_lists 를 메인페이지 표기를 위해 index.html로 전달
#         return render_template('index.html', user_info=user_info, cafe_lists=cafe_lists)
#     except jwt.ExpiredSignatureError:
#         return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
#     except jwt.exceptions.DecodeError:
#         return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# 검색 버튼 눌렀을 시 수행. cafe_name이 정확히 일치하는 값만 검색 가능함.
@app.route('/api/search', methods=['GET'])
def search_cafe_list():
    cafe_name = request.args.get('cafe_name')
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        # cafe_name 과 정확히 일치하는 하나의 카페 정보만 전달. dictionary 형태로 cafe_info에 저장
        cafe_info = db.jejucafedb.find_one({"cafe_name": cafe_name}, {"_id": False})
        cafe_lists = list()
        # 정확히 검색하여 검색된 값이 있는 경우
        if cafe_info is not None:
            # cafe_lists 를 list() 형태로 미리 선언 후 위에서 구한 cafe_info dictionary 값을 append로 추가
            cafe_lists.append(cafe_info)
        return render_template('index.html', user_info=user_info, cafe_lists=cafe_lists)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))
#
#
# @app.route('/api/search', methods=['GET'])
# def search_cafe_list():
#     # DB에서 저장된 카페 목록 찾아서 HTML에 나타내기
#     raw_cafe_name = request.args.get('cafe_name')
#     cafe_name = "/" + raw_cafe_name + "/"
#
#
#     token_receive = request.cookies.get('mytoken')
#     try:
#         payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
#         user_info = db.users.find_one({"username": payload["id"]})
#
#         # LIKE 검색을 위해 정규식 표현 사용. "카페" 가 포함된 모든 단어 검색.
#         # 예) '카페' 검색 시, "카페 도두", "무인카페 산책", "비밀의숲 카페" 모두 검색됨.
#         # MongoDB : db.jejucafedb.find({"cafe_name" : /cafe_name/})
#         # RDBMS 형식 : SELECT * FROM jejucafedb WHERE name LIKE %cafe_name% 검색과 동일
#         # 참고1 ) https://stackoverflow.com/questions/3305561/how-to-query-mongodb-with-like
#         # 참고2 ) https://stackoverflow.com/questions/19867389/pymongo-in-regex
#         # re.compile('.*') = '/'
#
#         cafe_lists = list(db.jejucafedb.find({"cafe_name": re.compile('.*' + cafe_name + '.*')}, {"_id": False}))
#
#         return render_template('index.html', user_info=user_info, cafe_lists=cafe_lists)
#     except jwt.ExpiredSignatureError:
#         return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
#     except jwt.exceptions.DecodeError:
#         return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# 모달 개별화 시도하고자 작성했던 코드
# @app.route('/api/open', methods=['GET'])
# def show_stars():
#     cafe = list(db.jejucafedb.find({}, {'_id': False}))
#     return jsonify({'all_cafe': cafe})


#
@app.route('/api/comment', methods=['POST'])
def write_review():
    # 작성한 코멘트 저장하기 위해 index.html에서 '_give' 변수로 받아와서 doc 생성 후 db에 추가
    cafe_name_receive = request.form['cafe_name_give']
    nickname_receive = request.form['nickname_give']
    score_receive = request.form['score_give']
    comment_receive = request.form['comment_give']


    # DB에 삽입할 review 만들기
    doc = {
        'cafe': cafe_name_receive,
        'nickname': nickname_receive,
        'score': score_receive,
        'comment': comment_receive
    }

    # reviews에 review 저장하기
    db.jejucafedbcomment.insert_one(doc)
    # 성공 여부 & 성공 메시지 반환
    return jsonify({'msg': '코멘트 작성 완료!'})


@app.route('/api/read', methods=['GET'])
def listing():
    # Modal 에서 코멘트 조회를 위해 showComments(cafe_name)으로 접근하고,
    # /api/read?cafe_name=카페이름 형태로 AJAX get 요청하면 ?cafe_name= 이하의 값을 request.args.get(...)으로 가져옴
    cafe_name_receive = request.args.get('cafe_name')
    replies = list(db.jejucafedbcomment.find({"cafe": cafe_name_receive}, {'_id': False}))

    return jsonify({'all_replies':replies})



@app.route('/api/like', methods=['POST'])
def like():
    cafe_name_receive = request.form['cafe_name_give']
    user_name_receive = request.form['user_name_give']

    # 찜해둔 카페 리스트 받아오기
    likes = db.users.find_one({"username": user_name_receive}, {"_id": False})["like"]

    # 목록 안에 받아온 카페가 있을때
    if cafe_name_receive in likes:
        db.users.update_one(
            {"username": user_name_receive}, {"$pull": {"like": cafe_name_receive}}
        )
        return jsonify({"msg": "찜 해제 완료"})
   # 목록안에 받아온 카페가 없을때
    else:
        db.users.update_one(
            {"username": user_name_receive}, {"$push": {"like": cafe_name_receive}}
        )
        return jsonify({"msg": "찜하기 완료"})


@app.route('/api/create', methods=['POST'])
def Add_newcafe():
    # 클라이언트로 부터 받은 내용 변수에 저장
    cafename_receive = request.form['CafeName_give']
    cafearea_receive = request.form['CafeArea_give']
    cafeaddress_receive = request.form['CafeAddress_give']
    cafeimgurl_receive = request.form['CafeImgurl_give']
    # Doc 생성
    doc = {
        "cafe_name": cafename_receive,
        "cafe_area": cafearea_receive,
        "cafe_address": cafeaddress_receive,
        "cafe_thumbnail_url": cafeimgurl_receive
    }
    #jejucafedb에 추가.
    db.jejucafedb.insert_one(doc)
    return jsonify({'result': 'success', 'msg': '카페가 추가되었습니다.'})



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
