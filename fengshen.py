#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风神Club签到脚本
小程序名：风神Club
创建日期：2025-09-11
环境变量：
　　变量名：fengshen
　　变量值：userId&token
　　多个账号间用#分隔：userId1&token1#userId2&token2
Token获取：打开小程序登录，抓包域名https://fsapp.dfmc.com.cn/appv3/api 中返回数据以accessToken开头的那条数据，获取userId和token值（注意这里是token，不是accessToken）
！！此脚本会获取账号Token到云端生成加密签名，但不会在云端保存，介意请勿使用！！
"""

import os
import sys
import time
import random
import json
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import requests
except ImportError:
    print("❌ 请先安装依赖：requests")
    print("安装命令：pip install requests")
    sys.exit(1)

try:
    import cloud_auth
except ImportError:
    print("❌ 找不到云函数模块，请确保cloud_auth.py文件在同一目录下")
    print("访问https://github.com/3ixi/CloudScripts获取")
    sys.exit(1)


class FengShen:
    def __init__(self):
        self.base_url = "https://fsapp.dfmc.com.cn/appv3/api"
        self.mod = "fsapp"
        
        self.user_credentials = self._load_user_credentials()
        
        try:
            self.auth_client = cloud_auth.get_auth_client()
        except Exception as e:
            print(f"❌ 初始化认证客户端失败: {e}")
            sys.exit(1)
    
    def _load_user_credentials(self) -> list:
        credential_env = os.getenv('fengshen')
        if not credential_env:
            print("❌ 未找到环境变量'fengshen'，请设置您的账号Token")
            print("格式：userId&token，多个账号用#分隔")
            sys.exit(1)
        
        credentials = []
        for cred in credential_env.split('#'):
            cred = cred.strip()
            if cred and '&' in cred:
                uid, token = cred.split('&', 1)
                credentials.append({'uid': uid.strip(), 'token': token.strip()})
        
        if not credentials:
            print("❌ 环境变量'fengshen'中没有有效的账号Token")
            sys.exit(1)
        
        return credentials
    
    def _get_timestamp(self) -> int:
        return int(time.time() * 1000)
    
    def _generate_noncestr(self) -> str:
        r = int(time.time() * 1000)
        noncestr = ""
        
        for _ in range(32):
            t = int((r + 16 * random.random()) % 16)
            r = r // 16
            noncestr += format(t, 'x')
        
        return noncestr
    
    def _get_auth_signatures(self, timestamp: int, uid: str, token: str, api: str, noncestr: str) -> Dict[str, str]:
        try:
            response = self.auth_client.call_service(
                self.mod,
                timestamp=timestamp,
                uid=uid,
                token=token,
                api=api,
                noncestr=noncestr
            )

            if response.get('success'):
                keysign = response.get('keysign', '')
                sign = response.get('sign', '')

                if not keysign or not sign:
                    raise Exception("返回的keysign或sign为空")

                return {
                    'keysign': keysign,
                    'sign': sign
                }
            else:
                error_msg = response.get('error', '未知错误')
                raise Exception(f"获取签名信息失败: {error_msg}")

        except Exception as e:
            print(f"❌ 获取签名信息失败: {e}")
            raise
    
    def _build_headers(self, uid: str, api: str, keysign: str, sign: str, timestamp: int, noncestr: str, payload: str = "") -> Dict[str, str]:
        content_length = len(payload.encode('utf-8')) if payload else 0
        
        headers = {
            "Host": "fsapp.dfmc.com.cn",
            "Connection": "keep-alive",
            "Content-Length": str(content_length),
            "content-type": "application/json",
            "appid": "appJUGpYPchujWIBc6EfaA1XksysvZqvqB1",
            "keysign": keysign,
            "appcode": "miniprogram",
            "uid": uid,
            "apitype": "8",
            "noncestr": noncestr,
            "brand": "fs",
            "timestamp": str(timestamp),
            "lang": "cn",
            "api": api,
            "sign": sign,
            "Accept-Encoding": "gzip,compress,br,deflate",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.62(0x18003e3a) NetType/WIFI Language/zh_CN",
            "Referer": "https://servicewechat.com/wxae0a9289f3272125/426/page-frame.html"
        }
        
        return headers
    
    def _check_response(self, response_data: Dict[str, Any]) -> bool:
        result = response_data.get('result', '0')
        if result != '1':
            msg = response_data.get('msg', '未知错误')
            print(f"❌ 请求失败: {msg}")
            return False
        return True
    
    def _make_request(self, uid: str, token: str, api: str, payload: str = "{}") -> Optional[Dict[str, Any]]:
        timestamp = self._get_timestamp()
        noncestr = self._generate_noncestr()
        
        try:
            auth_info = self._get_auth_signatures(timestamp, uid, token, api, noncestr)
        except Exception:
            return None
        
        headers = self._build_headers(
            uid, api, auth_info['keysign'], auth_info['sign'], 
            timestamp, noncestr, payload
        )
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                data=payload,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
    
    def check_token_validity(self, uid: str, token: str) -> Optional[Dict[str, Any]]:
        api = "ly.mp.miniprogram.growth.points.user.query"
        response_data = self._make_request(uid, token, api)
        
        if response_data and self._check_response(response_data):
            return response_data.get('rows', {})
        return None
    
    def check_signin_status(self, uid: str, token: str) -> Optional[Dict[str, Any]]:
        api = "ly.mp.miniprogram.owninfo.get"
        response_data = self._make_request(uid, token, api)
        
        if response_data and self._check_response(response_data):
            return response_data.get('rows', {})
        return None
    
    def signin(self, uid: str, token: str) -> bool:
        api = "ly.mp.miniprogram.activity.namiSignin"
        response_data = self._make_request(uid, token, api)
        
        if response_data and self._check_response(response_data):
            msg = response_data.get('msg', '签到成功')
            today = datetime.now().strftime('%Y-%m-%d')
            print(f"✅ {today} {msg}")
            return True
        return False
    
    def get_points(self, uid: str, token: str) -> Optional[Dict[str, Any]]:
        api = "ly.mp.miniprogram.growth.points.user.query"
        response_data = self._make_request(uid, token, api)
        
        if response_data and self._check_response(response_data):
            return response_data.get('rows', {})
        return None
    
    def process_user(self, credential: Dict[str, str], user_index: int):
        uid = credential['uid']
        token = credential['token']
        
        print(f"\n{'='*50}")
        print(f"处理第 {user_index + 1} 个账号 (UID: {uid})")
        print(f"{'='*50}")
        
        user_info = self.check_token_validity(uid, token)
        if not user_info:
            print(f"账号userId【{uid}】Token失效，请更新")
            return
        
        member_name = user_info.get('memberName', '未知用户')
        soon_expire_points = int(user_info.get('soonExpirePointsSum', '0'))
        
        if soon_expire_points > 0:
            print(f"【{member_name}】Token有效，有{soon_expire_points}积分即将过期")
        else:
            print(f"【{member_name}】Token有效")
        
        signin_info = self.check_signin_status(uid, token)
        if not signin_info:
            return
        
        is_sign = signin_info.get('isSign', 0)
        if is_sign == 1:
            print("今日已签到")
        else:
            print("今日未签到")
            self.signin(uid, token)
        
        points_info = self.get_points(uid, token)
        if points_info:
            can_use_points = points_info.get('canUsePoints', '0')
            print(f"📊 当前可用积分{can_use_points}")
    
    def run(self):
        print("🟢 风神签到脚本启动")
        print(f"📋️ 共找到 {len(self.user_credentials)} 个账号")
        
        for i, credential in enumerate(self.user_credentials):
            self.process_user(credential, i)
        
        print(f"\n{'='*50}")
        print("✅ 所有账号处理完成")
        print(f"{'='*50}")


def main():
    try:
        client = FengShen()
        client.run()
    except KeyboardInterrupt:
        print("\n❌ 脚本被用户中断")
    except Exception as e:
        print(f"❌ 脚本运行出错: {e}")


if __name__ == "__main__":
    main()