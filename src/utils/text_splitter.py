# 分片处理工具
import re
import json
from src.utils.logger import logger

class TextSplitter:
    """文本分片处理工具"""

    def __init__(self, max_tokens=150000):
        """
        初始化分片器
        
        Args:
            max_tokens: 最大token数（保守设置为150000，小于MiniMax的204800上限）
        """
        # 保守估计：1 token ≈ 2-3 中文字符
        self.max_chars = max_tokens * 2  # 保守估计，实际可以更大
        self.min_chunk_size = 5000  # 最小分片大小

    def split_text(self, text):
        """
        将文本分割成多个分片
        
        Args:
            text: 原始文本
            
        Returns:
            list: 分片列表
        """
        if not text:
            return []

        if len(text) <= self.max_chars:
            return [text]

        chunks = []
        current_pos = 0
        text_length = len(text)

        while current_pos < text_length:
            # 计算当前分片的结束位置
            end_pos = min(current_pos + self.max_chars, text_length)
            
            # 尝试在段落边界分割
            if end_pos < text_length:
                # 找到最近的段落结束
                newline_pos = text.rfind('\n', current_pos, end_pos)
                if newline_pos > current_pos + self.max_chars // 2:
                    end_pos = newline_pos + 1
                else:
                    # 找到最近的句子结束
                    sentence_end = text.rfind('。', current_pos, end_pos)
                    if sentence_end > current_pos + self.max_chars // 2:
                        end_pos = sentence_end + 1
                    elif text.rfind('！', current_pos, end_pos) > current_pos + self.max_chars // 2:
                        end_pos = text.rfind('！', current_pos, end_pos) + 1
                    elif text.rfind('？', current_pos, end_pos) > current_pos + self.max_chars // 2:
                        end_pos = text.rfind('？', current_pos, end_pos) + 1
            
            chunk = text[current_pos:end_pos]
            chunks.append(chunk)
            current_pos = end_pos

        return chunks

    def merge_results(self, results):
        """
        合并多个分片的处理结果
        
        Args:
            results: 分片处理结果列表
            
        Returns:
            dict: 合并后的结果
        """
        if not results:
            return {}

        # 合并JSON格式的结果
        merged_knowledge = []
        
        for result in results:
            if not result:
                continue
            
            try:
                # 尝试解析为JSON
                if isinstance(result, str):
                    # 提取JSON部分
                    if '```json' in result:
                        json_start = result.find('```json') + 7
                        json_end = result.find('```', json_start)
                        if json_end > json_start:
                            json_str = result[json_start:json_end]
                        else:
                            json_str = result
                    else:
                        json_str = result
                    
                    # 清理JSON字符串
                    json_str = json_str.strip()
                    
                    if not json_str:
                        continue
                    
                    data = json.loads(json_str)
                else:
                    data = result
                
                if isinstance(data, list):
                    merged_knowledge.extend(data)
                elif isinstance(data, dict):
                    if 'knowledge_points' in data:
                        if isinstance(data['knowledge_points'], list):
                            merged_knowledge.extend(data['knowledge_points'])
                        else:
                            merged_knowledge.append(data['knowledge_points'])
                    elif 'topics' in data:
                        if isinstance(data['topics'], list):
                            merged_knowledge.extend(data['topics'])
                        else:
                            merged_knowledge.append(data['topics'])
                    else:
                        # 未知格式，尝试作为单个知识点
                        merged_knowledge.append(data)
                else:
                    # 未知格式，尝试作为单个知识点
                    merged_knowledge.append(data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"解析结果失败: {e}")
                # 非JSON格式，作为文本处理
                merged_knowledge.append({'text': result})

        # 去重
        seen = set()
        unique_knowledge = []
        for item in merged_knowledge:
            if isinstance(item, dict):
                key_parts = []
                for field in ['name', 'text', 'content', 'chapter']:
                    if field in item:
                        key_parts.append(str(item[field]))
                key = ''.join(key_parts)
            else:
                key = str(item)
            
            if key not in seen and key.strip():
                seen.add(key)
                unique_knowledge.append(item)

        return {
            'knowledge_points': unique_knowledge,
            'total_points': len(unique_knowledge)
        }