import os
import json
from typing import Dict, List, Any

def merge_entity_knowledge_base(input_dir: str, output_file: str) -> Dict[str, Any]:
    """
    合并多个实体文件，构建统一的实体知识库
    
    Args:
        input_dir: 包含实体JSON文件的目录
        output_file: 输出合并后的知识库文件路径
        
    Returns:
        合并后的实体知识库字典
    """
    
    # 初始化实体知识库
    entity_kb: Dict[str, Dict[str, Any]] = {}
    
    # 遍历目录中的所有JSON文件
    for filename in os.listdir(input_dir):
        if filename.startswith("entities_") and filename.endswith(".json"):
            file_path = os.path.join(input_dir, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    entities = json.load(f)
                
                # 处理每个实体
                for ent in entities:
                    key = ent["entity_name"]
                    
                    if key in entity_kb:
                        # 合并实体类型
                        for type_item in ent.get("type", []):
                            if type_item not in entity_kb[key]["type"]:
                                entity_kb[key]["type"].append(type_item)
                        
                        # 合并领域相关性 (新增)
                        for relevance in ent.get("domain_relevance", []):
                            if relevance not in entity_kb[key]["domain_relevance"]:
                                entity_kb[key]["domain_relevance"].append(relevance)
                        
                        # 合并摘要信息
                        old_summary = entity_kb[key]["summary"]
                        new_summary = ent["summary"]
                        if old_summary != new_summary:
                            entity_kb[key]["summary"] = f"{old_summary} | {new_summary}".strip()
                        
                        # 合并chunk_ids
                        for chunk_id in ent.get("chunk_ids", []):
                            if chunk_id not in entity_kb[key]["chunk_ids"]:
                                entity_kb[key]["chunk_ids"].append(chunk_id)
                    else:
                        # 新增实体
                        entity_kb[key] = {
                            "entity_name": ent["entity_name"],
                            "type": ent["type"][:], 
                            "domain_relevance": ent.get("domain_relevance", [])[:],
                            "summary": ent["summary"],
                            "chunk_ids": ent.get("chunk_ids", [])[:]
                        }
                        
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")
                continue
    
    # 转换为列表格式
    final_entities = list(entity_kb.values())
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_entities, f, ensure_ascii=False, indent=4)
    
    print(f"合并完成，共处理 {len(final_entities)} 个唯一实体")
    print(f"结果已保存至: {output_file}")
    
    return entity_kb

def query_entity(entity_kb: Dict[str, Dict[str, Any]], entity_name: str) -> Dict[str, Any]:
    """
    查询特定实体的信息
    
    Args:
        entity_kb: 实体知识库
        entity_name: 实体名称
        
    Returns:
        实体信息字典，如果未找到则返回空字典
    """
    return entity_kb.get(entity_name, {})

# 使用示例
if __name__ == "__main__":
    # 合并所有实体文件
    input_directory = "./entities_output"
    output_file = "./kg_output/entities_kb.json"
    
    # 构建实体知识库
    entity_knowledge_base = merge_entity_knowledge_base(input_directory, output_file)
    
    # 示例查询
    test_entities = ["水"]
    
    for entity_name in test_entities:
        entity_info = query_entity(entity_knowledge_base, entity_name)
        if entity_info:
            print(f"\n实体名称: {entity_info['entity_name']}")
            print(f"类型: {entity_info['type']}")
            print(f"领域相关性: {entity_info['domain_relevance']}") 
            print(f"摘要: {entity_info['summary']}")
            print(f"来源chunk IDs: {entity_info['chunk_ids']}")
        else:
            print(f"未找到实体: {entity_name}")