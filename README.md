# KG_construction
Code for knowledge graph construction

## 1. CSV_output
CSV文件及相关处理脚本

## 2. KG_output
KG json文件

## 3. chunks_output
原始文本块，实体切块和关系切块方式不同，关系切块方式更加细致

## 4. KG_construction_files
* ac_automaton.py: ac自动机，用于匹配出现在文本中的实体
* entity_db.py: 合并实体json文件，并生成实体库
* triple_db.py: 合并三元组json文件，并生成三元组库
* get_chunks.py: 获取文本块，并生成实体切块和关系切块
* get_entities.py: 获取实体
* get_relations.py: 获取关系
* get_triples.py: 获取三元组(未使用)
* llm_model.py: LLM调用的类文件
* prompt.py: LLM调取的prompt
* qwen3-8b.py: LLM流式输出测试文件
* neo4j_database.py: 导入neo4j图数据库并可视化文件

### 脚本：
* entity_batch_process.sh: 批量处理实体
* relation_batch_process.sh: 批量处理关系
* qwen_deploy.sh: LLM部署文件,通过VLLM调用大模型

### 一键调用指令
```bash
./qwen_deploy.ph
```
