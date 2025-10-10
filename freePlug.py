#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONE 自动购买历史点播脚本
APP下载链接：https://2f2279ygf3x29x.icu?code=jqJ9txPeVS
创建日期：2025-10-10
说明：访问https://onelogin.316199.xyz/ 登录账号（未注册也可直接登录）并获取config.json配置文件，将下载下来的config.json配置文件保存到脚本同级目录
"""
import os
import json
import time
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

import cloud_auth

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, 'config.json')

def read_config():
    with open(config_path, 'r', encoding='utf-8') as file:
        config = json.load(file)
    return config

def write_config(config):
    with open(config_path, 'w', encoding='utf-8') as file:
        json.dump(config, file, ensure_ascii=False, indent=4)

def check_config():
    if not os.path.exists(config_path):
        print("=" * 30)
        print("❌ 未找到配置文件 config.json")
        print("")
        print("📱 请使用浏览器访问以下网址登录并获取配置文件：")
        print("🔗 https://onelogin.316199.xyz")
        print("")
        print("获取配置文件后，将其保存为 config.json 并放在脚本同目录下")
        print("=" * 30)
        return False
    return True

def get_previous_month(year, month):
    if month == 1:
        return year - 1, 12
    else:
        return year, month - 1

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
                return True, "Token更新成功"
            else:
                return False, f"请求失败: {data.get('mezsage', '未知错误')}"
        else:
            return False, result.get('error', '未知错误')
    except Exception as e:
        return False, f"刷新Token失败: {e}"

def get_article_list_cloud(auth_client, account, config, published_at, page=1):
    try:
        buy_url = config.get('buy_url', 'https://api.zbdk8ws.com')
        
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

def purchase_item_cloud(auth_client, account, config, item_id):
    try:
        buy_url = config.get('buy_url', 'https://api.zbdk8ws.com')
        
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

def main():
    # 检查配置文件
    if not check_config():
        return
    
    # 读取配置
    config = read_config()
    
    # 清理空账号
    config = clean_empty_accounts(config)
    
    # 获取结束月份配置
    end_month_config = config.get('end_month', '2021-9')
    try:
        end_year, end_month = map(int, end_month_config.split('-'))
        print(f"将扫描点播列表直到 {end_year}年{end_month}月")
    except:
        # 默认结束月份为2021年9月
        end_year, end_month = 2021, 9
        print(f"结束月份配置有误，将使用默认值: {end_year}年{end_month}月")
    
    # 从当前月开始逐月请求直到结束月份
    current_year, current_month = datetime.now().year, datetime.now().month
    
    print("\n====== ONE插件白嫖脚本开始执行 ======")
    print(f"共有 {len(config['accounts'])} 个账号配置")
    print("脚本作者:3iXi,版本:V9C,更新时间:25/10/10")
    print("本脚本免费使用，让你付费的均是骗子")
    
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
    
    # 统计购买成功的数量
    total_purchase_count = 0
    
        try:
            auth_client = cloud_auth.get_auth_client()
        except Exception as e:
            print(f"❌ 创建云函数认证客户端失败: {e}")
            return
    
        # 为每个账号执行白嫖操作
        for account_idx, account in enumerate(config['accounts']):
            account_name = account.get('nickname', f'账号{account_idx+1}')
            print(f"\n开始为 {account_name} 执行白嫖操作...")
            
            # 先刷新Token
            success, message = refresh_token_cloud(auth_client, account, config)
            if success:
                print(f"{account_name} Token刷新成功")
                # 更新配置
                config['accounts'][account_idx] = account
                write_config(config)
            else:
                print(f"❌ {account_name} Token刷新失败: {message}")
                continue
        
            # 重置当前年月
            scan_year, scan_month = current_year, current_month
        
            while (scan_year > end_year) or (scan_year == end_year and scan_month >= end_month):
                published_at = f"20;{scan_year - 2020}-{scan_month}"
                    
                print(f"{account_name}: 开始扫描 {scan_year}年{scan_month}月 的数据...")
            
                # 每月请求60页
                page = 1
                has_data = True  # 标记当前月份是否有数据
                month_purchase_count = 0  # 本月购买成功的数量
                    
                while page <= 60 and has_data:
                    # 获取文章列表
                    success, data = get_article_list_cloud(auth_client, account, config, published_at, page)
                    
                    if not success:
                        print(f"❌ {account_name}: {scan_year}年{scan_month}月 第 {page} 页请求失败: {data}")
                        break
                    
                    # 如果没有数据，跳过当前月
                    if not data.get('data'):
                        has_data = False
                        break
                    
                    # 查找buy和coin同时为0的数据
                    buyable_items = [item for item in data['data'] if item['buy'] == 0 and item['coin'] == '0']
                        
                    if buyable_items:
                        for item in buyable_items:
                            buy_id = item['id']
                            buy_title = item['title']
                                
                            # 执行购买
                            success, buy_data = purchase_item_cloud(auth_client, account, config, buy_id)
                                
                            if success:
                                result = buy_data.get('mezsage', '未知')
                                print(f"✅ {account_name}: 购买成功 - {buy_title} ({result})")
                                month_purchase_count += 1
                                total_purchase_count += 1
                            else:
                                print(f"❌ {account_name}: 购买失败 - {buy_title} ({buy_data})")
                    
                    # 如果是最后一页，跳出循环
                    if len(data['data']) < 20:
                        break
                    
                    # 增加页数，继续请求下一页
                    page += 1
                
                if month_purchase_count > 0:
                    print(f"📊 {account_name}: {scan_year}年{scan_month}月 共购买成功 {month_purchase_count} 个点播")
                
                # 请求完当前月份后，刷新当前账号TOKEN
                success, message = refresh_token_cloud(auth_client, account, config)
                if success:
                    config['accounts'][account_idx] = account
                    write_config(config)
            
                # 更新当前月份为前一个月
                scan_year, scan_month = get_previous_month(scan_year, scan_month)
                
                # 如果已经到达结束月份，退出循环
                if (scan_year < end_year) or (scan_year == end_year and scan_month < end_month):
                    print(f"{account_name}: 已达到结束月份 {end_year}年{end_month}月，结束扫描。")
                    break
    
        print("\n====== ONE插件白嫖脚本执行完成 ======")
        
        if total_purchase_count > 0:
            print(f"🎉 本次共成功购买 {total_purchase_count} 个点播")
            # 只有购买成功时才发送通知
            if enable_notify:
                from SendNotify import stop_capture_and_notify
                stop_capture_and_notify("ONE插件白嫖脚本执行结果")
        else:
            print("ℹ️  本次没有购买到新点播")
            # 没有购买到点播时停止捕获但不发送通知
            if enable_notify:
                from SendNotify import _global_output_capture
                _global_output_capture.stop_capture()
    
    except KeyboardInterrupt:
        print("\n⚠️  脚本被用户中断")
        # 中断时如果有购买成功也发送通知
        if enable_notify:
            try:
                if 'total_purchase_count' in locals() and total_purchase_count > 0:
                    from SendNotify import stop_capture_and_notify
                    stop_capture_and_notify("ONE插件白嫖脚本执行结果")
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
                if 'total_purchase_count' in locals() and total_purchase_count > 0:
                    from SendNotify import stop_capture_and_notify
                    stop_capture_and_notify("ONE插件白嫖脚本执行结果")
                else:
                    from SendNotify import _global_output_capture
                    _global_output_capture.stop_capture()
            except:
                pass

if __name__ == "__main__":
    main()
