from bson.objectid import ObjectId
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import requests
import bcrypt
from datetime import timedelta, datetime
import jwt
import xml.etree.ElementTree as ET

client = MongoClient('mongodb+srv://test:sparta@cluster0.tm0bxlm.mongodb.net/?retryWrites=true&w=majority')
db = client.dbsparta

app = Flask(__name__)
API_KEY = "AoGOZl9nF3tclj3GG7ldBlDpomSBaQOyxi7GWPkSlgbjBoOD0ur23TRX2haHdaHC8Np7vRjEAcCW0g0PBPMRGQ%3D%3D"
SECRET_KEY = "DFLSJFKL3r8343dsfjl!!"

@app.route('/')
def home():
    return render_template('index.html')


# db에서 자유게시판의 데이터를 가져와 intro에 전달.
@app.route('/intro/')
def intro():
    token_receive = request

    all_items = list(db.items.find())
    return render_template('intro.html', items=all_items)


# tour API에서 전달받은 데이터를 intro페이지에 전송해준다.
@app.route('/intro/<contentTypeId>')
def apiIntro(contentTypeId):
    # 프론트단에서 전달 받은 contentTypeId(카테고리 분류 번호)와 API키를 넣어 tourAPI에 request를 보낸다. 
    # reponse값이 xml방식 이므로 xml.etree.ElementTree 라이브러리를 이용해 파싱 해준다.
    response = requests.get(f"http://apis.data.go.kr/B551011/KorService/areaBasedList?numOfRows=12&pageNo=1&MobileOS=ETC&MobileApp=AppTest&ServiceKey={API_KEY}&listYN=Y&arrange=A&contentTypeId={contentTypeId}&areaCode=1&sigunguCode=3&cat1=&cat2=&cat3=")
    tree = ET.fromstring(response.content)
    tree_items = tree[1][0]
    # ET.dump() << xml방식의 데이터를 string으로 표시해주는 함수

    all_items = []
    
    # 필요한 데이터를 반복문을 이용해 추출 후 all_items List에 넣어준다.
    for i in range(len(tree[1][0])):
        title = tree_items[i].find("title").text
        img = tree_items[i].find("firstimage").text
        contentid = tree_items[i].find("contentid").text

        # 사진이 없을 경우 대체 이미지 삽입
        if not img:
            img = "https://artsmidnorthcoast.com/wp-content/uploads/2014/05/no-image-available-icon-6.png"

        doc = {"title":title, "img":img, "_id":contentid}
        all_items.append(doc)
        
    return render_template('intro.html', items=all_items)


@app.route('/api/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give'] 

    # ID(유저)가 존재하는지 확인
    user = db.users.find_one({'id':id_receive})

    if user is None:    
    ## 유저가 없을시 회원가입 후 로그인
        pw_hash = bcrypt.hashpw(pw_receive.encode('utf-8'), bcrypt.gensalt()) # bycrypt 라이브러리를 이용해 패스워드 암호화
        pw_decode = pw_hash.decode('utf-8') # db에는 utf-8 형식의 데이터가 저장되지 않기 때문에 저장전에 decode한다.
        db.users.insert_one({'id': id_receive, 'pw': pw_decode})
        db_pw = pw_decode
    else:
        db_pw = user['pw'] # db에 저장돼있는 패스워드
        
    doc = login(id_receive, pw_receive, db_pw)
    return jsonify(doc)

@app.route('/api/tokenCheck', methods=['POST'])
def token_check():
    token_receive = request.form['token_give']
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms='HS256')
        user = db.user.find_one({"id":payload['id']})
        return jsonify({'result':'success'})
    except jwt.ExpiredSignatureError:
        return jsonify({'result':'fail', 'msg':'로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result':'fail', 'msg':'로그인 정보가 존재하지 않습니다.'})


def login(id_receive, pw_receive, db_pw):
    # bcrypt라이브러리의 패스워드 체크 함수를 사용해 입력받은 패스워드와 db에 저장돼있는 패스워드를 비교한다.
    if bcrypt.checkpw(pw_receive.encode('utf-8'), db_pw.encode('utf-8')):
        payload = {
            'id': id_receive,
            'exp': datetime.utcnow() + timedelta(days=1) # days(1)일후 날짜를 반환한다. 토큰의 유효시간
        }           
        # 필요한 정보들을 모아 jwt로 인코딩 한다.
        # SECRET_KEY = 임의로 지정한 string값
        # algoriithm = HS256 서명 알고리즘을 사용해 암호화
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256') 
        doc = {'result':'success', 'token':token}
        return doc
    else:
        doc = {'result':'fail', 'msg':'패스워드를 확인해주세요!'}
        return doc

##----------------

@app.route('/detail/<typeId>/')
def detail(typeId):
             
    return render_template('detail.html')


@app.route('/api/detail')
def apiDetail():
    contentId = request.args.get('contentId')
    item = db.items.find_one({'_id':ObjectId(contentId)})

    doc = {
        "title":item['title'],
        "desc":item['desc'],
        "link":item['link'],
        "img":item['img']
    }
    return jsonify(doc)



@app.route("/gangbuk", methods=["POST"])
def gangbuk_post():
    name_receive = request.form['name_give']
    comment_receive = request.form['comment_give']

    doc = {
        'name': name_receive,
        'comment': comment_receive
    }

    db.gangbuk.insert_one(doc)

    return jsonify({'msg':'후기 작성완료!'})

@app.route("/gangbuk", methods=["GET"])
def gangbuk_get():
    comment_list = list(db.gangbuk.find({}, {'_id': False}))
    return jsonify({'comments':comment_list})



##-------------------

@app.route('/write')
def write():
    return render_template('write.html')


@app.route("/api/write", methods=["POST"])
def write_post():
    title_receive = request.form['title_give']
    desc_receive = request.form['desc_give']
    link_receive = request.form['link_give']
    img_receive = request.form['img_give']

    doc = {
        'title': title_receive,
        'desc': desc_receive,
        'link': link_receive,
        'img': img_receive
        }

    db.items.insert_one(doc)

    return jsonify({'msg': '저장 완료!'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=4000, debug=True)
