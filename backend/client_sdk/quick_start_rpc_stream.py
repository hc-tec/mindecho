#!/usr/bin/env python3
"""
快速开始 - RPC客户端（流式监听示例）

演示如何使用 EAIRPCClient 的 run_plugin_stream，在一次性任务执行期间持续监听同一 topic 上的多次事件，
并在收到事件后继续执行后续逻辑。
"""

import asyncio
from typing import Any, Dict

from client_sdk.params import TaskParams
from client_sdk.rpc_client_async import EAIRPCClient


async def main():
    # 创建客户端
    client = EAIRPCClient(
        base_url="http://127.0.0.1:8008",  # 服务程序 ip+port
        api_key="testkey",                 # 与服务程序约定好的 API 密钥
        webhook_host="127.0.0.1",         # Webhook 订阅服务的监听地址
        webhook_port=0,                  # Webhook 订阅服务的监听端口
    )

    try:
        # 启动客户端（启动内置 webhook server）
        await client.start()
        print("✅ RPC客户端已启动 (流式监听示例)")

        # 准备插件配置（以 yuanbao_chat 为例）
        # 注意: cookie_ids 需替换为你的账户 cookie id 列表
        ask_question = "你好，我是小星星 (stream)"
        task_params = TaskParams(
            cookie_ids=["819969a2-9e59-46f5-b0ca-df2116d9c2a0"],
        )

        # 启动插件并持续监听：
        # - run_plugin_stream 会创建一个临时 topic 并订阅到当前客户端的 webhook
        # - 任务执行过程中产生的多次发布事件都会被推送到该 topic
        # - 通过异步上下文管理器自动完成资源清理
        print("\n▶️ 启动插件并进入持续监听模式...")
        async with client.run_plugin_stream(plugin_id="yuanbao_chat",ask_question=ask_question, task_params=task_params, interval=30) as stream:
            # 使用 stream.next(timeout=60) 设置60秒超时的拉取循环
            while True:
                try:
                    event = await stream.next(timeout=60)
                except TimeoutError:
                    print("⌛ 60s内未收到事件，继续等待...")
                    continue

                event_id = event.get("event_id")
                topic_id = event.get("topic_id")
                plugin = event.get("plugin_id")
                payload = event.get("payload", {})
                print(f"\n📩 收到事件: event_id={event_id}, topic_id={topic_id}, plugin_id={plugin}")

                # 规范结构: { success: bool, result: any, error?: string }
                success = payload.get("success", True)
                result = payload.get("result")
                error = payload.get("error")

                if not success:
                    print(f"❌ 任务执行错误: {error}")
                    break

                # 任务可能多次产生结果，这里简单打印并在首个有效结果后退出示例
                if isinstance(result, dict):
                    print(f"AI回复: {result.get('data')[0].get('last_model_message', 'N/A')}")
                else:
                    # 如果没有标准 result 字段，打印原始 payload 以便调试
                    print("ℹ️ 事件payload:", payload)
                    # 根据你的业务需要决定是否继续等待或退出，这里选择退出
                    break

        print("\n✅ 持续监听结束，示例完成。")

    except Exception as e:
        print(f"❌ 错误: {e}")

    finally:
        # 停止客户端（关闭 webhook server、释放资源）
        await client.stop()
        print("\n✅ RPC客户端已停止")


if __name__ == "__main__":
    print("🚀 启动 RPC 客户端流式监听快速示例...")
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        pass