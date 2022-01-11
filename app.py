from flask import Flask, render_template, jsonify, request, redirect, url_for

app = Flask(__name__)
import jwt
import datetime
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import requests

from pymongo import MongoClient

# Ubuntu 환경의 경우
# client = MongoClient('mongodb://test:test@localhost', 27017)
client = MongoClient('13.209.87.246', 27017, username="test", password="test")
db = client.dbsparta

SECRET_KEY = 'JEJU'


## HTML을 주는 부분
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template('index.html', user_info=user_info)
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
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,
        "password": password_hash,
        "nickname": nickname_receive,
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
def main():
    # DB에서 저장된 카페 목록 찾아서 HTML에 나타내기
    cafe_area = request.args.get('area')
    # area값이 포함되어 접근했을 경우
    if cafe_area in ["제주시", "서귀포시", "성산읍", "애월읍"]:
        cafe_lists = list(db.jejucafedb.find({"cafe_area":cafe_area}, {"_id": False}))
    elif cafe_area == "지역전체":
        cafe_lists = list(db.jejucafedb.find({}, {"_id": False}))
    # 전체 페이지 조회로 접근했을 경우
    else:
        cafe_lists = list(db.jejucafedb.find({}, {"_id": False}))
    return render_template("main-page.html", cafe_lists=cafe_lists)


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
