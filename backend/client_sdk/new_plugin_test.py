#!/usr/bin/env python3
"""
快速开始 - RPC客户端

最简单的使用方式，只需几行代码即可调用插件功能。
"""

import asyncio

from client_sdk.rpc_client import EAIRPCClient
from client_sdk.params import TaskParams, ServiceParams


async def main():
    # 创建客户端
    client = EAIRPCClient(
        base_url="http://127.0.0.1:9000", # 服务程序ip+port
        api_key="testkey",  # 与服务程序约定好的API密钥
        webhook_host="127.0.0.1", # webhook订阅服务，当服务程序成功获取到client所需要的订阅数据时，就会通过webhook调用向此请求发送订阅数据
        webhook_port=0, # 随机端口
    )
    
    try:
        # 启动客户端
        await client.start()
        print("✅ RPC客户端已启动")

        # chat_result = await client.get_collection_list_from_bilibili(
        #     task_params=TaskParams(
        #         cookie_ids=["23d87982-a801-4d12-ae93-50a85e336e98"],
        #         close_page_when_task_finished=False,
        #     ),
        # )
        # print(chat_result)

        chat_result = await client.get_video_details_from_bilibili(
            bvid="BV1EMhqzhE2T",
            task_params=TaskParams(
                cookie_ids=["23d87982-a801-4d12-ae93-50a85e336e98"],
                close_page_when_task_finished=False,
            ),
            service_params=ServiceParams(
                need_raw_data=True
            )
        )

        print(chat_result)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    finally:
        # 停止客户端
        await client.stop()
        print("\n✅ RPC客户端已停止")


if __name__ == "__main__":
    print("🚀 启动RPC客户端快速示例...")
    try:
        asyncio.run(main())
    except asyncio.CancelledError as e:
        pass
    