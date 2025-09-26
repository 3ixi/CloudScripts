#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
石小羊家园签到脚本
小程序名：石小羊家园
创建日期：2025-09-23
环境变量：
    变量名：sxyjy
    变量值：Xyjy-Auth的值
    多个账号用#分隔：Xyjy-Auth1#Xyjy-Auth2
说明：登录小程序，任意选择社区/职业，注册后开启抓包，随便点一下页面，抓包任意https://xy-api-jswm.gxshiyang.cn 网址请求头中的Xyjy-Auth的值。
"""

import os
import sys
import time
import random
from typing import Optional, Dict, Any, List

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
    import SendNotify as _sn
    SendNotify = getattr(_sn, 'SendNotify', lambda title="", content="": None)
    start_capture = getattr(_sn, 'start_capture', lambda: None)
    stop_capture_and_notify = getattr(_sn, 'stop_capture_and_notify', lambda title="": None)
    NOTIFICATION_ENABLED = hasattr(_sn, 'SendNotify')
except ImportError:
    NOTIFICATION_ENABLED = False
    def SendNotify(title="", content=""):
        return None
    def start_capture():
        return None
    def stop_capture_and_notify(title=""):
        return None


class ShiXiaoYang:
    def __init__(self):
        self.base_url = "https://xy-api-jswm.gxshiyang.cn"
        self.mod = "shiyang"

        self.user_tokens = self._load_user_tokens()

        try:
            self.auth_client = cloud_auth.get_auth_client()
        except Exception as e:
            print(f"❌ 初始化认证客户端失败: {e}")
            sys.exit(1)

    def _load_user_tokens(self) -> List[str]:
        token_env = os.getenv('sxyjy')
        if not token_env:
            print("❌ 未找到环境变量sxyjy")
            sys.exit(1)

        tokens = [t.strip() for t in token_env.split('#') if t.strip()]
        if not tokens:
            print("❌ 环境变量'sxyjy'中没有有效的Token")
            sys.exit(1)

        return tokens

    def _get_timestamp(self) -> int:
        return int(time.time() * 1000)

    def _build_headers(self, user_token: str, method: str) -> Dict[str, str]:
        headers = {
            "Host": "xy-api-jswm.gxshiyang.cn",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541022) XWEB/16467",
            "Xyjy-Auth": user_token,
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": "https://xy-h5.gxshiyang.cn",
            "Referer": "https://xy-h5.gxshiyang.cn/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        return headers

    def _decrypt_response(self, raw_text: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self.auth_client.call_service(self.mod, encrypted=raw_text)

            if isinstance(resp, dict):
                if 'code' in resp:
                    return resp
                if 'data' in resp and isinstance(resp['data'], (dict, list)):
                    return resp

            return None
        except Exception as e:
            print(f"❌ 云解密失败: {e}")
            return None

    async def _get_and_decrypt(self, client: httpx.AsyncClient, path: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        try:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            raw = r.text
            decrypted = self._decrypt_response(raw)
            if not decrypted:
                print("❌ 解密后内容无效")
                return None
            return decrypted
        except Exception as e:
            print(f"❌ GET请求失败: {e}")
            return None

    async def _post_and_decrypt(self, client: httpx.AsyncClient, path: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        try:
            import json
            body = json.dumps(payload, separators=(',',':'))
            body_bytes = body.encode('utf-8')
            local_headers = dict(headers)
            local_headers['Content-Length'] = str(len(body_bytes))
            r = await client.post(url, headers=local_headers, content=body_bytes)
            r.raise_for_status()
            raw = r.text
            decrypted = self._decrypt_response(raw)
            if not decrypted:
                print("❌ 解密后内容无效")
                return None
            return decrypted
        except Exception as e:
            print(f"❌ POST 请求失败: {e}")
            return None

    async def _post_plain(self, client: httpx.AsyncClient, path: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        try:
            body = __import__('json').dumps(payload, separators=(',',':'))
            body_bytes = body.encode('utf-8')
            local_headers = dict(headers)
            local_headers['Content-Length'] = str(len(body_bytes))
            r = await client.post(url, headers=local_headers, content=body_bytes)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"❌ POST请求失败: {e}")
            return None

    async def process_user(self, user_token: str, user_index: int):
        print(f"\n{'='*30}")
        print(f"处理第 {user_index + 1} 个账号")
        print(f"{'='*30}")

        async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
            # 1. 获取账号信息
            ts = self._get_timestamp()
            path = f"/credit-shop/app/creditAppUser/getCreditAppUserCount?xy_timestamp={ts}"
            headers = self._build_headers(user_token, "GET")
            info = await self._get_and_decrypt(client, path, headers)
            if not info:
                return

            if info.get('code') != 200:
                print(f"❌ {info.get('msg')}")
                return

            data = info.get('data', {})
            user_name = data.get('userName', '未知用户')
            credit = data.get('credit', 0)
            print(f"【{user_name}】Token有效，当前积分{credit}")

            # 2. 检查是否签到
            ts = self._get_timestamp()
            path = f"/credit-shop/app/creditSignRule/signRuleList?xy_timestamp={ts}"
            headers = self._build_headers(user_token, "POST")
            rule_resp = await self._post_and_decrypt(client, path, headers, {})
            if not rule_resp:
                return

            if rule_resp.get('code') != 200:
                print(f"❌ {rule_resp.get('msg')}")
                return

            rules = rule_resp.get('data', [])
            today_item = None
            for item in rules:
                if item.get('isToday'):
                    today_item = item
                    break

            if not today_item:
                print("⚠️ 未找到今日签到配置，跳过")
            else:
                if today_item.get('isSign'):
                    print(f"【{user_name}】已签到，跳过签到")
                else:
                    # 提交签到
                    ts = self._get_timestamp()
                    path = f"/credit-shop/app/creditSignRule/sign?xy_timestamp={ts}"
                    headers = self._build_headers(user_token, "POST")
                    payload = {"id": str(today_item.get('id','')) , "reward": int(today_item.get('reward',0))}
                    sign_resp = await self._post_and_decrypt(client, path, headers, payload)
                    if sign_resp and sign_resp.get('code') == 200:
                        print(f"{sign_resp.get('data')}")

            # 3. 获取未做任务
            ts = self._get_timestamp()
            path = f"/credit-shop/app/creditTask/list?xy_timestamp={ts}"
            headers = self._build_headers(user_token, "GET")
            tasks_resp = await self._get_and_decrypt(client, path, headers)
            if not tasks_resp:
                return

            if tasks_resp.get('code') != 200:
                print(f"❌ {tasks_resp.get('msg')}")
                return

            tasks = tasks_resp.get('data', [])
            todo_names = [t.get('name') for t in tasks if int(t.get('finishNumber',0)) == 0]

            # 打印今日待完成任务数
            try:
                todo_count = len(todo_names)
            except Exception:
                todo_count = 0
            print(f"今日共有{todo_count}个待完成任务")

            # 4. 提交完成任务，每个请求间隔1-3秒
            for name in todo_names:
                ts = self._get_timestamp()
                path = f"/credit-shop/app/creditTask/complete?xy_timestamp={ts}"
                headers = self._build_headers(user_token, "POST")
                payload = {"taskType": name}
                plain_resp = await self._post_plain(client, path, headers, payload)
                if plain_resp:
                    msg = plain_resp.get('msg', '')
                    print(f"任务【{name}】提交完成，{msg}")
                else:
                    print(f"任务【{name}】提交失败")

                await __import__('asyncio').sleep(random.uniform(1,3))

            # 等待一段时间让任务状态更新
            print("等待任务状态更新...")
            await __import__('asyncio').sleep(3)

            # 所有待做任务提交完成后，获取已完成待领取奖励的任务列表并尝试领取
            ts = self._get_timestamp()
            path = f"/credit-shop/app/carouselChart/getList?xy_timestamp={ts}"
            headers = self._build_headers(user_token, "GET")
            finished_resp = await self._get_and_decrypt(client, path, headers)
            if not finished_resp:
                print("⚠️ 获取已完成任务列表失败或解密失败")
            else:
                if finished_resp.get('code') != 200:
                    print(f"⚠️ 获取已完成任务列表返回错误: {finished_resp.get('msg')}")
                else:
                    finished_tasks = finished_resp.get('data', [])
                    print(f"📋 获取到 {len(finished_tasks)} 个任务状态信息")

                    for task in finished_tasks:
                        task_name = task.get('name', '未知任务')
                        finish_num = task.get('finishNumber', 0)
                        task_id = task.get('id', 'N/A')
                        print(f"  任务【{task_name}】")
                        # print(f"  任务【{task_name}】- ID: {task_id}, finishNumber: {finish_num}")

                    to_receive = [t for t in finished_tasks if int(t.get('finishNumber', 0)) == 1]
                    print(f"检测到 {len(to_receive)} 个待领取奖励的任务")

                    if len(to_receive) > 0:
                        print("开始领取任务奖励...")
                        for item in to_receive:
                            task_name = item.get('name')
                            task_id = item.get('id')
                            print(f"准备领取任务【{task_name}】奖励")
                            if not task_id:
                                print(f"  ⚠️ 任务【{task_name}】缺少ID，跳过")
                                continue
                            ts = self._get_timestamp()
                            recv_path = f"/credit-shop/app/creditTask/receive?taskId={task_id}&xy_timestamp={ts}"
                            recv_headers = self._build_headers(user_token, "GET")
                            try:
                                url = f"{self.base_url}{recv_path}"
                                r = await client.get(url, headers=recv_headers)
                                r.raise_for_status()
                                recv_resp = r.json()
                            except Exception as e:
                                print(f"  ⚠️ 任务【{task_name}】领取奖励时请求失败: {e}")
                                continue

                            if recv_resp.get('code') != 200:
                                print(f"  ⚠️ 任务【{task_name}】领取奖励返回错误: {recv_resp.get('msg')}")
                                continue

                            reward_raw = recv_resp.get('data')
                            reward_decrypted = None
                            try:
                                if isinstance(reward_raw, str):
                                    maybe = self.auth_client.call_service(self.mod, encrypted=reward_raw)
                                    if isinstance(maybe, dict):
                                        reward_decrypted = maybe.get('data') if 'data' in maybe else maybe
                                    else:
                                        reward_decrypted = maybe
                                else:
                                    reward_decrypted = reward_raw
                            except Exception as e:
                                print(f"  ⚠️ 任务【{task_name}】奖励解密失败: {e}")
                                reward_decrypted = reward_raw

                            print(f"  ✅ 任务【{task_name}】奖励领取成功: {reward_decrypted}")

                            # 每次领取奖励后等待一下
                            await __import__('asyncio').sleep(1)
                    else:
                        print("暂无待领取奖励的任务")
            # 在所有任务完成后，再次请求最新的积分
            ts = self._get_timestamp()
            path = f"/credit-shop/app/creditAppUser/getCreditAppUserCount?xy_timestamp={ts}"
            headers = self._build_headers(user_token, "GET")
            latest = await self._get_and_decrypt(client, path, headers)
            if latest and latest.get('code') == 200:
                latest_data = latest.get('data', {})
                credit_now = latest_data.get('credit', credit)
                print(f"今日任务完成，当前积分{credit_now}")
            else:
                if latest and 'msg' in latest:
                    print(f"⚠️ 获取最新积分失败: {latest.get('msg')}")
                else:
                    print("⚠️ 获取最新积分失败或解密失败")

    async def run(self):
        if NOTIFICATION_ENABLED:
            start_capture()

        print("🟢 石小羊家园自动任务脚本启动")
        print(f"📋️ 共找到 {len(self.user_tokens)} 个账号")

        for i, token in enumerate(self.user_tokens):
            await self.process_user(token, i)

        print(f"\n{'='*30}")
        print("✅ 所有账号处理完成")
        print(f"{'='*30}")

        if NOTIFICATION_ENABLED:
            stop_capture_and_notify("石小羊家园签到结果")


async def main():
    try:
        client = ShiXiaoYang()
        await client.run()
    except KeyboardInterrupt:
        print("\n❌ 脚本被用户中断")
        if NOTIFICATION_ENABLED:
            stop_capture_and_notify("石小羊家园脚本中断")
    except Exception as e:
        print(f"❌ 脚本运行出错: {e}")
        if NOTIFICATION_ENABLED:
            stop_capture_and_notify("石小羊家园脚本运行错误")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
