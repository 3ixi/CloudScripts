#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知模块 - 支持多种推送方式
创建日期：2025-09-16
支持的推送方式：WxPusher、PushPlus、企微Webhook、企微应用通知、Telegram、邮件、钉钉、Bark
"""

import os
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import sys
import io
from datetime import datetime
from typing import Optional, Dict, Any

# ==================== 配置区域 ====================
# 推送方式配置 - 将False改为True表示启用对应的推送方式
ENABLE_WXPUSHER = False          # WxPusher推送
ENABLE_PUSHPLUS = False          # PushPlus推送
ENABLE_WECOM_WEBHOOK = False     # 企业微信Webhook
ENABLE_WECOM_APP = False         # 企业微信应用通知
ENABLE_TELEGRAM = False          # Telegram推送
ENABLE_EMAIL = False             # 邮件推送
ENABLE_DINGTALK = False          # 钉钉推送
ENABLE_BARK = False              # Bark推送

# 在下方填写推送方式对应的参数，或者在环境变量中设置
# 比如可以创建环境变量PUSHPLUS_TOKEN，值就是用户token值
# 或者直接在''引号中填写用户token值
# 举例：PUSHPLUS_TOKEN = os.getenv('PUSHPLUS_TOKEN', 'y0owg5w5b81234569atdd84rr60yci7g')

# ==================== WxPusher配置 ====================
WXPUSHER_APP_TOKEN = os.getenv('WXPUSHER_APP_TOKEN', '')  # WxPusher的AppToken
WXPUSHER_UIDS = os.getenv('WXPUSHER_UIDS', '')            # 用户UID，多个用;分隔

# ==================== PushPlus配置 ====================
PUSHPLUS_TOKEN = os.getenv('PUSHPLUS_TOKEN', '')          # PushPlus的用户令牌

# ==================== 企业微信Webhook配置 ====================
WECOM_WEBHOOK_URL = os.getenv('WECOM_WEBHOOK_URL', '')    # 企业微信机器人Webhook地址

# ==================== 企业微信应用配置 ====================
WECOM_CORPID = os.getenv('WECOM_CORPID', '')              # 企业微信CorpID
WECOM_CORPSECRET = os.getenv('WECOM_CORPSECRET', '')      # 企业微信应用Secret
WECOM_AGENTID = os.getenv('WECOM_AGENTID', '')            # 企业微信应用AgentID
WECOM_TOUSER = os.getenv('WECOM_TOUSER', '@all')          # 接收用户，@all为全部

# ==================== Telegram配置 ====================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')  # Telegram Bot Token
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')      # Telegram Chat ID

# ==================== 邮件配置 ====================
EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER', '')    # SMTP服务器
EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587')) # SMTP端口
EMAIL_USER = os.getenv('EMAIL_USER', '')                  # 发送邮箱
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')          # 邮箱密码或授权码
EMAIL_TO = os.getenv('EMAIL_TO', '')                      # 接收邮箱，多个用;分隔

# ==================== 钉钉配置 ====================
DINGTALK_WEBHOOK_URL = os.getenv('DINGTALK_WEBHOOK_URL', '') # 钉钉机器人Webhook地址
DINGTALK_SECRET = os.getenv('DINGTALK_SECRET', '')           # 钉钉机器人密钥

# ==================== Bark配置 ====================
BARK_SERVER = os.getenv('BARK_SERVER', '')                # Bark服务器地址
BARK_DEVICE_KEY = os.getenv('BARK_DEVICE_KEY', '')        # Bark设备密钥

# ==================== 输出捕获类 ====================
class OutputCapture:
    
    def __init__(self):
        self.content = []
        self.original_stdout = sys.stdout
        self.capture_enabled = False
    
    def start_capture(self):
        if not self.capture_enabled:
            self.capture_enabled = True
            sys.stdout = self._DualOutput(self.original_stdout, self)
    
    def stop_capture(self):
        if self.capture_enabled:
            sys.stdout = self.original_stdout
            self.capture_enabled = False
    
    def add_content(self, content):
        if content:
            self.content.append(str(content))
    
    def get_content(self):
        return "\n".join(self.content)
    
    def clear(self):
        self.content.clear()
    
    def __enter__(self):
        self.start_capture()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_capture()
    
    class _DualOutput:
        
        def __init__(self, original_stdout, capture_instance):
            self.original_stdout = original_stdout
            self.capture_instance = capture_instance
        
        def write(self, text):
            self.original_stdout.write(text)
            if text.strip():
                self.capture_instance.add_content(text.strip())
        
        def flush(self):
            self.original_stdout.flush()
        
        def __getattr__(self, name):
            return getattr(self.original_stdout, name)

_global_output_capture = OutputCapture()

def capture_output(title="脚本运行结果"):
    def decorator(func):
        def wrapper(*args, **kwargs):
            global _global_output_capture
            
            _global_output_capture.clear()
            _global_output_capture.start_capture()
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                _global_output_capture.add_content(f"❌ 脚本运行错误: {e}")
                raise
            finally:
                _global_output_capture.stop_capture()
                
                captured_content = _global_output_capture.get_content()
                if captured_content:
                    SendNotify(title, captured_content)
        
        return wrapper
    return decorator


def start_capture():
    global _global_output_capture
    _global_output_capture.clear()
    _global_output_capture.start_capture()


def stop_capture_and_notify(title="脚本运行结果"):
    global _global_output_capture
    _global_output_capture.stop_capture()
    
    captured_content = _global_output_capture.get_content()
    if captured_content:
        SendNotify(title, captured_content)


def add_to_capture(content):
    global _global_output_capture
    _global_output_capture.add_content(content)


try:
    import requests
except ImportError:
    print("❌ 请先安装依赖：requests")
    sys.exit(1)


class NotificationSender:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CloudScripts-Notification/1.0'
        })

    def _truncate_title(self, content: str, max_length: int = 30) -> str:
        if not content:
            return "3iXi云函数脚本通知"
        
        title = content.replace('\n', ' ').replace('\r', ' ').strip()
        if len(title) > max_length:
            title = title[:max_length] + "..."
        
        return title or "3iXi云函数脚本通知"

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ==================== WxPusher推送 ====================
    def send_wxpusher(self, title: str, content: str) -> bool:
        """WxPusher推送"""
        if not WXPUSHER_APP_TOKEN or not WXPUSHER_UIDS:
            print("⚠️ WxPusher配置不完整，跳过推送")
            return False

        try:
            url = "https://wxpusher.zjiecode.com/api/send/message"
            
            uids = [uid.strip() for uid in WXPUSHER_UIDS.split(';') if uid.strip()]
            
            data = {
                "appToken": WXPUSHER_APP_TOKEN,
                "content": content,
                "summary": title,
                "contentType": 1,
                "uids": uids
            }
            
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 1000:
                print("✅ WxPusher推送成功")
                return True
            else:
                print(f"❌ WxPusher推送失败: {result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ WxPusher推送异常: {e}")
            return False

    # ==================== PushPlus推送 ====================
    def send_pushplus(self, title: str, content: str) -> bool:
        """PushPlus推送"""
        if not PUSHPLUS_TOKEN:
            print("⚠️ PushPlus配置不完整，跳过推送")
            return False

        try:
            url = "http://www.pushplus.plus/send"
            
            data = {
                "token": PUSHPLUS_TOKEN,
                "title": title,
                "content": content,
                "template": "html"
            }
            
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                print("✅ PushPlus推送成功")
                return True
            else:
                print(f"❌ PushPlus推送失败: {result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ PushPlus推送异常: {e}")
            return False

    # ==================== 企业微信Webhook推送 ====================
    def send_wecom_webhook(self, title: str, content: str) -> bool:
        if not WECOM_WEBHOOK_URL:
            print("⚠️ 企业微信Webhook配置不完整，跳过推送")
            return False

        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }
            
            response = self.session.post(WECOM_WEBHOOK_URL, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') == 0:
                print("✅ 企业微信Webhook推送成功")
                return True
            else:
                print(f"❌ 企业微信Webhook推送失败: {result.get('errmsg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ 企业微信Webhook推送异常: {e}")
            return False

    # ==================== 企业微信应用推送 ====================
    def _get_wecom_access_token(self) -> Optional[str]:
        try:
            url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
            params = {
                "corpid": WECOM_CORPID,
                "corpsecret": WECOM_CORPSECRET
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') == 0:
                return result.get('access_token')
            else:
                print(f"❌ 获取企业微信访问令牌失败: {result.get('errmsg', '未知错误')}")
                return None
                
        except Exception as e:
            print(f"❌ 获取企业微信访问令牌异常: {e}")
            return None

    def send_wecom_app(self, title: str, content: str) -> bool:
        if not all([WECOM_CORPID, WECOM_CORPSECRET, WECOM_AGENTID]):
            print("⚠️ 企业微信应用配置不完整，跳过推送")
            return False

        try:
            access_token = self._get_wecom_access_token()
            if not access_token:
                return False
            
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            data = {
                "touser": WECOM_TOUSER,
                "msgtype": "text",
                "agentid": int(WECOM_AGENTID),
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }
            
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') == 0:
                print("✅ 企业微信应用推送成功")
                return True
            else:
                print(f"❌ 企业微信应用推送失败: {result.get('errmsg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ 企业微信应用推送异常: {e}")
            return False

    # ==================== Telegram推送 ====================
    def send_telegram(self, title: str, content: str) -> bool:
        """Telegram推送"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("⚠️ Telegram配置不完整，跳过推送")
            return False

        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            
            message = f"*{title}*\n\n{content}"
            
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                print("✅ Telegram推送成功")
                return True
            else:
                print(f"❌ Telegram推送失败: {result.get('description', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram推送异常: {e}")
            return False

    # ==================== 邮件推送 ====================
    def send_email(self, title: str, content: str) -> bool:
        """邮件推送"""
        if not all([EMAIL_SMTP_SERVER, EMAIL_USER, EMAIL_PASSWORD, EMAIL_TO]):
            print("⚠️ 邮件配置不完整，跳过推送")
            return False

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.header import Header
            
            msg = MIMEMultipart()
            msg['From'] = Header(f"CloudScripts <{EMAIL_USER}>", 'utf-8')
            msg['Subject'] = Header(title, 'utf-8')
            
            text_content = MIMEText(content, 'plain', 'utf-8')
            msg.attach(text_content)
            
            to_emails = [email.strip() for email in EMAIL_TO.split(';') if email.strip()]
            
            server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            
            for to_email in to_emails:
                msg['To'] = Header(to_email, 'utf-8')
                server.sendmail(EMAIL_USER, to_email, msg.as_string())
            
            server.quit()
            print("✅ 邮件推送成功")
            return True
            
        except Exception as e:
            print(f"❌ 邮件推送异常: {e}")
            return False

    # ==================== 钉钉推送 ====================
    def _get_dingtalk_sign(self, timestamp: int, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return sign

    def send_dingtalk(self, title: str, content: str) -> bool:
        if not DINGTALK_WEBHOOK_URL:
            print("⚠️ 钉钉配置不完整，跳过推送")
            return False

        try:
            url = DINGTALK_WEBHOOK_URL
            
            if DINGTALK_SECRET:
                timestamp = int(time.time() * 1000)
                sign = self._get_dingtalk_sign(timestamp, DINGTALK_SECRET)
                url += f"&timestamp={timestamp}&sign={sign}"
            
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }
            
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') == 0:
                print("✅ 钉钉推送成功")
                return True
            else:
                print(f"❌ 钉钉推送失败: {result.get('errmsg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ 钉钉推送异常: {e}")
            return False

    # ==================== Bark推送 ====================
    def send_bark(self, title: str, content: str) -> bool:
        if not BARK_SERVER or not BARK_DEVICE_KEY:
            print("⚠️ Bark配置不完整，跳过推送")
            return False

        try:
            server = BARK_SERVER.rstrip('/')
            url = f"{server}/{BARK_DEVICE_KEY}/{urllib.parse.quote(title)}/{urllib.parse.quote(content)}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                print("✅ Bark推送成功")
                return True
            else:
                print(f"❌ Bark推送失败: {result.get('message', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ Bark推送异常: {e}")
            return False

    # ==================== 主推送方法 ====================
    def send_notification(self, title: str = "", content: str = "") -> bool:
        if not content:
            print("⚠️ 通知内容为空，跳过推送")
            return False
        
        if not title:
            title = self._truncate_title(content)
        
        timestamp = self._get_current_time()
        content = f"发送时间: {timestamp}\n\n{content}"
        
        success_count = 0
        total_count = 0
        
        if ENABLE_WXPUSHER:
            total_count += 1
            if self.send_wxpusher(title, content):
                success_count += 1
        
        if ENABLE_PUSHPLUS:
            total_count += 1
            if self.send_pushplus(title, content):
                success_count += 1
        
        if ENABLE_WECOM_WEBHOOK:
            total_count += 1
            if self.send_wecom_webhook(title, content):
                success_count += 1
        
        if ENABLE_WECOM_APP:
            total_count += 1
            if self.send_wecom_app(title, content):
                success_count += 1
        
        if ENABLE_TELEGRAM:
            total_count += 1
            if self.send_telegram(title, content):
                success_count += 1
        
        if ENABLE_EMAIL:
            total_count += 1
            if self.send_email(title, content):
                success_count += 1
        
        if ENABLE_DINGTALK:
            total_count += 1
            if self.send_dingtalk(title, content):
                success_count += 1
        
        if ENABLE_BARK:
            total_count += 1
            if self.send_bark(title, content):
                success_count += 1
        
        if total_count == 0:
            print("⚠️ 未启用任何推送方式")
            return False
        
        print(f"📊 推送结果: {success_count}/{total_count} 成功")
        return success_count > 0


_notification_sender = None

def SendNotify(title: str = "", content: str = "") -> bool:
    global _notification_sender
    
    if _notification_sender is None:
        _notification_sender = NotificationSender()
    
    return _notification_sender.send_notification(title, content)


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("📱 SendNotify通知模块测试")
    print("=" * 30)
    
    # 测试通知
    test_title = "SendNotify测试通知"
    test_content = """这是一条测试通知消息。

测试内容包括：
✅ 通知模块正常工作
📱 推送功能测试成功
🔔 各平台推送状态正常

如果您收到此消息，说明通知配置正确"""
    
    result = SendNotify(test_title, test_content)
    
    if result:
        print("✅ 测试完成，有推送成功")
    else:
        print("❌ 测试完成，但没有推送成功")