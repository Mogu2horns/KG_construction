import json
import os

def merge_all_triplets(json_directory, output_file):
    """
    合并指定目录下的所有三元组JSON文件并保存到新文件
    
    Args:
        json_directory (str): 包含JSON文件的目录路径
        output_file (str): 合并后输出文件的路径
        
    Returns:
        int: 合并的三元组总数
    """
    
    # 存储所有三元组的列表
    all_triplets = []
    
    # 检查目录是否存在
    if not os.path.exists(json_directory):
        raise FileNotFoundError(f"目录 {json_directory} 不存在")
    
    # 遍历目录中的所有JSON文件
    print(f"开始扫描目录: {json_directory}")
    file_count = 0
    
    for filename in os.listdir(json_directory):
        if filename.endswith('.json'):
            file_path = os.path.join(json_directory, filename)
            
            try:
                # 读取并解析JSON文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    triplets = json.load(f)
                    
                    # 将当前文件中的三元组添加到总列表中
                    all_triplets.extend(triplets)
                    file_count += 1
                    print(f"已处理文件: {filename} (包含 {len(triplets)} 个三元组)")
                    
            except json.JSONDecodeError as e:
                print(f"警告: 文件 {filename} 不是有效的JSON格式，已跳过")
            except Exception as e:
                print(f"警告: 处理文件 {filename} 时出错: {e}")
    
    # 保存合并后的结果到新文件
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_triplets, f, ensure_ascii=False, indent=2)
        
        print(f"\n合并完成:")
        print(f"- 处理了 {file_count} 个JSON文件")
        print(f"- 总共合并了 {len(all_triplets)} 个三元组")
        print(f"- 结果已保存到: {output_file}")
        
        return len(all_triplets)
        
    except Exception as e:
        print(f"保存文件时出错: {e}")
        return 0

# 使用示例
if __name__ == "__main__":
    # 设置输入目录和输出文件路径
    input_directory = "/disk1/wuchufeng/KG_construction/triplets_output"
    output_file_path = "/disk1/wuchufeng/KG_construction/kg_output/triples_kb.json"
    
    # 执行合并操作
    total_triplets = merge_all_triplets(input_directory, output_file_path)
    
    # 可选：显示前几个三元组作为预览
    if total_triplets > 0:
        with open(output_file_path, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
            print(f"\n前5个三元组预览:")
            for i, triplet in enumerate(sample_data[:5]):
                print(f"{i+1}. {triplet}")