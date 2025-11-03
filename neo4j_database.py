"""
连接neo4j数据库示例
"""

# # main.py
# import os
# from dotenv import load_dotenv
# from neo4j import GraphDatabase

# # 加载 .env 文件中的环境变量
# load_dotenv()

# # 从环境变量中读取配置
# URI = os.getenv("NEO4J_URI")
# PASSWORD = os.getenv("NEO4J_PASSWORD")
# AUTH = ("neo4j", PASSWORD)  # Aura 用户名固定为 "neo4j"

# # 验证是否加载成功
# if not URI or not PASSWORD:
#     raise ValueError("请确保 .env 文件中设置了 NEO4J_URI 和 NEO4J_PASSWORD")

# # 连接 Neo4j Aura
# driver = GraphDatabase.driver(URI, auth=AUTH)

# # 测试连接
# with driver.session() as session:
#     result = session.run("RETURN 'Connected via .env!' AS message")
#     print(result.single()["message"])

# driver.close()

"""
知识图谱数据处理与Neo4j导入工具
功能包括：
1. 导入实体和三元组JSON文件
2. 扩充实体库，将三元组中出现但实体库中未包含的实体按实体库格式重构
3. 转换为CSV格式并保存
4. 导入到Neo4j数据库
"""

import pandas as pd
import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging
from typing import List, Dict, Any
import re

# 加载环境变量
load_dotenv()

import pandas as pd
import re

class Neo4jLabelCleaner:
    """Neo4j标签清理器 - 提取第一个中文短语作为LABEL"""
    
    def __init__(self):
        pass
    
    def clean_file(self, input_file, output_file):
        """清理标签，提取第一个中文短语"""
        df = pd.read_csv(input_file)
        
        if ':LABEL' in df.columns:
            # 清理标签并提取第一个中文短语
            df[':LABEL'] = df[':LABEL'].apply(self._extract_first_chinese_phrase)
        
        # 保存文件
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"文件已保存: {output_file}")
        
        return df
    
    def _extract_first_chinese_phrase(self, label):
        """提取第一个中文短语作为LABEL"""
        if pd.isna(label):
            return 'Unknown'
        
        label_str = str(label)
        
        # 1. 移除Entity;前缀
        cleaned = re.sub(r'^Entity;', '', label_str)
        
        # 2. 提取|分割的第一个部分
        if '|' in cleaned:
            first_part = cleaned.split('|')[0].strip()
        else:
            first_part = cleaned
        
        # 3. 提取第一个连续的中文字符串
        chinese_match = re.search(r'[\u4e00-\u9fff]+', first_part)
        if chinese_match:
            return chinese_match.group()
        else:
            # 如果没有中文，返回整个第一部分（去除多余符号）
            return re.sub(r'[^\w\u4e00-\u9fff]', '', first_part)
    
    def _validate_cleaning(self, df):
        """验证清理结果"""
        if ':LABEL' in df.columns:
            print("清理后的标签分布:")
            print(df[':LABEL'].value_counts())

class KnowledgeGraphProcessor:
    def __init__(self, uri=None, username="neo4j", password=None):
        """
        初始化知识图谱处理器
        
        Args:
            将json格式的文件处理成csv格式文件，便于导入Neo4j数据库
        """
        # self.uri = uri or os.getenv("NEO4J_URI")
        # self.username = username
        # self.password = password or os.getenv("NEO4J_PASSWORD")
        
        # # 验证必要参数
        # if not self.uri or not self.password:
        #     raise ValueError("请确保设置NEO4J_URI和NEO4J_PASSWORD环境变量")
            
        # # 初始化数据库驱动
        # self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        
        # 数据存储
        self.entities = {}  # 以entity_name为key的实体字典
        self.triples = []   # 三元组列表
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
    
    def load_data(self, entities_json_path, triples_json_path):
        """
        导入实体和三元组JSON文件，转换为类的实例变量
        
        Args:
            entities_json_path (str): 实体JSON文件路径
            triples_json_path (str): 三元组JSON文件路径
        """
        # 读取实体JSON文件
        with open(entities_json_path, 'r', encoding='utf-8') as f:
            entities_data = json.load(f)
        
        # 读取三元组JSON文件
        with open(triples_json_path, 'r', encoding='utf-8') as f:
            triples_data = json.load(f)
        
        # 转换实体数据为字典格式，以entity_name为key
        for entity in entities_data:
            entity_copy = entity.copy()
            # 将原始chunk_ids重命名为entity_chunk_id
            if 'chunk_ids' in entity_copy:
                entity_copy['entity_chunk_id'] = entity_copy.pop('chunk_ids')
            else:
                entity_copy['entity_chunk_id'] = []
            
            # 初始化relation_chunk_id为空列表
            entity_copy['relation_chunk_id'] = []
            
            self.entities[entity_copy['entity_name']] = entity_copy
        
        # 保存三元组数据
        self.triples = triples_data
        
        print(f"加载了 {len(self.entities)} 个实体和 {len(self.triples)} 个三元组")
    
    def enrich_entities(self):
        """
        遍历三元组字典变量，扩充实体字典
        将三元组中出现但实体库中未包含的实体按实体库格式重构
        区分entity_chunk_id和relation_chunk_id
        """
        # 遍历三元组，查找缺失的实体
        for triple in self.triples:
            chunk_id = triple.get('chunk_id', 'unknown')
            
            # 合并处理subject和object
            for entity_name in [triple['subject'], triple['object']]:
                # 检查实体是否在实体库中
                if entity_name not in self.entities:
                    # 不在实体库中，创建新实体，属性记作unknown，chunk_id添加到relation_chunk_id
                    self.entities[entity_name] = {
                        "entity_name": entity_name,
                        "type": ["Unknown"],
                        "domain_relevance": ["unknown"],
                        "summary": "信息待补充",
                        "entity_chunk_id": [],
                        "relation_chunk_id": [chunk_id]
                    }
                else:
                    # 在实体库中，将chunk_id添加到relation_chunk_id（避免重复添加）
                    if chunk_id not in self.entities[entity_name]['relation_chunk_id']:
                        self.entities[entity_name]['relation_chunk_id'].append(chunk_id)
        
        print(f"扩充后共有 {len(self.entities)} 个实体")
    
    def to_csv(self, entities_csv_path:str ='./CSV_output/entities.csv', 
            triples_csv_path:str ='./CSV_output/triples.csv'):
        """
        将扩充过的实体字典和三元组字典重构，按照neo4j要求输入的csv格式进行转换，并保存csv文件
        
        Args:
            entities_csv_path (str): 实体CSV文件保存路径
            triples_csv_path (str): 三元组CSV文件保存路径
        """
        # 转换实体数据为DataFrame
        entities_list = []
        entity_id_map = {}  # 用于映射实体名称到实体ID
        
        # 为每个实体分配ID
        for i, (entity_name, entity) in enumerate(self.entities.items(), 1):
            entity_id = f"entity_{i}"
            entity_id_map[entity_name] = entity_id
            
            # 分别处理entity_chunk_id和relation_chunk_id
            entity_chunk_ids_str = "|".join(map(str, entity.get("entity_chunk_id", []))) if entity.get("entity_chunk_id") else "unknown"
            relation_chunk_ids_str = "|".join(map(str, entity.get("relation_chunk_id", []))) if entity.get("relation_chunk_id") else "unknown"
            
            entity_row = {
                "id:ID": entity_id,
                "name": entity_name,
                "summary": entity.get("summary", "信息待补充"),
                "type": "|".join(entity.get("type", ["Unknown"])),
                "domain_relevance": "|".join(entity.get("domain_relevance", ["unknown"])),
                "entity_chunk_id": entity_chunk_ids_str,
                "relation_chunk_id": relation_chunk_ids_str,
                ":LABEL": f"Entity;{'|'.join(entity.get('type', ['Unknown']))}"
            }
            entities_list.append(entity_row)
        
        # 创建实体DataFrame
        entities_df = pd.DataFrame(entities_list)
        
        # 转换关系数据为DataFrame
        triples_list = []
        for i, triple in enumerate(self.triples, 1):
            subject_name = triple["subject"]
            object_name = triple["object"]
            
            # 确保关系中的实体都在实体列表中
            if subject_name in entity_id_map and object_name in entity_id_map:
                triple_row = {
                    ":START_ID": entity_id_map[subject_name],
                    ":END_ID": entity_id_map[object_name],
                    ":TYPE": triple["relation"]
                }
                triples_list.append(triple_row)
        
        # 创建关系DataFrame
        triples_df = pd.DataFrame(triples_list)
        
        # 保存为CSV文件
        entities_df.to_csv(entities_csv_path, index=False, encoding='utf-8')
        triples_df.to_csv(triples_csv_path, index=False, encoding='utf-8')
        
        print(f"实体数据已保存至: {entities_csv_path}")
        print(f"关系数据已保存至: {triples_csv_path}")
        
        return entities_csv_path, triples_csv_path
    

class KGCSVImporter:
    """
    知识图谱CSV数据导入器
    专门用于将实体和关系CSV文件导入到Neo4j数据库中
    """
    
    def __init__(self, uri: str = None, username: str = "neo4j", password: str = None):
        """
        初始化知识图谱CSV导入器
        
        Args:
            uri (str): Neo4j数据库URI
            username (str): 数据库用户名
            password (str): 数据库密码
        """
        # 设置日志
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
        # 从环境变量获取配置
        self.uri = uri or os.getenv("NEO4J_URI")
        self.username = username
        self.password = password or os.getenv("NEO4J_PASSWORD")
        
        # 验证必要参数
        if not self.uri or not self.password:
            raise ValueError("请确保设置NEO4J_URI和NEO4J_PASSWORD环境变量")
            
        # 初始化数据库驱动
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        
        # 测试连接
        self._test_connection()
        
        self.logger.info("KGCSVImporter初始化成功")
    
    def _test_connection(self):
        """测试数据库连接"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
                self.logger.info("数据库连接测试成功")
        except Exception as e:
            self.logger.error(f"数据库连接测试失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            self.logger.info("数据库连接已关闭")
    
    def import_entities_from_csv(self, csv_path: str) -> int:
        """使用Python批量导入实体"""
        self.logger.info(f"开始导入实体数据: {csv_path}")
        
        # 读取CSV文件
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        if ':LABEL' not in df.columns:
            self.logger.error("CSV文件缺少:LABEL列")
            return 0
        
        total_count = 0
        batch_size = 1000
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            count = self._import_entity_batch(batch)
            total_count += count
            self.logger.info(f"已导入 {min(i+batch_size, len(df))}/{len(df)} 个实体")
        
        self.logger.info(f"成功导入 {total_count} 个实体")
        return total_count
    
    def _import_entity_batch(self, batch_df: pd.DataFrame) -> int:
        """批量导入实体"""
        query = """
        UNWIND $entities AS entity
        MERGE (n:Entity {id: entity.id})
        SET n += entity.properties
        WITH n, entity
        CALL apoc.create.addLabels(n, entity.labels) YIELD node
        RETURN count(n)
        """
        
        entities_data = []
        for _, row in batch_df.iterrows():
            # 准备属性（排除ID和LABEL列）
            properties = {}
            for col in row.index:
                if col not in [':ID', ':LABEL'] and pd.notna(row[col]):
                    properties[col] = row[col]
            
            # 处理标签
            labels = [label.strip() for label in str(row[':LABEL']).split(';') if label.strip()]
            
            entity_data = {
                "id": row['id:ID'],
                "properties": properties,
                "labels": labels
            }
            entities_data.append(entity_data)
        
        try:
            with self.driver.session() as session:
                result = session.run(query, entities=entities_data)
                return result.single()[0]
        except Exception as e:
            self.logger.error(f"批量导入实体时出错: {e}")
            return 0
    
    def import_relations_from_csv(self, csv_path: str) -> int:
        """使用Python批量导入关系"""
        self.logger.info(f"开始导入关系数据: {csv_path}")
        
        df = pd.read_csv(csv_path, encoding='utf-8')
        total_count = 0
        batch_size = 1000
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            count = self._import_relation_batch(batch)
            total_count += count
            self.logger.info(f"已导入 {min(i+batch_size, len(df))}/{len(df)} 个关系")
        
        self.logger.info(f"成功导入 {total_count} 个关系")
        return total_count
    
    def _import_relation_batch(self, batch_df: pd.DataFrame) -> int:
        """批量导入关系"""
        query = """
        UNWIND $relations AS rel
        MATCH (start:Entity {id: rel.start_id})
        MATCH (end:Entity {id: rel.end_id})
        MERGE (start)-[r:RELATION {type: rel.type}]->(end)
        RETURN count(r)
        """
        
        relations_data = []
        for _, row in batch_df.iterrows():
            relation_data = {
                "start_id": row[':START_ID'],
                "end_id": row[':END_ID'],
                "type": row[':TYPE']
            }
            relations_data.append(relation_data)
        
        try:
            with self.driver.session() as session:
                result = session.run(query, relations=relations_data)
                return result.single()[0]
        except Exception as e:
            self.logger.error(f"批量导入关系时出错: {e}")
            return 0
    
    def import_from_csv_files(self, entities_csv_path: str, relations_csv_path: str) -> Dict[str, int]:
        """
        从CSV文件导入实体和关系数据
        
        Args:
            entities_csv_path (str): 实体CSV文件路径
            relations_csv_path (str): 关系CSV文件路径
            
        Returns:
            Dict[str, int]: 导入统计信息
        """
        self.logger.info("开始批量导入实体和关系数据")
        
        # 导入实体
        entity_count = self.import_entities_from_csv(entities_csv_path)
        
        # 导入关系
        relation_count = self.import_relations_from_csv(relations_csv_path)
        
        # 返回统计信息
        stats = {
            "entities_imported": entity_count,
            "relations_imported": relation_count
        }
        
        self.logger.info(f"批量导入完成: {stats}")
        return stats
    
    def clear_database(self):
        """
        清空数据库中的所有实体和关系
        """
        self.logger.warning("正在清空数据库...")
        
        with self.driver.session() as session:
            # 删除所有关系
            session.run("MATCH ()-[r]->() DELETE r")
            self.logger.info("已删除所有关系")
            
            # 删除所有节点
            session.run("MATCH (n) DELETE n")
            self.logger.info("已删除所有节点")
            
            # 删除所有约束
            session.run("DROP CONSTRAINT entity_id_unique IF EXISTS")
            self.logger.info("已删除所有约束")
        
        self.logger.info("数据库清空完成")
    
    def create_indexes(self):
        """
        创建数据库索引以提高查询性能
        """
        with self.driver.session() as session:
            # 为实体名称创建索引
            session.run("CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)")
            
            # 为实体类型创建索引
            session.run("CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            
            # 为关系类型创建索引
            session.run("CREATE INDEX relation_type_index IF NOT EXISTS FOR ()-[r:RELATION]-() ON (r.type)")
        
        self.logger.info("数据库索引创建完成")



# 使用示例
if __name__ == "__main__":
    # 创建导入器实例
    importer = KGCSVImporter()
    importer.clear_database()
    importer.import_from_csv_files(entities_csv_path="./CSV_output/nodes.csv", relations_csv_path="./CSV_output/triples.csv")
    print("导入完毕")
    