#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONE 自动购买白嫖点播脚本
APP下载链接：https://2f2279ygf3x29x.icu?code=jqJ9txPeVS
创建日期：2025-10-10
说明：访问https://onelogin.316199.xyz/ 登录账号（未注册也可直接登录）并获取config.json配置文件，将下载下来的config.json配置文件保存到脚本同级目录
"""
import os
import json
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

import cloud_auth

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, 'config.json')

# 清理空账号信息
def clean_empty_accounts(config):
    if 'accounts' in config and isinstance(config['accounts'], list):
        # 过滤掉所有必填字段为空的账号
        original_count = len(config['accounts'])
        config['accounts'] = [account for account in config['accounts'] 
                             if account.get('TOKEN') and account.get('USER_KEY')]
        
        # 如果有账号被移除，更新配置文件
        if len(config['accounts']) < original_count:
            print(f"已清理 {original_count - len(config['accounts'])} 个空账号")
            write_config(config)
    
    return config

# 检查配置文件是否存在并验证必要的配置项
def check_config():
    if not os.path.exists(config_path):
        print("=" * 30)
        print("❌ 未找到配置文件config.json")
        print("")
        print("📱 请使用浏览器访问以下网址登录并获取配置文件：")
        print("🔗 https://onelogin.316199.xyz")
        print("")
        print("下载配置文件后，将其放在脚本同级目录下")
        print("=" * 30)
        return False
    
    try:
        config = read_config()
        
        # 清理空账号
        config = clean_empty_accounts(config)
        
        # 检查账号配置
        if not config.get('accounts') or len(config['accounts']) == 0:
            print("配置文件中缺少账号信息，请至少配置一个账号")
            return False
            
        # 确保共用的配置项在根级别存在
        common_fields = ["API_URL", "APP_VERSION", "PLATFORM"]
        missing_common_fields = [field for field in common_fields if not config.get(field)]
        if missing_common_fields:
            print(f"配置文件缺少以下共用配置项: {', '.join(missing_common_fields)}")
            print("请在配置文件中填入这些信息")
            return False
            
        # 检查每个账号的必要字段
        required_account_fields = ["TOKEN", "USER_KEY"]
        for i, account in enumerate(config['accounts']):
            missing_fields = [field for field in required_account_fields if not account.get(field)]
            if missing_fields:
                print(f"账号 {i+1} 缺少以下必要项: {', '.join(missing_fields)}")
                print("请在配置文件中填入这些信息后再运行脚本")
                return False
        
        # 确保SendNotify字段存在
        if 'SendNotify' not in config:
            config['SendNotify'] = False
            write_config(config)
        
        return True
    
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return False

# 读取配置文件
def read_config():
    with open(config_path, 'r', encoding='utf-8') as file:
        config = json.load(file)
    return config

# 写入配置文件
def write_config(config):
    with open(config_path, 'w', encoding='utf-8') as file:
        json.dump(config, file, ensure_ascii=False, indent=4)

# 调用云函数接口刷新Token
def refresh_token_cloud(auth_client, account, config):
    try:
        result = auth_client.call_service(
            'ONE',
            action='refresh_token',
            token=account['TOKEN'],
            user_key=account['USER_KEY'],
            api_url=config['API_URL'],
            app_version=config['APP_VERSION'],
            platform=config['PLATFORM']
        )
        
        if result.get('success'):
            data = result.get('data', {})
            if data.get('code') == 200:
                user_data = data['data']['user']
                account['TOKEN'] = user_data['token']
                account['nickname'] = user_data.get('nickname', account.get('nickname', ''))
                account['avatar'] = user_data.get('avatar', account.get('avatar', ''))
                account['integral'] = user_data.get('integral', account.get('integral', 0))
                account['login_ip'] = user_data.get('login_ip', account.get('login_ip', ''))
                account['updated_at'] = user_data.get('updated_at', account.get('updated_at', ''))
                
                if 'domain' in data['data'] and 'api' in data['data']['domain']:
                    api_list = data['data']['domain']['api']
                    config['api_list'] = api_list
                        
                    current_buy_url = config.get('buy_url', '')
                    if current_buy_url not in api_list and api_list:
                        config['buy_url'] = api_list[0]
                
                return True, "Token更新成功"
            else:
                return False, f"请求失败: {data.get('mezsage', '未知错误')}"
        else:
            return False, result.get('error', '未知错误')
    except Exception as e:
        return False, f"刷新Token失败: {e}"

# 调用云函数接口获取文章列表
def get_article_list_cloud(auth_client, account, config, published_at, page=1):
    try:
        buy_url = config.get('buy_url', config['api_list'][0] if config.get('api_list') else 'https://api.pjq6he.com')
        
        result = auth_client.call_service(
            'ONE',
            action='get_list',
            token=account['TOKEN'],
            user_key=account['USER_KEY'],
            buy_url=buy_url,
            app_version=config['APP_VERSION'],
            platform=config['PLATFORM'],
            published_at=published_at,
            page=page,
            size=20
        )
        
        if result.get('success'):
            return True, result.get('data', {})
        else:
            return False, result.get('error', '未知错误')
    except Exception as e:
        return False, str(e)

# 调用云函数接口执行购买操作
def purchase_item_cloud(auth_client, account, config, item_id):
    try:
        buy_url = config.get('buy_url', config['api_list'][0] if config.get('api_list') else 'https://api.pjq6he.com')
        
        result = auth_client.call_service(
            'ONE',
            action='purchase',
            token=account['TOKEN'],
            user_key=account['USER_KEY'],
            buy_url=buy_url,
            app_version=config['APP_VERSION'],
            platform=config['PLATFORM'],
            item_id=item_id
        )
        
        if result.get('success'):
            return True, result.get('data', {})
        else:
            return False, result.get('error', '未知错误')
    except Exception as e:
        return False, str(e)

# 执行购买操作的函数
def execute_freebuy(auth_client):
    # 读取配置
    config = read_config()
    
    # 清理空账号
    config = clean_empty_accounts(config)
    
    # 获取公共配置
    accounts = config['accounts']
    
    # 统计购买成功的数量
    purchase_count = 0
    
    for account_idx, account in enumerate(accounts):
        account_name = account.get('nickname', f'账号{account_idx+1}')
        print(f"\n正在为 {account_name} 执行白嫖购买操作...")
        
        try:
            # 刷新Token
            success, mezsage = refresh_token_cloud(auth_client, account, config)
            if success:
                print(f"{account_name} Token刷新成功")
                # 更新配置
                config['accounts'][account_idx] = account
                write_config(config)
            else:
                print(f"❌ {account_name} Token刷新失败: {mezsage}")
                continue
            
            # 获取当前月份
            current_year, current_month = datetime.now().year, datetime.now().month
            published_at = f"20;{current_year - 2020}-{current_month}"
            
            # 获取文章列表
            success, data = get_article_list_cloud(auth_client, account, config, published_at, 1)
            
            if not success:
                print(f"❌ {account_name} 获取文章列表失败: {data}")
                continue
            
            # 查找buy和coin同时为0的数据
            if not data.get('data'):
                print(f"{account_name} 没有找到可以购买的点播")
                continue
            
            buyable_items = [item for item in data['data'] if item['buy'] == 0 and item['coin'] == '0']
            
            if not buyable_items:
                print(f"{account_name} 本次没有找到可以购买的点播")
            else:
                for item in buyable_items:
                    buy_id = item['id']
                    buy_title = item['title']
                    print(f"尝试为账号 {account_name} 购买ID为 {buy_id} 的点播，标题为 {buy_title}")
                    
                    # 执行购买
                    success, buy_data = purchase_item_cloud(auth_client, account, config, buy_id)
                    
                    if success:
                        result = buy_data.get('mezsage', '未知')
                        print(f"✅ {account_name} 购买成功: {buy_title} - {result}")
                        purchase_count += 1
                    else:
                        print(f"❌ {account_name} 购买失败: {buy_title} - {buy_data}")
        
        except Exception as e:
            print(f"❌ 处理账号 {account_name} 时发生错误: {e}")
    
    return purchase_count

# 主函数
def main():
    # 检查配置文件
    if not check_config():
        return
    
    print("\n====== ONE白嫖脚本开始执行 ======")
    print("脚本作者:3iXi,版本:V9C,更新时间:25/10/10")
    print("本脚本免费使用,让你付费的均是骗子")
    
    enable_notify = False
    
    try:
        # 读取配置文件
        config = read_config()
        
        # 获取账号数量
        accounts = config.get('accounts', [])
        account_count = len(accounts)
        
        if account_count == 0:
            print("配置文件中没有账号信息，请先配置账号")
            return
        
        print(f"共有 {account_count} 个账号配置")
        
        # 判断是否需要启用SendNotify
        enable_notify = config.get('SendNotify', False)
        if enable_notify:
            try:
                from SendNotify import start_capture, stop_capture_and_notify
                start_capture()
                print("✅ SendNotify通知已启用\n")
            except ImportError:
                print("⚠️ 未找到SendNotify.py模块，将不发送通知\n")
                enable_notify = False
        
        # 创建云函数认证客户端
        auth_client = cloud_auth.get_auth_client()
        
        # 执行购买流程
        purchase_count = execute_freebuy(auth_client)
        
        print("\n====== ONE白嫖脚本执行完成 ======")
        
        if purchase_count > 0:
            print(f"🎉 本次共成功购买 {purchase_count} 个点播")
            # 只有购买成功时才发送通知
            if enable_notify:
                from SendNotify import stop_capture_and_notify
                stop_capture_and_notify("ONE白嫖脚本执行结果")
        else:
            print("ℹ️  本次没有购买到新点播")
            # 没有购买到点播时停止捕获但不发送通知
            if enable_notify:
                from SendNotify import _global_output_capture
                _global_output_capture.stop_capture()
            
    except KeyboardInterrupt:
        print("\n⚠️  脚本被用户中断")
        # 中断时如果有购买成功才发送通知
        if enable_notify:
            try:
                if 'purchase_count' in locals() and purchase_count > 0:
                    from SendNotify import stop_capture_and_notify
                    stop_capture_and_notify("ONE白嫖脚本执行结果")
                else:
                    from SendNotify import _global_output_capture
                    _global_output_capture.stop_capture()
            except:
                pass
    except Exception as e:
        print(f"❌ 执行脚本时出现未处理的异常: {e}")
        # 异常时如果有购买成功才发送通知
        if enable_notify:
            try:
                if 'purchase_count' in locals() and purchase_count > 0:
                    from SendNotify import stop_capture_and_notify
                    stop_capture_and_notify("ONE白嫖脚本执行结果")
                else:
                    from SendNotify import _global_output_capture
                    _global_output_capture.stop_capture()
            except:
                pass

if __name__ == "__main__":
    main()