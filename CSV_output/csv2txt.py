# convert_eg_triples_to_csv.py
import pandas as pd
import csv

def convert_eg_triples_to_csv(input_file, output_file):
    """
    该文件用来将txt文件转换为csv文件。将eg_triples.txt文件转换为CSV格式
    
    Args:
        input_file (str): 输入的txt文件路径
        output_file (str): 输出的csv文件路径
    """
    
    # 读取txt文件
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 处理数据
    data = []
    for line in lines:
        # 去除首尾的引号和换行符
        line = line.strip().strip('"')
        if line and not line.startswith('index,subject,relation,object'):
            # 分割数据
            parts = line.split(',', 3)  # 最多分割成4部分
            if len(parts) == 4:
                # 处理索引
                index = parts[0].strip()
                # 处理主体、关系、客体，去除可能的引号
                subject = parts[1].strip().strip('"')
                relation = parts[2].strip().strip('"')
                object_ = parts[3].strip().strip('"')
                
                data.append({
                    'index': index,
                    'subject': subject,
                    'relation': relation,
                    'object': object_
                })
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 保存为CSV文件
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"转换完成！共处理 {len(data)} 行数据")
    print(f"输出文件: {output_file}")
    
    # 显示前几行作为示例
    print("\n前5行数据预览:")
    print(df.head(5))
    
    return df

def convert_eg_triples_to_csv_v2(input_file, output_file):
    """
    使用csv模块处理更复杂的文本格式
    
    Args:
        input_file (str): 输入的txt文件路径
        output_file (str): 输出的csv文件路径
    """
    
    data = []
    
    # 读取并解析文件
    with open(input_file, 'r', encoding='utf-8') as f:
        # 读取所有行
        lines = f.readlines()
        
        # 处理每一行
        for i, line in enumerate(lines):
            # 去除行首行尾的空白字符和引号
            line = line.strip().strip('"')
            
            # 跳过标题行
            if line.startswith('index,subject,relation,object'):
                continue
                
            if line:
                try:
                    # 使用csv模块解析可能包含引号的行
                    reader = csv.reader([line], delimiter=',')
                    row_data = next(reader)
                    
                    if len(row_data) >= 4:
                        index = row_data[0].strip()
                        subject = row_data[1].strip()
                        relation = row_data[2].strip()
                        object_ = row_data[3].strip()
                        
                        # 如果还有更多列，将其余部分合并到object中
                        if len(row_data) > 4:
                            object_ += ',' + ','.join(row_data[4:])
                        
                        data.append({
                            'index': index,
                            'subject': subject,
                            'relation': relation,
                            'object': object_
                        })
                except Exception as e:
                    print(f"处理第 {i+1} 行时出错: {line}")
                    print(f"错误信息: {e}")
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 保存为CSV文件
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"转换完成！共处理 {len(data)} 行数据")
    print(f"输出文件: {output_file}")
    
    # 显示前几行作为示例
    print("\n前5行数据预览:")
    print(df.head(5))
    
    return df

# 使用示例
if __name__ == "__main__":
    input_file = './eg_triples.txt'
    output_file = './eg_triples.csv'
    
    try:
        # 尝试使用第一种方法
        df = convert_eg_triples_to_csv_v2(input_file, output_file)
    except Exception as e:
        print(f"转换过程中出现错误: {e}")