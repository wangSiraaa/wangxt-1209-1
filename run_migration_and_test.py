#!/usr/bin/env python3
"""执行数据库迁移 + 运行回归测试"""
import asyncio
import asyncpg
import subprocess
import sys

async def run_migration():
    print("="*60)
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
                print('⚠️  索引可能已存在，跳过')
        except Exception as e:
            if 'already exists' in str(e):
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

def run_regression_test():
    print("\n" + "="*60)
    print("运行回归测试...")
    print("="*60)
    try:
        result = subprocess.run(
            [sys.executable, 'test_regression_defect_grid.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f'❌ 测试执行失败: {e}')
        return False

if __name__ == "__main__":
    ok = asyncio.run(run_migration())
    if ok:
        ok = run_regression_test()
    sys.exit(0 if ok else 1)
