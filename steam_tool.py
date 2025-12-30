"""
Steam 评论获取工具
用于获取 Steam 游戏的用户评论
"""
import requests
import time
from typing import Optional, Dict
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from config import config as app_config
from logger import logger


class SteamReviewsInput(BaseModel):
    """Steam 评论工具的输入参数"""
    game_name: str = Field(description="游戏名称，例如：'CS2', 'Dota 2', 'Cyberpunk 2077'")
    num_reviews: int = Field(
        default=app_config.STEAM_NUM_REVIEWS,
        description=f"要获取的评论数量，默认 {app_config.STEAM_NUM_REVIEWS} 条，最多 {app_config.STEAM_MAX_REVIEWS} 条"
    )


class SteamReviewsTool(BaseTool):
    """获取 Steam 游戏评论的工具"""
    
    name: str = "steam_reviews"
    description: str = f"""
    获取 Steam 游戏的用户评论和评价。
    当用户询问关于游戏评价、玩家反馈、游戏口碑、Steam评分时使用。
    输入游戏名称和评论数量（可选，默认{app_config.STEAM_NUM_REVIEWS}条，最多{app_config.STEAM_MAX_REVIEWS}条），返回最新的用户评论和总体评价。
    支持获取大量评论，可以看到更全面的玩家反馈。
    评论语言：{app_config.STEAM_LANGUAGE}，筛选方式：{app_config.STEAM_FILTER}
    """
    args_schema: type[BaseModel] = SteamReviewsInput
    
    def _search_game(self, game_name: str) -> Optional[int]:
        """
        搜索游戏并获取 AppID
        
        Args:
            game_name: 游戏名称
            
        Returns:
            游戏的 AppID，如果未找到则返回 None
        """
        try:
            # 使用 Steam 搜索 API
            search_url = "https://store.steampowered.com/api/storesearch/"
            params = {
                'term': game_name,
                'cc': 'cn',  # 中国区
                'l': 'schinese'  # 简体中文
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('total', 0) > 0 and data.get('items'):
                # 返回第一个匹配的游戏 ID
                return data['items'][0]['id']
            
            return None
        except Exception as e:
            logger.error(f"搜索游戏失败: {e}")
            return None
    
    def _get_reviews(self, app_id: int, num_reviews: int = None) -> Dict:
        """
        获取游戏评论（支持分页获取更多评论）
        
        Args:
            app_id: 游戏的 AppID
            num_reviews: 要获取的评论数量（最多 100 条）
            
        Returns:
            评论数据字典，包含合并后的多页评论
        """
        try:
            # 限制最大数量
            max_reviews = app_config.STEAM_MAX_REVIEWS
            num_reviews = min(num_reviews, max_reviews)
            
            all_reviews = []
            cursor = "*"  # Steam API 的分页游标，* 表示第一页
            per_page = 20  # 每页最多 20 条（Steam API 限制）
            
            # 计算需要请求的页数
            pages_needed = (num_reviews + per_page - 1) // per_page
            
            logger.log(f"正在获取 {num_reviews} 条评论，需要 {pages_needed} 页...")
            
            for page in range(pages_needed):
                # 从第二页开始添加延时，避免触发速率限制
                if page > 0:
                    delay = app_config.STEAM_REQUEST_DELAY
                    logger.log(f"等待 {delay} 秒后请求第 {page + 1} 页...")
                    time.sleep(delay)
                
                # Steam 评论 API
                reviews_url = f"https://store.steampowered.com/appreviews/{app_id}"
                params = {
                    'json': 1,
                    'language': app_config.STEAM_LANGUAGE,  # 从配置读取语言
                    'num_per_page': per_page,
                    'cursor': cursor,
                    'purchase_type': 'all',
                    'filter': app_config.STEAM_FILTER  # 从配置读取筛选方式
                }
                
                response = requests.get(reviews_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # 获取当前页的评论
                reviews = data.get('reviews', [])
                if not reviews:
                    break  # 没有更多评论了
                
                all_reviews.extend(reviews)
                
                # 检查是否已经获取足够的评论
                if len(all_reviews) >= num_reviews:
                    break
                
                # 获取下一页的游标
                cursor = data.get('cursor', '')
                if not cursor or cursor == '*':
                    break  # 没有下一页了
            
            # 返回合并后的数据
            return {
                'reviews': all_reviews[:num_reviews],  # 截取到指定数量
                'query_summary': data.get('query_summary', {})
            }
            
        except Exception as e:
            logger.error(f"获取评论失败: {e}")
            return {}
    
    def _format_reviews(self, reviews_data: Dict, game_name: str) -> str:
        """
        格式化评论数据
        
        Args:
            reviews_data: 原始评论数据
            game_name: 游戏名称
            
        Returns:
            格式化后的评论文本
        """
        if not reviews_data or 'reviews' not in reviews_data:
            return f"未能找到《{game_name}》的评论数据。"
        
        reviews = reviews_data.get('reviews', [])
        if not reviews:
            return f"《{game_name}》暂无评论。"
        
        # 获取总体评价统计
        query_summary = reviews_data.get('query_summary', {})
        total_positive = query_summary.get('total_positive', 0)
        total_negative = query_summary.get('total_negative', 0)
        total_reviews = query_summary.get('total_reviews', 0)
        
        # 计算好评率
        positive_rate = 0
        if total_reviews > 0:
            positive_rate = (total_positive / total_reviews) * 100
        
        # 构建输出
        result = f"《{game_name}》Steam 评价分析\n\n"
        result += f"📊 总体评价：\n"
        result += f"- 总评论数：{total_reviews:,} 条\n"
        result += f"- 好评：{total_positive:,} 条 ({positive_rate:.1f}%)\n"
        result += f"- 差评：{total_negative:,} 条\n\n"
        
        result += f"💬 最新玩家评论（{len(reviews)} 条）：\n\n"
        
        # 显示所有获取的评论
        for i, review in enumerate(reviews, 1):
            # 评价类型
            is_positive = review.get('voted_up', False)
            vote_emoji = "👍" if is_positive else "👎"
            
            # 游戏时长
            playtime_hours = review.get('author', {}).get('playtime_forever', 0) / 60
            
            # 评论内容
            comment = review.get('review', '').strip()
            # 限制长度
            if len(comment) > 200:
                comment = comment[:200] + "..."
            
            result += f"{i}. {vote_emoji} {'推荐' if is_positive else '不推荐'}\n"
            result += f"   游戏时长：{playtime_hours:.1f} 小时\n"
            result += f"   评论：{comment}\n\n"
        
        return result
    
    def _run(self, game_name: str, num_reviews: int = None) -> str:
        """
        执行工具：获取 Steam 游戏评论
        
        Args:
            game_name: 游戏名称
            num_reviews: 要获取的评论数量
            
        Returns:
            格式化的评论文本
        """
        # 1. 搜索游戏获取 AppID
        app_id = self._search_game(game_name)
        if not app_id:
            return f"未找到游戏《{game_name}》，请检查游戏名称是否正确。"
        
        # 2. 获取评论
        reviews_data = self._get_reviews(app_id, num_reviews)
        
        # 3. 格式化并返回
        return self._format_reviews(reviews_data, game_name)
    
    async def _arun(self, game_name: str, num_reviews: int = None) -> str:
        """异步执行（暂时使用同步实现）"""
        return self._run(game_name, num_reviews)


# 创建工具实例的便捷函数
def create_steam_reviews_tool() -> SteamReviewsTool:
    """创建 Steam 评论工具实例"""
    return SteamReviewsTool()


# 测试代码
if __name__ == "__main__":
    import sys
    import io
    
    # 设置输出编码为 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    tool = create_steam_reviews_tool()
    
    # 测试搜索游戏
    logger.log("测试 1: 搜索《CS2》...")
    result = tool._run("CS2", num_reviews=3)
    logger.log(result)
    
    logger.separator()
    
    # 测试另一个游戏
    logger.log("测试 2: 搜索《Dota 2》...")
    result = tool._run("Dota 2", num_reviews=3)
    logger.log(result)
