# fix_chinese_relations.py
"""
该文件用来参考大模型输出的英文关系对照表，将中文修复成英文关系
"""
import pandas as pd

def fix_chinese_relations_in_triples(triples_csv_path, error_triples_csv_path, output_path):
    """
    根据error_triples.csv中指定的索引位置，修复triples.csv中的中文关系
    
    Args:
        triples_csv_path (str): 原始三元组CSV文件路径
        error_triples_csv_path (str): 错误三元组CSV文件路径（包含需要修复的索引和英文关系）
        output_path (str): 修复后输出文件路径
    """
    
    # 读取原始三元组数据
    triples_df = pd.read_csv(triples_csv_path)
    
    # 读取错误三元组数据（包含正确的英文关系）
    error_triples_df = pd.read_csv(error_triples_csv_path)
    
    # 创建修复映射字典：索引 -> 英文关系
    fix_mapping = {}
    for _, row in error_triples_df.iterrows():
        index = row['index']
        subject = row['subject']
        relation = row['relation']
        obj = row['object']
        fix_mapping[index] = relation
    
    # 复制原始数据以避免修改原数据
    new_triples_df = triples_df.copy()
    
    # 根据索引替换关系
    for index, english_relation in fix_mapping.items():
        # CSV索引从1开始，但pandas DataFrame索引从0开始
        df_index = index - 1
        if 0 <= df_index < len(new_triples_df):
            new_triples_df.iloc[df_index, new_triples_df.columns.get_loc(':TYPE')] = english_relation
            print(f"已修复索引 {index} 的关系: {english_relation}")
        else:
            print(f"警告: 索引 {index} 超出范围，跳过")
    
    # 保存修复后的文件
    new_triples_df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n修复完成，共处理 {len(fix_mapping)} 个关系")
    print(f"修复后的文件已保存到: {output_path}")
    
    return new_triples_df

def main():
    """
    主函数，执行修复操作
    """
    # 文件路径配置
    triples_csv_path = './CSV_output/triples.csv'
    error_triples_csv_path = './CSV_output/eg_triples.csv'
    output_path = './CSV_output/new_triples.csv'
    
    # 执行修复操作
    try:
        fixed_df = fix_chinese_relations_in_triples(
            triples_csv_path=triples_csv_path,
            error_triples_csv_path=error_triples_csv_path,
            output_path=output_path
        )
        
        # 显示一些统计信息
        print(f"\n处理统计:")
        print(f"- 原始三元组总数: {len(pd.read_csv(triples_csv_path))}")
        print(f"- 需要修复的关系数: {len(pd.read_csv(error_triples_csv_path))}")
        print(f"- 修复后三元组总数: {len(fixed_df)}")
        
    except FileNotFoundError as e:
        print(f"错误: 找不到文件 - {e}")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")

if __name__ == "__main__":
    main()