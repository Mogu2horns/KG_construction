import os
import re

def delete_hash_files():
    """
    删除文件夹中类似哈希乱码的文件
    哈希文件通常特征：64个十六进制字符 + 扩展名
    """
    target_directory = "./船舶建造工艺学2/images"
    
    # 匹配64个十六进制字符的文件名（SHA256格式）
    hash_pattern = re.compile(r'^[a-f0-9]{64}\.\w+$', re.IGNORECASE)
    
    deleted_count = 0
    error_count = 0
    
    try:
        # 检查文件夹是否存在
        if not os.path.exists(target_directory):
            print(f"错误: 文件夹 '{target_directory}' 不存在")
            return
        
        # 遍历文件夹中的所有文件
        for filename in os.listdir(target_directory):
            file_path = os.path.join(target_directory, filename)
            
            # 只处理文件，不处理文件夹
            if os.path.isfile(file_path):
                # 检查文件名是否符合哈希模式
                if hash_pattern.match(filename):
                    try:
                        os.remove(file_path)
                        print(f"已删除: {filename}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"删除失败 {filename}: {e}")
                        error_count += 1
        
        print(f"\n操作完成！")
        print(f"成功删除: {deleted_count} 个文件")
        print(f"删除失败: {error_count} 个文件")
        
    except Exception as e:
        print(f"访问文件夹失败: {e}")

# 使用示例
delete_hash_files()