# ac_automaton.py
import json
import ahocorasick
import jsonlines
from typing import List, Dict, Any

class ACEntityMatcher:
    def __init__(self, entities_file: str):
        """
        初始化AC自动机实体匹配器
        
        Args:
            entities_file: 包含实体信息的JSON文件路径
        """
        self.entities_file = entities_file
        self.automaton = ahocorasick.Automaton()
        self.entity_dict = {}
        self._build_automaton()
    
    def _build_automaton(self):
        """构建AC自动机"""
        # 读取实体数据
        with open(self.entities_file, 'r', encoding='utf-8') as f:
            entities = json.load(f)
        
        # 将实体添加到自动机中
        for entity in entities:
            entity_name = entity["entity_name"]
            self.automaton.add_word(entity_name, entity)
            self.entity_dict[entity_name] = entity
        
        # 构建自动机
        self.automaton.make_automaton()
        print(f"已加载 {len(self.entity_dict)} 个实体到AC自动机中")
    
    def match_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        在文本中匹配实体
        
        Args:
            text: 输入文本
            
        Returns:
            匹配到的实体列表
        """
        matched_entities = []
        matched_names = set()
        
        # 使用AC自动机匹配实体
        for end_index, entity in self.automaton.iter(text):
            entity_name = entity["entity_name"]
            if entity_name not in matched_names:
                matched_entities.append(entity)
                matched_names.add(entity_name)
        
        return matched_entities
    
    def match_entities_with_context(self, text: str, max_entities: int = 15) -> str:
        """
        匹配实体并格式化为上下文字符串
        
        Args:
            text: 输入文本
            max_entities: 最大返回实体数
            
        Returns:
            格式化的实体字符串
        """
        matched_entities = self.match_entities(text)
        
        # 限制实体数量
        if len(matched_entities) > max_entities:
            matched_entities = matched_entities[:max_entities]
        
        # 格式化为字符串
        if not matched_entities:
            return "未找到相关实体"
        
        entity_list_str = "\n".join([
            f"- {entity['entity_name']} ({', '.join(entity['type'][:3])}): {entity['summary'][:100]}..." 
            for entity in matched_entities
        ])
        
        return entity_list_str
    
    def get_entity_stats(self) -> Dict[str, Any]:
        """
        获取实体统计信息
        
        Returns:
            实体统计信息
        """
        type_count = {}
        chunk_count = 0
        
        for entity in self.entity_dict.values():
            # 统计实体类型
            for entity_type in entity.get("type", []):
                type_count[entity_type] = type_count.get(entity_type, 0) + 1
            
            # 统计涉及的chunk数量
            chunk_count += len(entity.get("chunk_ids", []))
        
        return {
            "total_entities": len(self.entity_dict),
            "type_distribution": type_count,
            "total_chunk_references": chunk_count
        }

def test_entity_matching_with_relation_chunk():
    """使用relation_chunks中的第一个chunk进行实体匹配测试"""
    # 初始化匹配器
    matcher = ACEntityMatcher("./kg_output/entities_kb.json")
    
    # 读取relation_chunks.jsonl中的第一个chunk
    with jsonlines.open("./chunks_output/relation_chunks.jsonl", mode='r') as reader:
        for chunk in reader:
            first_chunk = chunk
            break
    
    test_text = first_chunk["chunk_content"]
    print("=== 使用relation_chunks中的第一个chunk进行实体匹配测试 ===")
    print(f"文本来源: {first_chunk['source']}")
    print(f"Chunk ID: {first_chunk['metadata']}")
    print("\n测试文本内容:")
    print("-" * 50)
    print(test_text[:500] + "..." if len(test_text) > 500 else test_text)
    print("-" * 50)
    
    # 打印统计信息
    stats = matcher.get_entity_stats()
    print(f"\n实体库统计信息:")
    print(f"  总实体数: {stats['total_entities']}")
    print(f"  总引用chunk数: {stats['total_chunk_references']}")
    
    # 匹配实体
    print("\n实体匹配结果:")
    print("=" * 50)
    matched_entities = matcher.match_entities(test_text)
    print(f"匹配到 {len(matched_entities)} 个实体:")
    
    for i, entity in enumerate(matched_entities, 1):
        print(f"\n{i}. 实体: {entity['entity_name']}")
        print(f"   类型: {', '.join(entity['type'][:5])}")
        print(f"   摘要: {entity['summary'][:150]}...")
        print(f"   来源chunks: {entity['chunk_ids'][:10]}{'...' if len(entity['chunk_ids']) > 10 else ''}")
    
    # 显示格式化结果
    print("\n格式化结果 (用于大模型上下文):")
    print("=" * 50)
    formatted_result = matcher.match_entities_with_context(test_text, max_entities=20)
    print(formatted_result)
    
    return matched_entities

def interactive_test():
    """交互式测试"""
    matcher = ACEntityMatcher("./kg_output/entities_kb.json")
    
    print("\n=== 交互式实体匹配测试 ===")
    print("输入文本进行实体匹配测试，输入 'quit' 退出")
    
    while True:
        user_input = input("\n请输入测试文本: ").strip()
        if user_input.lower() == 'quit':
            break
        
        if not user_input:
            continue
            
        print("\n匹配结果:")
        print("-" * 30)
        result = matcher.match_entities_with_context(user_input)
        print(result)

if __name__ == "__main__":
    # 运行测试
    matched_entities = test_entity_matching_with_relation_chunk()
    
    # 如果需要交互式测试，取消下面的注释
    # interactive_test()