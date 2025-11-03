### CSV_OUTPUT目录下文件含义及作用

* nodes.csv:  处理后的，导入neo4j中的节点文件
* entities.csv: 原始实体文件
* triples.csv: 关系文件
* chinese_relations.csv: 含有错误的中文关系的文件
* eg_triples.csv: 修复中文关系，含有英文关系的文件
* csv2txt.py: txt转csv脚本
* fix_chinese_relations.py: 修复中文关系脚本