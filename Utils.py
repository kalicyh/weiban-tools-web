import asyncio
import datetime
import json
import os
from PIL import Image
import random
import requests
import time

# From https://github.com/JefferyHcool/weibanbot/blob/main/enco.py
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad
import base64

DEFAULT_SCHOOL_NAME = '浙江财经大学东方学院'
'''这个常量的作用是暂存学校名，当同时输入的多个帐号来自同一个学校，用此避免重复地输入学校名'''

class main:
    headers = { 'x-token': "",
                "User-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Mobile Safari/537.36 Edg/103.0.1264.77"
            }

    def __init__(self, code, id, token, realName):
        self.tenantCode = code
        self.userId = id
        self.x_token = token
        self.realName = realName
        self.userProjectId = []
        self.taskName = []
        self.resourceNames = ['第0项']

    def init(self):
        self.headers['x-token'] = self.x_token

    # 以下俩个方法来自https://github.com/Sustech-yx/WeiBanCourseMaster

    # js里的时间戳似乎都是保留了三位小数的.
    def __get_timestamp(self):
        return str(round(datetime.datetime.now().timestamp(), 3))

    # Magic: 用于构造、拼接"完成学习任务"的url
    # js: (jQuery-3.2.1.min.js)
    # f = '3.4.1'
    # expando = 'jQuery' + (f + Math.random()).replace(/\D/g, "")
    def __gen_rand(self):
        return ("3.4.1" + str(random.random())).replace(".", "")

    def get_Project_Info(self):
        url = f'https://weiban.mycourse.cn/pharos/index/listMyProject.do?timestamp={time.time()}'
        data = {
            'tenantCode': self.tenantCode,
            'userId': self.userId,
            'ended': 2
        }
        response = requests.post(url, data=data, headers=self.headers)
        data = json.loads(response.text)['data']
        if len(data) <= 0:self.userProjectId = ''
        else:
            self.userProjectId = [i["userProjectId"] for i in data]
            self.taskName = [i["projectName"] for i in data]

    # def getRealName(self):
    #     url = f"https://weiban.mycourse.cn/pharos/my/getInfo.do?timestamp={int(time.time())}"
    #     data = {
    #         'tenantCode': self.tenantCode,
    #         'userId': self.userId
    #     }
    #     response = requests.post(url, data=data, headers=self.headers)
    #     text = response.text
    #     data = json.loads(text)
    #     return data['data']['realName']

    # def getTaskName(self):
    #     url = f"https://weiban.mycourse.cn/pharos/index/listStudyTask.do?timestamp={int(time.time())}"
    #     data = {
    #         'tenantCode': self.tenantCode,
    #         'userId': self.userId,
    #         'limit': 2
    #     }
    #     response = requests.post(url, data=data, headers=self.headers)
    #     text = response.text
    #     data = json.loads(text)
    #     for i in data['data']:
    #         if self.userProjectId in i['userProjectId']:taskName = i['projectName']
    #     return taskName

    # def getProgress(self):
    #     url = "https://weiban.mycourse.cn/pharos/project/showProgress.do"
    #     data = {
    #         'userProjectId': self.userProjectId,
    #         'tenantCode': self.tenantCode,
    #         'userId': self.userId
    #     }
    #     response = requests.post(url, data=data, headers=self.headers)
    #     text = response.text
    #     data = json.loads(text)
    #     return data['data']['progressPet']

    def getCategory(self, j, chooseType):
        url = "https://weiban.mycourse.cn/pharos/usercourse/listCategory.do"
        data = {
            'userProjectId': self.userProjectId[j],
            'tenantCode': self.tenantCode,
            'userId': self.userId,
            'chooseType': chooseType
        }
        response = requests.post(url, data=data, headers=self.headers)
        text = response.text
        data = json.loads(text)
        list = data['data']
        result = []
        for i in list:
            if i['totalNum'] > i['finishedNum']:
                result.append(i['categoryCode'])
        return result

    def getCourse(self, j, chooseType):
        url = "https://weiban.mycourse.cn/pharos/usercourse/listCourse.do"
        result = []
        for i in self.getCategory(j ,chooseType):
            data = {
                "userProjectId": self.userProjectId[j],
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "chooseType": chooseType,
                "name": "",
                "categoryCode": i,
            }
            response = requests.post(url, data=data, headers=self.headers)
            text = response.text
            data = json.loads(text)["data"]
            for i in data:
                if i["finished"] == 2:
                    result.append(i["resourceId"])
        return result

    def getFinishIdList(self, j, chooseType):
        url = "https://weiban.mycourse.cn/pharos/usercourse/listCourse.do"
        result = {}
        for i in self.getCategory(j, chooseType):
            data = {
                "userProjectId": self.userProjectId[j],
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "chooseType": chooseType,
                "categoryCode": i,
            }
            response = requests.post(url, data=data, headers=self.headers)
            text = response.text
            data = json.loads(text)["data"]
            for i in data:
                if i["finished"] == 2:
                    if "userCourseId" in i:
                        result[i["resourceId"]] = i["userCourseId"]
                        # print(i['resourceName'])
                        self.resourceNames.append(i['resourceName'])
                        self.tempUserCourseId = i["userCourseId"]
                    else:
                        result[i["resourceId"]] = self.tempUserCourseId
        return result


    async def start(self, i, courseId):
        data = {
            "userProjectId": self.userProjectId[i],
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "courseId": courseId,
        }
        headers = {"x-token": self.x_token}
        res = requests.post(
            "https://weiban.mycourse.cn/pharos/usercourse/study.do",
            data=data,
            headers=headers,
        )
        while json.loads(res.text)['code'] == -1:
            await asyncio.sleep(5)
            res = requests.post(
                "https://weiban.mycourse.cn/pharos/usercourse/study.do",
                data=data,
                headers=headers,
            )
        print(f"start:{courseId}\r",end='')

    def finish(self, i, courseId, finishId):
        get_url_url = "https://weiban.mycourse.cn/pharos/usercourse/getCourseUrl.do"
        finish_url = "https://weiban.mycourse.cn/pharos/usercourse/v2/{}.do"
        data = {
            "userProjectId": self.userProjectId[i],
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "courseId": courseId,
        }
        requests.post(get_url_url, data=data, headers=self.headers)
        token = self.get_method_token(finishId)
        finish_url = finish_url.format(token)
        ts = self.__get_timestamp().replace(".", "")
        param = {
            "callback": "jQuery{}_{}".format(self.__gen_rand(), ts),
            "userCourseId": finishId,
            "tenantCode": self.tenantCode,
            "_": str(int(ts) + 1),
        }
        requests.get(finish_url, params=param, headers=self.headers).text
        print(f"{self.realName} Finish:{courseId}")

    def get_method_token(self, course_id):
        url = "https://weiban.mycourse.cn/pharos/usercourse/getCaptcha.do"
        params = {
            "userCourseId": course_id,
            "userProjectId": self.userProjectId,
            "userId": self.userId,
            "tenantCode": self.tenantCode
        }
        text = requests.get(url, headers=self.headers, params=params).text
        question_id = json.loads(text)['captcha']['questionId']
        url = "https://weiban.mycourse.cn/pharos/usercourse/checkCaptcha.do"
        params = {
            "userCourseId": course_id,
            "userProjectId": self.userProjectId,
            "userId": self.userId,
            "tenantCode": self.tenantCode,
            "questionId": question_id
        }
        data = {
            "coordinateXYs": "[{\"x\":199,\"y\":448},{\"x\":241,\"y\":466},{\"x\":144,\"y\":429}]"
        }
        text = requests.post(url, headers=self.headers, params=params, data=data).text
        return json.loads(text)['data']['methodToken']

def fill_key(key):
    key_size = 128
    filled_key = key.ljust(key_size // 8, b'\x00')
    return filled_key

def write_to_task_file(task_id, content):
    directory = './log'
    file_path = os.path.join(directory, f"{task_id}.txt")
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(file_path, 'a') as file:
        file.write(content + '\n')
    print(f"内容已写入到 {file_path}")

def aes_encrypt(data, key):
    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    base64_cipher = base64.b64encode(ciphertext).decode('utf-8')
    result_cipher = base64_cipher.replace('+', '-').replace('/', '_')
    return result_cipher


def login(payload):
    init_key = 'xie2gg'
    key = fill_key(init_key.encode('utf-8'))

    encrypted = aes_encrypt(
        f'{{"keyNumber":"{payload["userName"]}","password":"{payload["password"]}","tenantCode":"{payload["tenantCode"]}","time":{payload["timestamp"]},"verifyCode":"{payload["verificationCode"]}"}}',
        key
    )
    return encrypted

def apitruecaptcha(config, content):
    image=base64.b64encode(content)
    url = 'https://api.apitruecaptcha.org/one/gettext'
    data = {
        'data':str(image,'utf-8'),
        'userid':config["TrueCaptcha"]["userId"],
        'apikey':config["TrueCaptcha"]["apiKey"]
    }
    result = requests.post(url, json.dumps(data))
    res=result.json()
    try:verifycode = res['result']
    except:
        if res.get('success') == False:
            print(f"{res['error_type']} {res['error_message']}")
            if 'Credits' in res['error_message']:
                print("TrueCaptcha已达每日请求上限，无法再识别验证码。")
                return None
            else:verifycode = apitruecaptcha(config, content)
        elif res.get('message') == 'Internal server error':verifycode = apitruecaptcha(config, content)
        else:verifycode = apitruecaptcha(config, content)
    return verifycode

def get_tenant_code(school_name: str) -> str:
    tenant_list = requests.get(
        "https://weiban.mycourse.cn/pharos/login/getTenantListWithLetter.do"
    ).text
    data = json.loads(tenant_list)["data"]
    for i in data:
        for j in i["list"]:
            if j["name"] == school_name:
                return j["code"]

def set_accounts(accounts, password):
    global DEFAULT_SCHOOL_NAME
    file_path = 'config.json'  # 文件路径
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"文件 {file_path} 已删除")
    else:
        print(f"文件 {file_path} 不存在")
    try:
        with open("config.json", "r+", encoding='utf8') as file:config = json.load(file)
    except:
        config = {}
        config['TrueCaptcha'] = None
        config['Accounts'] = []
    # if config.get("TrueCaptcha") is None:
    #     print('验证码识别使用 TrueCaptcha.org，如果你想手动识别验证码，请按 Ctrl + C')
    #     try:
    #         config["TrueCaptcha"] = {}
    #         config["TrueCaptcha"]["userId"] = input('请输入 TrueCaptcha.org 的 userId：')
    #         config["TrueCaptcha"]["apiKey"] = input('请输入 TrueCaptcha.org 的 apiKey：')
    #         if config["TrueCaptcha"]["userId"] == '' or config["TrueCaptcha"]["apiKey"] == '':config["TrueCaptcha"] = None
    #     except KeyboardInterrupt:config["TrueCaptcha"] = None
    if config.get("TrueCaptcha") is None:print('\n你选择了手动识别验证码。\n')
    print('输入学校名、帐号、密码，结束输入请按 Ctrl + C')
    try:
        if config["Accounts"]:DEFAULT_SCHOOL_NAME = config["Accounts"][-1]['schoolName']
        while True:
            print(f'正在录入第 {len(config["Accounts"])+1} 个帐号')
            account = {}
            # 如果直接按回车，则将DEFAULT_SCHOOL_NAME的值赋给schoolName，否则将schoolName的值赋给DEFAULT_SCHOOL_NAME
            # account['schoolName'] = input(f'请输入学校名称（当前默认学校为 {DEFAULT_SCHOOL_NAME}）：')
            account['schoolName'] = DEFAULT_SCHOOL_NAME
            # if account['schoolName'] == '':account['schoolName'] = DEFAULT_SCHOOL_NAME
            # else:DEFAULT_SCHOOL_NAME = account['schoolName']
            account['id'] = accounts
            account['password'] = password
            account['State'] = 0
            # if account['id'] == '' or account['password'] == '':
            #     print(f'\n停止输入账号，已保存 {len(config["Accounts"])} 个帐号')
            config['Accounts'].append(account)
            break
    except KeyboardInterrupt:print(f'\n停止输入账号，已保存 {len(config["Accounts"])} 个帐号')
    with open('config.json', 'w', encoding='utf8') as file:
        file.write(json.dumps(config, indent=4, ensure_ascii=False))
    print('配置已保存。\n')
    return config

def check_captcha_status(task_id):
    """检查验证码状态"""
    try:
        response = requests.get(f"http://localhost:8000/status?task_id={task_id}")
        response.raise_for_status()
        status = response.json()
        return status
    except requests.RequestException:
        return {"status": "错误"}

def create_captcha_file(url, task_id):
    api_url = "http://localhost:8000/create-captcha-file"
    # 定义请求的数据
    data = {
        "url": url,
        "task_id": task_id
    }
    try:
        # 发送 POST 请求
        response = requests.post(api_url, json=data)
        # 检查请求是否成功
        response.raise_for_status()
        # 解析 JSON 响应
        result = response.json()
        return result
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}

def get_Login_State(config : dict, account : dict) -> dict:
    '''
    传入参数 config - 配置内容

    传入参数 account - 一组账户信息
    ```json
        {
            "schoolName": "XX学校",
            "id": "20230001",
            "password": "12345678",
            "State": 0
        }
    ```
    以字典形式 返回该账户的登录态
    
    ```json
        {
            "token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "userId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "tenantCode": "00000001",
            "realName": "张三"
        }
    ```
    '''
    school_name = account['schoolName']
    tenant_code = get_tenant_code(school_name=school_name)
    user_id = account['id']
    user_pwd = account['password']
    now = time.time()
    # 打开验证码
    img_data = requests.get(f"https://weiban.mycourse.cn/pharos/login/randLetterImage.do?time={now}").content
    if config['TrueCaptcha'] is None:
        print("验证码链接：",end='')
        print(f"https://weiban.mycourse.cn/pharos/login/randLetterImage.do?time={now}")
        url = f"https://weiban.mycourse.cn/pharos/login/randLetterImage.do?time={now}"
        print(user_id)
        create_captcha_file(url, user_id)
        # with open("code.jpg", "wb") as file:
        #     file.write(img_data)
        # file.close()
        # Image.open("code.jpg").show()
        # # 获取验证码
        # verity_code = input("请输入验证码:")
        # os.remove("code.jpg")
        # 轮询检查验证码状态
        while True:
            file_path = f'./captchas/captchas_{user_id}.txt'
            if os.path.exists(file_path):
                status = check_captcha_status(user_id)
                if status["status"] == "验证码已提交":
                    verity_code = status["code"]
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"文件 {file_path} 已删除")
                    else:
                        print(f"文件 {file_path} 不存在")
                    break
                else:
                    print("等待验证码提交...")
                    time.sleep(5)  # 每5秒检查一次
    else:
        verity_code = apitruecaptcha(config, img_data)
    # 调用js方法
    payload = {
        "userName": user_id,
        "password": user_pwd,
        "tenantCode": tenant_code,
        "timestamp": now,
        "verificationCode": verity_code
    }
    ret = login(payload)
    request_data = {"data": ret}

    response = requests.post(
        "https://weiban.mycourse.cn/pharos/login/login.do", data=request_data
    ).text
    response = json.loads(response)
    if response['code'] == '0':
        tenantCode = response.get('data').get('tenantCode')
        userId = response.get('data').get('userId')
        x_token = response.get('data').get('token')
        realName = response.get('data').get('realName')
        print(f"用户 {user_id} {realName} 登录成功")
        write_to_task_file(user_id, f"用户 {user_id} {realName} 登录成功")
        return {"token":x_token,"userId":userId,"tenantCode":tenantCode,"realName":realName,"raw_id":user_id}
    elif "账号与密码不匹配" in response["msg"] or "账号已被锁定" in response["msg"] or "权限错误" in response["msg"]:
        print(f'用户 {user_id} 登录失败，错误码 {response["code"]} 原因为 {response["msg"]}')
        write_to_task_file(user_id, f'用户 {user_id} 登录失败，错误码 {response["code"]} 原因为 {response["msg"]}')
        return {"is_locked":True,"raw_id":user_id}
    else:
        print(f'用户 {user_id} 登录失败，错误码 {response["code"]} 原因为 {response["msg"]}')
        write_to_task_file(user_id, f'用户 {user_id} 登录失败，错误码 {response["code"]} 原因为 {response["msg"]}')
        return get_Login_State(config, account)

def save_Login_State(config):
    if config.get('Accounts_login_state') is None or len(config['Accounts_login_state']) == 0:
        config['Accounts_login_state'] = []
        for account in config.get("Accounts"):
            if account['State'] == 1:print(f'用户 {account["id"]} 已经完成，跳过登录')
            elif account['State'] == 0:
                login_State = get_Login_State(config, account)
                if login_State.get("is_locked") is True:account['State'] = -1
                else:config['Accounts_login_state'].append(login_State)
            elif account['State'] == -1:print(f'用户 {account["id"]} 密码错误，无法登录')
            with open('config.json', 'w', encoding='utf8') as file:file.write(json.dumps(config, indent=4, ensure_ascii=False))
        print('登录态已保存。\n')
    else:
        print('已存在登录态，跳过登录。\n')
        write_to_task_file(account["id"], '已存在登录态，跳过登录。\n')