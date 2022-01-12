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
app.secret_key = "JEJU"

## HTML을 주는 부분
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        cafe_lists = list(db.jejucafedb.find({}, {"_id": False}))
        return render_template('index.html', user_info=user_info, cafe_lists=cafe_lists)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)


@app.route('/api/login', methods=['POST'])
def sign_in():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


@app.route('/api/signup', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    nickname_receive = request.form['nickname_give']
    like = []
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,
        "password": password_hash,
        "nickname": nickname_receive,
        "like": like
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


@app.route('/api/check_id', methods=['POST'])
def check_id():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    # print(value_receive, type_receive, exists)
    return jsonify({'result': 'success', 'exists': exists})


@app.route('/api/check_nickname', methods=['POST'])
def check_nickname():
    nickname_receive = request.form['nickname_give']
    exists = bool(db.users.find_one({"nickname": nickname_receive}))
    # print(value_receive, type_receive, exists)
    return jsonify({'result': 'success', 'exists': exists})


@app.route('/api/posts/', methods=['GET'])
def show_cafe_lists():
    # DB에서 저장된 카페 목록 찾아서 HTML에 나타내기
    cafe_area = request.args.get('area')
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        # area값이 포함되어 접근했을 경우
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
        pipeline = [{"$unwind": "$like"}, {
            "$lookup": {"from": "jejucafedb", "localField": "like", "foreignField": "cafe_name",
                        "as": "like_cafe_list"}},
                    {"$match": {'username': user_info['username']}}]
        cafe_like_list = list(db.users.aggregate(pipeline))
        like_number = 0
        cafe_lists = list()
        for cafe_like in cafe_like_list:
            cafe_lists.append(cafe_like_list[like_number]['like_cafe_list'][0])
            like_number = like_number + 1
        return render_template('index.html', user_info=user_info, cafe_lists=cafe_lists)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/api/search', methods=['GET'])
def search_cafe_list():
    # DB에서 저장된 카페 목록 찾아서 HTML에 나타내기
    cafe_name = request.args.get('cafe_name')
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})

        # LIKE 검색을 위해 정규식 표현 사용. "카페" 가 포함된 모든 단어 검색.
        # 예) '카페' 검색 시, "카페 도두", "무인카페 산책", "비밀의숲 카페" 모두 검색됨.
        # MongoDB : db.jejucafedb.find({"cafe_name" : /cafe_name/})
        # RDBMS 형식 : SELECT * FROM jejucafedb WHERE name LIKE %cafe_name% 검색과 동일
        # 참고1 ) https://stackoverflow.com/questions/3305561/how-to-query-mongodb-with-like
        # 참고2 ) https://stackoverflow.com/questions/19867389/pymongo-in-regex

        cafe_lists = list(db.jejucafedb.find({"cafe_name": re.compile('.*' + cafe_name + '.*')}, {"_id": False}))

        return render_template('index.html', user_info=user_info, cafe_lists=cafe_lists)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


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
    cafename_receive = request.form['CafeName_give']
    cafearea_receive = request.form['CafeArea_give']
    cafeaddress_receive = request.form['CafeAddress_give']
    cafeimgurl_receive = request.form['CafeImgurl_give']

    doc = {
        "cafe_name": cafename_receive,
        "cafe_area": cafearea_receive,
        "cafe_address": cafeaddress_receive,
        "cafe_thumbnail_url": cafeimgurl_receive
    }

    db.jejucafedb.insert_one(doc)
    return jsonify({'result': 'success', 'msg': '카페가 추가되었습니다.'})



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
