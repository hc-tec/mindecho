#!/usr/bin/env python3
"""
快速开始 - RPC客户端

最简单的使用方式，只需几行代码即可调用插件功能。
"""

import asyncio

from client_sdk.rpc_client import EAIRPCClient
from client_sdk.params import TaskParams


async def main():
    # 创建客户端
    client = EAIRPCClient(
        base_url="http://127.0.0.1:8008", # 服务程序ip+port
        api_key="testkey",  # 与服务程序约定好的API密钥
        webhook_host="127.0.0.1", # webhook订阅服务，当服务程序成功获取到client所需要的订阅数据时，就会通过webhook调用向此请求发送订阅数据
        webhook_port=0, # 随机端口
    )
    
    try:
        # 启动客户端
        await client.start()
        print("✅ RPC客户端已启动")

        # chat_result = await client.call_paddle_ocr(
        #     image_path_abs_path=r"D:\AIProject\everything-as-an-interface-apps\favorites_collect_and_process_with_ai_web\data\images\68a6a594000000001b03514e\1040g3k031ledqb3c5o0g5ohf2g8ocft9qm56a38!nd_dft_wlteh_webp_3.webp",
        #     task_params=TaskParams(
        #         cookie_ids=[],
        #         close_page_when_task_finished=True,
        #     ),
        # )

        chat_result = await client.get_collection_list_from_bilibili(
            task_params=TaskParams(
                cookie_ids=["23d87982-a801-4d12-ae93-50a85e336e98"],
                close_page_when_task_finished=True,
            ),
        )
        print(chat_result)
        
        # 🤖 与AI聊天
        # print("\n🤖 与AI元宝聊天...")
        # chat_result = await client.chat_with_yuanbao(
        #     ask_question="你好，我是小星星",
        #     conversation_id=None,
        #     task_params=TaskParams(
        #         cookie_ids=["819969a2-9e59-46f5-b0ca-df2116d9c2a0"],
        #         close_page_when_task_finished=True,
        #     ),
        # )
        # if chat_result["success"]:
        #     print(f"AI回复: {chat_result.get('data')[0].get('last_model_message', 'N/A')}")
        # else:
        #     print(chat_result["error"])
        # chat_result = await client.get_favorite_notes_brief_from_xhs(
        #     storage_file="data/note-brief-rpc.json",
        #     max_items=10,
        #     cookie_ids=["28ba44f1-bb67-41ab-86f0-a3d049d902aa"]
        # )
        # print(f"AI回复: {chat_result.get('data', 'N/A')}")
        
        # # 📱 获取小红书笔记
        # print("\n📱 获取小红书美食笔记...")
        # notes = await client_sdk.get_favorite_notes_brief_from_xhs(
        #     keywords=["美食", "推荐"],
        #     max_items=5
        # )
        # print(f"获取到 {len(notes.get('items', []))} 条笔记")
        #
        # # 打印前3条笔记标题
        # for i, note in enumerate(notes.get('items', [])[:3]):
        #     print(f"  {i+1}. {note.get('title', 'N/A')}")
        #
        # # 🔍 搜索小红书内容
        # print("\n🔍 搜索小红书咖啡内容...")
        # search_result = await client_sdk.search_notes_from_xhs(
        #     keywords=["咖啡", "拿铁"],
        #     max_items=3
        # )
        # print(f"搜索到 {len(search_result.get('items', []))} 条相关内容")
        
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
    