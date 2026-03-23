"""云雀简报 — 主入口：串联爬取 → 总结 → 组装 → 保存"""

import asyncio


async def generate_daily_brief():
    """生成每日简报的完整流程"""
    # TODO: 实现完整流程
    # 1. 加载配置
    # 2. 并发爬取
    # 3. LLM 总结
    # 4. 组装简报
    # 5. 保存文件
    raise NotImplementedError


def main():
    """CLI 入口"""
    asyncio.run(generate_daily_brief())


if __name__ == "__main__":
    main()
