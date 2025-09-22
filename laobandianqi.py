#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
老板电器签到脚本
小程序名：老板电器
创建日期：2025-09-08
环境变量：
　　变量名：laobandianqi
　　变量值：x-user-token
　　多个账号间用#分隔：x-user-token1#x-user-token2
Token获取：打开小程序登录，抓包域名https://aio.myroki.com 请求头中的x-user-token的值
"""

import os
import sys
import time
from typing import Optional, Dict, Any

try:
    import httpx
except ImportError:
    print("❌ 请先安装依赖：httpx[http2]")
    sys.exit(1)

try:
    import cloud_auth
except ImportError:
    print("❌ 找不到云函数模块，请确保cloud_auth.py文件在同一目录下")
    print("访问https://github.com/3ixi/CloudScripts获取")
    sys.exit(1)

try:
    from SendNotify import SendNotify, start_capture, stop_capture_and_notify
    NOTIFICATION_ENABLED = True
except ImportError:
    print("⚠️ 未找到SendNotify模块，可前往 https://github.com/3ixi/CloudScripts 获取")
    NOTIFICATION_ENABLED = False
    def SendNotify(title="", content=""):
        pass
    def start_capture():
        pass
    def stop_capture_and_notify(title=""):
        pass


class LaoBanDianQi:
    def __init__(self):
        self.base_url = "https://aio.myroki.com"
        self.mod = "roki"
        self.nonce = "1234567890123456"

        self.user_tokens = self._load_user_tokens()

        try:
            self.auth_client = cloud_auth.get_auth_client()
        except Exception as e:
            print(f"❌ 初始化认证客户端失败: {e}")
            sys.exit(1)
    
    def _load_user_tokens(self) -> list:
        token_env = os.getenv('laobandianqi')
        if not token_env:
            print("❌ 未找到环境变量 'laobandianqi'，请设置您的JWT凭证")
            sys.exit(1)
        
        tokens = [token.strip() for token in token_env.split('#') if token.strip()]
        if not tokens:
            print("❌ 环境变量 'laobandianqi' 中没有有效的JWT凭证")
            sys.exit(1)
        
        return tokens
    
    def _get_timestamp(self) -> int:
        return int(time.time() * 1000)
    
    def _get_auth_info(self, timestamp: int) -> Dict[str, str]:
        try:
            response = self.auth_client.call_service(
                self.mod,
                timestamp=timestamp
            )

            if response.get('success'):
                secret = response.get('secret', '')
                signature = response.get('signature', '')

                if not secret or not signature:
                    raise Exception("返回的secret或signature为空")

                return {
                    'secret': secret,
                    'signature': signature
                }
            else:
                error_msg = response.get('error', '未知错误')
                raise Exception(f"获取认证信息失败: {error_msg}")

        except Exception as e:
            print(f"❌ 获取认证信息失败: {e}")
            raise
    
    def _build_headers(self, user_token: str, timestamp: int, secret: str, signature: str, method: str) -> Dict[str, str]:
        headers = {
            "host": "aio.myroki.com",
            "x-app-env": "release",
            "x-user-token": user_token,
            "timestamp": str(timestamp),
            "signature": signature,
            "nonce": self.nonce,
            "secret": secret,
            "app-version": "5000",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254101e) XWEB/16389",
            "content-type": "application/json",
            "app-id": "roki_app",
            "accept": "*/*",
            "referer": "https://servicewechat.com/wxba70fb8e3eb3aab9/344/page-frame.html",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "zh-CN,zh;q=0.9"
        }

        if method.upper() == "POST":
            headers["content-length"] = "2"
            
        return headers
    
    def _check_response(self, response_data: Dict[str, Any]) -> bool:
        success = response_data.get('success', False)
        if not success:
            message = response_data.get('message', '未知错误')
            print(f"❌ 请求失败: {message}")
            return False
        return True
    
    async def get_user_profile(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        try:
            response = await client.get(
                f"{self.base_url}/api/v1/mini-app/user/profile",
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            if self._check_response(data):
                return data.get('data', {})
            return None
            
        except Exception as e:
            print(f"❌ 获取用户信息失败: {e}")
            return None
    
    async def check_in(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        try:
            response = await client.post(
                f"{self.base_url}/api/v1/mini-app/user/check-in-record/check-in",
                headers=headers,
                json={}
            )
            response.raise_for_status()
            
            data = response.json()
            if self._check_response(data):
                return data.get('data', {})
            return None
            
        except Exception as e:
            print(f"❌ 签到失败: {e}")
            return None
    
    async def process_user(self, user_token: str, user_index: int):
        print(f"\n{'='*30}")
        print(f"处理第 {user_index + 1} 个账号")
        print(f"{'='*30}")
        
        timestamp = self._get_timestamp()
        try:
            auth_info = self._get_auth_info(timestamp)
        except Exception:
            return
        
        get_headers = self._build_headers(
            user_token, 
            timestamp, 
            auth_info['secret'], 
            auth_info['signature'],
            "GET"
        )
        
        post_headers = self._build_headers(
            user_token, 
            timestamp, 
            auth_info['secret'], 
            auth_info['signature'],
            "POST"
        )
        
        async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
            user_profile = await self.get_user_profile(client, get_headers)
            if not user_profile:
                return
            
            nick_name = user_profile.get('nickName', '未知用户')
            today_is_check_in = user_profile.get('todayIsCheckIn', 0)
            
            if today_is_check_in == 1:
                print(f"【{nick_name}】Token有效，今日已签到")
                await self._show_points_info(client, get_headers)
                return
            else:
                print(f"【{nick_name}】Token有效，今日未签到")
            
            check_in_result = await self.check_in(client, post_headers)
            if check_in_result:
                consecutive_days = check_in_result.get('consecutiveDays', 0)
                print(f"✅ 签到成功，已连续签到{consecutive_days}天")
                
                await self._show_points_info(client, get_headers)
    
    async def _show_points_info(self, client: httpx.AsyncClient, headers: Dict[str, str]):
        user_profile = await self.get_user_profile(client, headers)
        if user_profile:
            points = user_profile.get('points', 0)
            expiring_points = user_profile.get('expiringPoints', 0)
            
            if expiring_points > 0:
                print(f"📊 当前积分{points}，有{expiring_points}积分即将过期")
            else:
                print(f"📊 当前积分{points}")
    
    async def run(self):
        if NOTIFICATION_ENABLED:
            start_capture()
            
        print("🟢 老板电器签到脚本启动")
        print(f"📋️ 共找到 {len(self.user_tokens)} 个账号")
        
        for i, token in enumerate(self.user_tokens):
            await self.process_user(token, i)
        
        print(f"\n{'='*30}")
        print("✅ 所有账号处理完成")
        print(f"{'='*30}")
        
        if NOTIFICATION_ENABLED:
            stop_capture_and_notify("老板电器签到结果")


async def main():
    """主函数"""
    try:
        client = LaoBanDianQi()
        await client.run()
    except KeyboardInterrupt:
        print("\n❌ 脚本被用户中断")
        if NOTIFICATION_ENABLED:
            stop_capture_and_notify("老板电器脚本中断")
    except Exception as e:
        print(f"❌ 脚本运行出错: {e}")
        if NOTIFICATION_ENABLED:
            stop_capture_and_notify("老板电器脚本运行错误")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
