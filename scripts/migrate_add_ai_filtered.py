"""
数据库迁移脚本：添加 is_ai_filtered 字段和 ai_filter_config 表

运行方式：python scripts/migrate_add_ai_filtered.py
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.models.database import async_engine


async def migrate():
    """执行数据库迁移"""
    async with async_engine.begin() as conn:
        # 检查 is_ai_filtered 字段是否已存在
        result = await conn.execute(
            text("PRAGMA table_info(articles)")
        )
        columns = [row[1] for row in result.fetchall()]
        
        if 'is_ai_filtered' not in columns:
            print("添加 is_ai_filtered 字段到 articles 表...")
            await conn.execute(
                text("ALTER TABLE articles ADD COLUMN is_ai_filtered BOOLEAN DEFAULT 0")
            )
            print("[OK] is_ai_filtered 字段添加成功")
        else:
            print("[OK] is_ai_filtered 字段已存在，跳过")
        
        # 检查 ai_filter_config 表是否存在
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_filter_config'")
        )
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("创建 ai_filter_config 表...")
            await conn.execute(
                text("""
                    CREATE TABLE ai_filter_config (
                        id INTEGER PRIMARY KEY,
                        enabled BOOLEAN DEFAULT 0,
                        filter_prompt TEXT,
                        auto_apply BOOLEAN DEFAULT 1,
                        last_run VARCHAR(50)
                    )
                """)
            )
            print("[OK] ai_filter_config 表创建成功")
        else:
            print("[OK] ai_filter_config 表已存在，跳过")
    
    print("\n迁移完成！")


if __name__ == "__main__":
    asyncio.run(migrate())
