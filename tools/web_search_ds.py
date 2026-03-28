import json
import os
from tavily import TavilyClient

def get_tavily_key() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_dir = os.path.dirname(base_dir)
    config_path = os.path.join(cfg_dir, "config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        return config.get("api_keys", {}).get("tavily")
    
def get_max_result_count() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_dir = os.path.dirname(base_dir)
    config_path = os.path.join(cfg_dir, "config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        return int(config.get("settings", {}).get("max_result_count_ds", 3))

def search_web(queries: list[str]) -> dict:
    if isinstance(queries, str):
        queries = [queries]
    tavily_client = TavilyClient(api_key=get_tavily_key())
    all_results_str = ""
    extracted_sources = []

    for q in queries:
        try:
            # 限制单次搜索条数，避免多个词加起来导致 Token 爆炸
            response = tavily_client.search(query=q, max_results=int(get_max_result_count())) 
            
            all_results_str += f"【搜索词：{q} 的结果】\n"
            for item in response.get("results", []):
                all_results_str += f"标题: {item['title']}\n内容: {item['content']}\n\n"
                extracted_sources.append(f"[{item['title']}]({item['url']})")

        except Exception as e:
            all_results_str += f"【搜索词：{q} 的结果】搜索失败: {str(e)}\n\n"
            
    return {
        "results": all_results_str if all_results_str.strip() else "本次工具调用失败或未搜索到相关结果。",
        "sources": extracted_sources
    }

web_search_tool_schema = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "当且仅当需要获取或用户显式要求你获取实时信息、新闻、或你不知道的外部知识时，调用此工具进行联网搜索。",
        "parameters": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "单个搜索关键词或句子，用于搜索引擎查询"
                    },
                    "description": "用于在搜索引擎中查询的关键词或完整句子的列表，支持多个查询项组成的列表，工具会依次处理每个查询项并返回结果"
                }
            },
            "required": ["queries"]
        }
    }
}