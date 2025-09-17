#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AnyProxy - API代理转发模块
通过拦截requests和httpx库的请求，实现透明代理功能
在任意脚本导入此模块后，可实现所有请求均通过代理服务器转发，而不是使用本机IP请求
创建日期：2025-09-17
模块作者：3iXi
项目主页：https://github.com/3ixi/CloudScripts

使用说明：
1. 在任意脚本（包括加密脚本）开头导入此模块：import AnyProxy
2. 设置环境变量CloudAuth为授权码（可通过https://3ixi.top 获取）
"""

import os
import json
import time
import base64
import sys
from datetime import datetime
from urllib.parse import urlparse

def check_required_packages():
    missing_packages = []

    try:
        import requests
    except ImportError:
        missing_packages.append('requests')

    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad
    except ImportError:
        missing_packages.append('pycryptodome')

    if missing_packages:
        print("❌ AnyProxy缺少必需的依赖库，请安装以下库：")
        print()
        for package in missing_packages:
            print(f"   {package}")
        print()
        print("安装完成后请重新运行脚本。")
        sys.exit(1)

check_required_packages()

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

DEFAULT_PROXY_SERVERS = ["https://cloud.3ixi.top", "https://3ixi.top"]

class AnyProxyClient:
    def __init__(self):
        self.proxy_servers = self._get_proxy_servers()
        self.current_server_index = 0
        self.auth_code = self._load_auth_code()
        self._init_crypto_params()
        
        # 需要排除的域名（不进行代理的域名）,如果有域名请求失败，可以在此处填写
        self.excluded_domains = {
            '3ixi.top',
            'cloud.3ixi.top', 
            'localhost',
            '127.0.0.1',
            'api.day.app',
            'oapi.dingtalk.com',
            'open.feishu.cn',
            'push.hellyw.com',
            'sctapi.ftqq.com',
            'sc.ftqq.com',
            'api2.pushdeer.com',
            'www.weplusbot.com',
            'qmsg.zendee.cn',
            'qyapi.weixin.qq.com',
            'api.telegram.org',
            'api-bot.aibotk.com',
            'push.i-i.me',
            'v1.hitokoto.cn',
            'pushplus.hxtrip.com',
            'www.pushplus.plus'
        }
        
        self._internal_session = requests.Session()
        
        self._original_requests = {}
        self._original_httpx = {}
        self._original_session_methods = {}
        
        self._enable_proxy()
        
        print("🎭️ AnyProxy已启用，所有请求将通过代理服务器转发")
        #print(f"🚫 排除域名: {', '.join(self.excluded_domains)}")

    def _init_crypto_params(self):
        key_fragments = {                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            'auth_token': 'QGp3', 'session_key': 'PFUk','api_path': 'MERJYmQp','api_host': 'ZW4pPw==',}

        connection_order = ['auth_token', 'session_key', 'api_path', 'api_host']
        proxy_get = ''.join([key_fragments[segment] for segment in connection_order])

        try:
            proxy_post = base64.b64decode(proxy_get).decode('utf-8')
            if len(proxy_post) == 16:
                self.proxy_go = proxy_post
                return
        except:
            pass

        backup_sequence = [64, 106, 119, 60, 85, 36, 48, 68, 73, 98, 100, 41, 101, 110, 41, 63]
        self.proxy_go = ''.join([chr(x) for x in backup_sequence])

    def _get_proxy_servers(self):
        proxy_server = os.getenv('PROXY_SERVER')
        if proxy_server:
            return [proxy_server.rstrip('/')]
        return DEFAULT_PROXY_SERVERS

    def _load_auth_code(self):
        auth_code = os.getenv('CloudAuth')
        if not auth_code:
            raise ValueError("未找到环境变量'CloudAuth'，请访问https://3ixi.top获取授权码")
        return auth_code

    def _load_auth_code(self):
        auth_code = os.getenv('CloudAuth')
        if not auth_code:
            raise ValueError("未找到环境变量'CloudAuth'，请设置授权码")
        return auth_code

    def _get_current_server(self):
        return self.proxy_servers[self.current_server_index].rstrip('/')

    def _switch_to_next_server(self):
        self.current_server_index = (self.current_server_index + 1) % len(self.proxy_servers)
        return self._get_current_server()

    def _should_proxy_request(self, url):
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.hostname
            
            if domain in self.excluded_domains:
                return False
                
            for excluded_domain in self.excluded_domains:
                if domain and domain.endswith(f'.{excluded_domain}'):
                    return False
                    
            return True
        except Exception:
            return False
        
    def _get_timestamps_now(self, timestamp_ms):
        now = datetime.fromtimestamp(timestamp_ms / 1000)
        year = now.year
        month = now.month
        day = now.day

        year_last_two = year % 100
        month_last_digit = month % 10
        ydd = f"{year_last_two:02d}{month_last_digit}{day:02d}"

        timestamp_str = str(timestamp_ms)[-13:]

        timestamps_string = timestamp_str + ydd[-3:]

        timestamp_bytes = timestamps_string.encode('utf-8')

        if len(timestamp_bytes) < 16:
            timestamp_bytes += b'\x00' * (16 - len(timestamp_bytes))
        elif len(timestamp_bytes) > 16:
            timestamp_bytes = timestamp_bytes[:16]

        return timestamp_bytes

    def _handle(self, data):
        timestamp_ms = int(time.time() * 1000)
        
        times = self._get_timestamps_now(timestamp_ms)
        
        cipher = AES.new(self.proxy_go.encode('utf-8'), AES.MODE_CBC, times)
        
        padded_data = pad(data.encode('utf-8'), AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)
        
        encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
        random_hex = hex(timestamp_ms)[2:]
        
        return encrypted_b64, random_hex

    def _aes_decrypt(self, encrypted_data, random_hex):
        timestamp_ms = int(random_hex, 16)
        
        times = self._get_timestamps_now(timestamp_ms)
        
        cipher = AES.new(self.proxy_go.encode('utf-8'), AES.MODE_CBC, times)
        
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted_padded = cipher.decrypt(encrypted_bytes)
        decrypted_data = unpad(decrypted_padded, AES.block_size)
        
        return decrypted_data.decode('utf-8')

    def _prepare_request_data(self, method, url, **kwargs):
        request_data = {
            'url': url,
            'method': method.upper(),
            'headers': kwargs.get('headers', {}),
        }
        
        if 'data' in kwargs:
            if isinstance(kwargs['data'], (dict, list)):
                request_data['body'] = json.dumps(kwargs['data'])
                if 'Content-Type' not in request_data['headers']:
                    request_data['headers']['Content-Type'] = 'application/json'
            elif isinstance(kwargs['data'], str):
                try:
                    json.loads(kwargs['data'])
                    request_data['body'] = kwargs['data']
                except json.JSONDecodeError:
                    request_data['body'] = kwargs['data']
                if 'Content-Type' not in request_data['headers'] and kwargs['data']:
                    request_data['headers']['Content-Type'] = 'application/json' if '{"' in kwargs['data'][:2] else 'text/plain'
            elif isinstance(kwargs['data'], bytes):
                try:
                    decoded_data = kwargs['data'].decode('utf-8')
                    json.loads(decoded_data)
                    request_data['body'] = decoded_data
                except (UnicodeDecodeError, json.JSONDecodeError):
                    request_data['body'] = kwargs['data'].decode('utf-8', errors='ignore')
                if 'Content-Type' not in request_data['headers']:
                    request_data['headers']['Content-Type'] = 'application/json'
            else:
                request_data['body'] = str(kwargs['data'])
        elif 'json' in kwargs:
            request_data['body'] = json.dumps(kwargs['json'])
            if 'Content-Type' not in request_data['headers']:
                request_data['headers']['Content-Type'] = 'application/json'
        
        if 'params' in kwargs:
            request_data['params'] = kwargs['params']
        if 'timeout' in kwargs:
            request_data['timeout'] = kwargs['timeout']
        if 'verify' in kwargs:
            request_data['verify'] = kwargs['verify']
        if 'allow_redirects' in kwargs:
            request_data['allow_redirects'] = kwargs['allow_redirects']
        
        return request_data

    def _make_proxy_request(self, method, url, **kwargs):
        if not self._should_proxy_request(url):
            original_method = self._original_requests.get(method.lower())
            if original_method:
                return original_method(url, **kwargs)
            else:
                return getattr(self._internal_session, method.lower())(url, **kwargs)
        
        request_data = self._prepare_request_data(method, url, **kwargs)
        
        proxy_data = {
            'auth_code': self.auth_code,
            'request': request_data
        }
        
        json_data = json.dumps(proxy_data, ensure_ascii=False)
        encrypted_data, random_hex = self._handle(json_data)
        
        headers = {
            'Content-Type': 'application/json',
            'random': random_hex
        }
        
        for _ in range(len(self.proxy_servers)):
            current_server = self._get_current_server()
            proxy_url = f"{current_server}/api/proxy"
            
            try:
                response = self._internal_session.post(
                    proxy_url, 
                    json={'data': encrypted_data}, 
                    headers=headers, 
                    timeout=30
                )
                
                response.raise_for_status()
                
                response_data = response.json()
                if 'data' in response_data:
                    decrypted_response = self._aes_decrypt(response_data['data'], random_hex)
                    result = json.loads(decrypted_response)
                    
                    if result.get('success'):
                        return self._create_response_object(result['response'])
                    else:
                        error_message = result.get('error', '代理请求失败')
                        if "今日代理使用次数已达到上限" in error_message:
                            print(f"🚨 {error_message}")
                        elif "已被管理员禁止访问" in error_message:
                            print(f"🚫 {error_message}")
                        elif "检测到滥用行为" in error_message:
                            print(f"⚠️  {error_message}")
                            print("您的授权码已被禁用，请联系管理员")
                        elif "授权码无效或已被禁用" in error_message:
                            print(f"🚫 {error_message}")
                            print("您的授权码已被禁用，请联系管理员")
                        raise Exception(error_message)
                else:
                    raise Exception('响应格式错误')
                    
            except Exception as e:
                print(f"代理请求失败: {e}")
                self._switch_to_next_server()
                print(f"尝试切换到备用代理服务器")
        
        raise Exception("所有代理服务器均请求失败，请检查网络连接或服务器状态")

    def _create_response_object(self, response_data):
        class ProxyResponse:
            def __init__(self, data):
                self.status_code = data.get('status', 200)
                self.reason = data.get('statusText', 'OK')
                self.headers = data.get('headers', {})
                self._content = data.get('data', '')
                self._json_data = None
                
                if isinstance(self._content, str):
                    try:
                        self._json_data = json.loads(self._content)
                    except:
                        pass
                else:
                    self._json_data = self._content

            def json(self):
                if self._json_data is not None:
                    return self._json_data
                raise ValueError("响应内容不是有效的JSON")

            @property
            def text(self):
                if isinstance(self._content, str):
                    return self._content
                return json.dumps(self._content)

            @property
            def content(self):
                return self.text.encode('utf-8')

            def raise_for_status(self):
                if 400 <= self.status_code < 600:
                    raise requests.HTTPError(f"{self.status_code} {self.reason}")

        return ProxyResponse(response_data)

    def _enable_proxy(self):
        self._original_requests['get'] = requests.get
        self._original_requests['post'] = requests.post
        self._original_requests['put'] = requests.put
        self._original_requests['delete'] = requests.delete
        self._original_requests['patch'] = requests.patch
        self._original_requests['head'] = requests.head
        self._original_requests['options'] = requests.options
        
        requests.get = lambda url, **kwargs: self._make_proxy_request('GET', url, **kwargs) if self._should_proxy_request(url) else self._original_requests['get'](url, **kwargs)
        requests.post = lambda url, **kwargs: self._make_proxy_request('POST', url, **kwargs) if self._should_proxy_request(url) else self._original_requests['post'](url, **kwargs)
        requests.put = lambda url, **kwargs: self._make_proxy_request('PUT', url, **kwargs) if self._should_proxy_request(url) else self._original_requests['put'](url, **kwargs)
        requests.delete = lambda url, **kwargs: self._make_proxy_request('DELETE', url, **kwargs) if self._should_proxy_request(url) else self._original_requests['delete'](url, **kwargs)
        requests.patch = lambda url, **kwargs: self._make_proxy_request('PATCH', url, **kwargs) if self._should_proxy_request(url) else self._original_requests['patch'](url, **kwargs)
        requests.head = lambda url, **kwargs: self._make_proxy_request('HEAD', url, **kwargs) if self._should_proxy_request(url) else self._original_requests['head'](url, **kwargs)
        requests.options = lambda url, **kwargs: self._make_proxy_request('OPTIONS', url, **kwargs) if self._should_proxy_request(url) else self._original_requests['options'](url, **kwargs)
        
        self._original_session_methods['request'] = requests.Session.request
        
        def patched_session_request(session_self, method, url, **kwargs):
            if session_self is self._internal_session:
                return self._original_session_methods['request'](session_self, method, url, **kwargs)
            
            if not self._should_proxy_request(url):
                return self._original_session_methods['request'](session_self, method, url, **kwargs)
            
            return self._make_proxy_request(method, url, **kwargs)
        
        requests.Session.request = patched_session_request
        
        try:
            import httpx
            self._original_httpx['get'] = httpx.get
            self._original_httpx['post'] = httpx.post
            self._original_httpx['put'] = httpx.put
            self._original_httpx['delete'] = httpx.delete
            self._original_httpx['patch'] = httpx.patch
            self._original_httpx['head'] = httpx.head
            self._original_httpx['options'] = httpx.options
            
            self._original_httpx['AsyncClient'] = httpx.AsyncClient
            
            httpx.get = lambda url, **kwargs: self._make_proxy_request('GET', url, **kwargs) if self._should_proxy_request(url) else self._original_httpx['get'](url, **kwargs)
            httpx.post = lambda url, **kwargs: self._make_proxy_request('POST', url, **kwargs) if self._should_proxy_request(url) else self._original_httpx['post'](url, **kwargs)
            httpx.put = lambda url, **kwargs: self._make_proxy_request('PUT', url, **kwargs) if self._should_proxy_request(url) else self._original_httpx['put'](url, **kwargs)
            httpx.delete = lambda url, **kwargs: self._make_proxy_request('DELETE', url, **kwargs) if self._should_proxy_request(url) else self._original_httpx['delete'](url, **kwargs)
            httpx.patch = lambda url, **kwargs: self._make_proxy_request('PATCH', url, **kwargs) if self._should_proxy_request(url) else self._original_httpx['patch'](url, **kwargs)
            httpx.head = lambda url, **kwargs: self._make_proxy_request('HEAD', url, **kwargs) if self._should_proxy_request(url) else self._original_httpx['head'](url, **kwargs)
            httpx.options = lambda url, **kwargs: self._make_proxy_request('OPTIONS', url, **kwargs) if self._should_proxy_request(url) else self._original_httpx['options'](url, **kwargs)
            
            httpx.AsyncClient = self._create_patched_async_client()
            
            print("✅ 已拦截httpx库的请求")
        except ImportError:
            pass

    def _create_patched_async_client(self):
        original_async_client = self._original_httpx['AsyncClient']
        proxy_client_instance = self
        
        class PatchedAsyncClient(original_async_client):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._proxy_client = proxy_client_instance
                
            async def request(self, method, url, **kwargs):
                if not self._proxy_client._should_proxy_request(url):
                    return await super().request(method, url, **kwargs)
                
                try:
                    proxy_response = self._proxy_client._make_proxy_request(method, url, **kwargs)
                    
                    class MockAsyncResponse:
                        def __init__(self, proxy_resp):
                            self.status_code = proxy_resp.status_code
                            self.headers = proxy_resp.headers
                            self._content = proxy_resp.content
                            self._text = proxy_resp.text
                            self._proxy_resp = proxy_resp
                            
                        def json(self):
                            return self._proxy_resp.json()
                            
                        @property
                        def text(self):
                            return self._text
                            
                        @property
                        def content(self):
                            return self._content
                            
                        def raise_for_status(self):
                            self._proxy_resp.raise_for_status()
                    
                    return MockAsyncResponse(proxy_response)
                    
                except Exception as e:
                    print(f"⚠️  代理请求失败，回退到原始请求: {e}")
                    return await super().request(method, url, **kwargs)
                    
            async def get(self, url, **kwargs):
                return await self.request('GET', url, **kwargs)
                
            async def post(self, url, **kwargs):
                return await self.request('POST', url, **kwargs)
                
            async def put(self, url, **kwargs):
                return await self.request('PUT', url, **kwargs)
                
            async def delete(self, url, **kwargs):
                return await self.request('DELETE', url, **kwargs)
                
            async def patch(self, url, **kwargs):
                return await self.request('PATCH', url, **kwargs)
                
            async def head(self, url, **kwargs):
                return await self.request('HEAD', url, **kwargs)
                
            async def options(self, url, **kwargs):
                return await self.request('OPTIONS', url, **kwargs)
        
        return PatchedAsyncClient
        self.excluded_domains.add(domain)
        print(f"✅ 已添加排除域名: {domain}")
        
    def remove_excluded_domain(self, domain):
        if domain in self.excluded_domains:
            self.excluded_domains.remove(domain)
            print(f"✅ 已移除排除域名: {domain}")
        else:
            print(f"⚠️  域名 {domain} 不在排除列表中")
    
    def list_excluded_domains(self):
        print(f"🚫 当前排除域名: {', '.join(sorted(self.excluded_domains))}")
        return list(self.excluded_domains)
    def add_excluded_domain(self, domain):
        self.excluded_domains.add(domain)
        print(f"✅ 已添加排除域名: {domain}")
        
    def remove_excluded_domain(self, domain):
        if domain in self.excluded_domains:
            self.excluded_domains.remove(domain)
            print(f"✅ 已移除排除域名: {domain}")
        else:
            print(f"⚠️  域名 {domain} 不在排除列表中")
    
    def list_excluded_domains(self):
        print(f"🚫 当前排除域名: {', '.join(sorted(self.excluded_domains))}")
        return list(self.excluded_domains)
        
    def disable_proxy(self):
        for method, original_func in self._original_requests.items():
            setattr(requests, method, original_func)
        
        for method, original_func in self._original_session_methods.items():
            setattr(requests.Session, method, original_func)
        
        try:
            import httpx
            for method, original_func in self._original_httpx.items():
                if method == 'AsyncClient':
                    httpx.AsyncClient = original_func
                else:
                    setattr(httpx, method, original_func)
        except ImportError:
            pass
        
        print("🔄 AnyProxy已禁用，恢复原始请求方法")

proxy_client = None

def enable_proxy():
    """启用代理功能"""
    global proxy_client
    if proxy_client is None:
        proxy_client = AnyProxyClient()
    return proxy_client

def disable_proxy():
    """禁用代理功能"""
    global proxy_client
    if proxy_client is not None:
        proxy_client.disable_proxy()
        proxy_client = None

def add_excluded_domain(domain):
    """添加排除域名"""
    global proxy_client
    if proxy_client is not None:
        proxy_client.add_excluded_domain(domain)
    else:
        print("⚠️  AnyProxy未启用")

def remove_excluded_domain(domain):
    """移除排除域名"""
    global proxy_client
    if proxy_client is not None:
        proxy_client.remove_excluded_domain(domain)
    else:
        print("⚠️  AnyProxy未启用")

def list_excluded_domains():
    """列出排除域名"""
    global proxy_client
    if proxy_client is not None:
        return proxy_client.list_excluded_domains()
    else:
        print("⚠️  AnyProxy未启用")
        return []

proxy_client = enable_proxy()
if __name__ == "__main__":
    print("AnyProxy - API代理转发模块")
    print("=" * 30)
    print("使用说明：")
    print("1. 在需要代理的脚本开头插入导入语句：import AnyProxy")
    print("2. 设置环境变量CloudAuth为授权码")
