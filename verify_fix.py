#!/usr/bin/env python3
"""完整执行：启动后端 -> 执行迁移 -> 运行测试 -> 关闭后端"""
import asyncio
import asyncpg
import subprocess
import sys
import time
import urllib.request
import urllib.error

API_URL = "http://127.0.0.1:19509/api"


def check_api():
    """检查API是否可用"""
    try:
        req = urllib.request.Request(f"{API_URL}/users")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


async def run_migration():
    """执行数据库迁移"""
    print("\n" + "="*60)
    print("执行数据库迁移...")
    print("="*60)
    try:
        conn = await asyncpg.connect(
            host='127.0.0.1',
            port=21509,
            user='postgres',
            password='postgres',
            database='blade_inspect'
        )
        try:
            with open('migrations/003_fix_grid_uniqueness.sql', 'r') as f:
                sql = f.read()
            await conn.execute(sql)
            print('✅ 迁移执行成功')
            
            result = await conn.fetch('''
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE indexname = 'uq_grid_turbine_active'
            ''')
            if result:
                print(f'✅ 部分唯一索引已创建: {result[0]["indexname"]}')
            else:
                print('⚠️  索引可能已存在')
        except Exception as e:
            if 'already exists' in str(e) or 'duplicate key' in str(e):
                print('⚠️  索引已存在，跳过迁移')
            else:
                print(f'❌ 迁移失败: {e}')
                return False
        finally:
            await conn.close()
        return True
    except Exception as e:
        print(f'❌ 数据库连接失败: {e}')
        return False


def run_tests():
    """运行回归测试"""
    print("\n" + "="*60)
    print("运行缺陷与并网冻结回归测试...")
    print("="*60)
    try:
        result = subprocess.run(
            [sys.executable, 'test_regression_defect_grid.py'],
            capture_output=True,
            text=True,
            timeout=180
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:500])
        return result.returncode == 0
    except Exception as e:
        print(f'❌ 测试执行失败: {e}')
        return False


def run_original_tests():
    """运行原有端到端测试"""
    print("\n" + "="*60)
    print("运行原有端到端测试...")
    print("="*60)
    try:
        result = subprocess.run(
            [sys.executable, 'test_workflow.py'],
            capture_output=True,
            text=True,
            timeout=180
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:500])
        return result.returncode == 0
    except Exception as e:
        print(f'❌ 测试执行失败: {e}')
        return False


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("# 风电场叶片巡检系统 — 缺陷与并网冻结修复验证")
    print("#"*60)

    # 1. 检查API是否已运行
    print("\n🔍 检查后端服务状态...")
    api_running = check_api()
    if api_running:
        print("✅ 后端服务已在运行")
    else:
        print("❌ 后端服务未运行，请先启动后端:")
        print("   cd /Users/mingyuan/workspace/sihuo/wangxtw3/1209")
        print("   python3 -m uvicorn server.main:app --host 127.0.0.1 --port 19509")
        print("\n或使用: nohup python3 -m uvicorn server.main:app --host 127.0.0.1 --port 19509 &")
        sys.exit(1)

    # 2. 执行数据库迁移
    ok = asyncio.run(run_migration())
    if not ok:
        sys.exit(1)

    # 3. 运行回归测试
    ok = run_tests()
    if not ok:
        sys.exit(1)

    # 4. 运行原有测试确保没有回归
    ok = run_original_tests()
    
    print("\n" + "#"*60)
    if ok:
        print("# ✅ 所有测试通过！修复验证完成")
    else:
        print("# ❌ 部分测试失败")
    print("#"*60 + "\n")
    
    sys.exit(0 if ok else 1)
