"""
测试收藏列表的搜索功能

测试场景：
1. 基本搜索 - 按关键词搜索标题和简介
2. 搜索 + 排序
3. 搜索 + 标签筛选
4. 搜索 + 分页
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.crud import crud_favorites
from app.schemas.unified import FavoriteItemCreate


@pytest.fixture
async def setup_test_items(db_session: AsyncSession):
    """创建测试数据"""
    # 创建测试作者
    author = models.Author(
        platform=models.PlatformEnum.BILIBILI,
        platform_user_id="test_user_001",
        username="测试作者"
    )
    db_session.add(author)
    await db_session.flush()

    # 创建测试收藏项
    test_items = [
        {
            "title": "深度学习入门教程",
            "intro": "这是一个关于 AI 和深度学习的入门教程",
            "platform": models.PlatformEnum.BILIBILI,
            "platform_item_id": "BV1test001",
        },
        {
            "title": "产品设计思维",
            "intro": "学习如何设计优秀的产品",
            "platform": models.PlatformEnum.BILIBILI,
            "platform_item_id": "BV1test002",
        },
        {
            "title": "AI 大模型应用实战",
            "intro": "使用 GPT-4 和 Claude 构建应用",
            "platform": models.PlatformEnum.BILIBILI,
            "platform_item_id": "BV1test003",
        },
        {
            "title": "Python 编程进阶",
            "intro": "深入理解 Python 高级特性",
            "platform": models.PlatformEnum.BILIBILI,
            "platform_item_id": "BV1test004",
        },
    ]

    created_items = []
    for item_data in test_items:
        db_item = models.FavoriteItem(
            **item_data,
            author_id=author.id,
            status=models.FavoriteItemStatus.PENDING
        )
        db_session.add(db_item)
        created_items.append(db_item)

    await db_session.commit()
    return created_items


@pytest.mark.asyncio
async def test_search_by_title(client: AsyncClient, setup_test_items):
    """测试按标题搜索"""
    response = await client.get(
        "/api/v1/collections",
        params={"page": 1, "size": 10, "q": "AI"}
    )

    assert response.status_code == 200
    data = response.json()

    # 应该找到包含 "AI" 的两条记录
    assert data["total"] >= 2

    # 验证返回的结果包含 "AI" 关键词
    for item in data["items"]:
        title_lower = item["title"].lower()
        intro_lower = item.get("intro", "").lower()
        assert "ai" in title_lower or "ai" in intro_lower


@pytest.mark.asyncio
async def test_search_by_intro(client: AsyncClient, setup_test_items):
    """测试按简介搜索"""
    response = await client.get(
        "/api/v1/collections",
        params={"page": 1, "size": 10, "q": "产品"}
    )

    assert response.status_code == 200
    data = response.json()

    # 应该找到至少一条记录
    assert data["total"] >= 1
    assert any("产品" in item.get("intro", "") or "产品" in item["title"] for item in data["items"])


@pytest.mark.asyncio
async def test_search_case_insensitive(client: AsyncClient, setup_test_items):
    """测试大小写不敏感搜索"""
    # 使用小写搜索
    response_lower = await client.get(
        "/api/v1/collections",
        params={"page": 1, "size": 10, "q": "python"}
    )

    # 使用大写搜索
    response_upper = await client.get(
        "/api/v1/collections",
        params={"page": 1, "size": 10, "q": "PYTHON"}
    )

    assert response_lower.status_code == 200
    assert response_upper.status_code == 200

    # 两次搜索应该返回相同的结果数
    assert response_lower.json()["total"] == response_upper.json()["total"]


@pytest.mark.asyncio
async def test_search_with_sorting(client: AsyncClient, setup_test_items):
    """测试搜索 + 排序"""
    response = await client.get(
        "/api/v1/collections",
        params={
            "page": 1,
            "size": 10,
            "q": "学习",
            "sort_by": "title",
            "sort_order": "asc"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # 验证结果按标题升序排列
    if len(data["items"]) > 1:
        titles = [item["title"] for item in data["items"]]
        assert titles == sorted(titles)


@pytest.mark.asyncio
async def test_search_with_pagination(client: AsyncClient, setup_test_items):
    """测试搜索 + 分页"""
    # 第一页
    response_page1 = await client.get(
        "/api/v1/collections",
        params={"page": 1, "size": 2, "q": "学习"}
    )

    assert response_page1.status_code == 200
    data_page1 = response_page1.json()

    # 验证分页参数生效
    assert len(data_page1["items"]) <= 2

    # 如果有多于2条结果，验证第二页
    if data_page1["total"] > 2:
        response_page2 = await client.get(
            "/api/v1/collections",
            params={"page": 2, "size": 2, "q": "学习"}
        )
        assert response_page2.status_code == 200
        data_page2 = response_page2.json()

        # 第二页的结果应该与第一页不同
        page1_ids = {item["id"] for item in data_page1["items"]}
        page2_ids = {item["id"] for item in data_page2["items"]}
        assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_search_no_results(client: AsyncClient, setup_test_items):
    """测试搜索无结果的情况"""
    response = await client.get(
        "/api/v1/collections",
        params={"page": 1, "size": 10, "q": "不存在的关键词xyz123"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_search_empty_query(client: AsyncClient, setup_test_items):
    """测试空搜索关键词（应返回所有结果）"""
    # 不传 q 参数
    response_no_q = await client.get(
        "/api/v1/collections",
        params={"page": 1, "size": 10}
    )

    # 传空字符串
    response_empty_q = await client.get(
        "/api/v1/collections",
        params={"page": 1, "size": 10, "q": ""}
    )

    assert response_no_q.status_code == 200
    assert response_empty_q.status_code == 200

    # 两次请求应该返回所有测试数据
    data_no_q = response_no_q.json()
    data_empty_q = response_empty_q.json()

    assert data_no_q["total"] >= 4  # 我们创建了4条测试数据
    assert data_empty_q["total"] == data_no_q["total"]


@pytest.mark.asyncio
async def test_search_partial_match(client: AsyncClient, setup_test_items):
    """测试部分匹配（模糊搜索）"""
    response = await client.get(
        "/api/v1/collections",
        params={"page": 1, "size": 10, "q": "深度"}
    )

    assert response.status_code == 200
    data = response.json()

    # 应该找到包含 "深度" 的记录
    assert data["total"] >= 1

    # 验证模糊匹配生效
    found = False
    for item in data["items"]:
        if "深度" in item["title"] or "深度" in item.get("intro", ""):
            found = True
            break
    assert found
