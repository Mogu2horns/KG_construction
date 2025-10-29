import re

def fix_single_hash_headings(file_path):
    """
    将单个#开头的标题改为四级标题####
    但保留包含"第X章"字样的标题
    """
    
    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    changes = []
    
    for line in lines:
        original_line = line.rstrip()  # 只去掉右侧空白，保留左侧缩进
        
        # 检查是否是以单个#开头的标题行（前面可能有空格）
        if re.match(r'^\s*#\s+', original_line) and not re.match(r'^\s*#{2,}', original_line):
            # 检查是否包含"第X章"字样，如果是则保留
            if re.search(r'第[零一二三四五六七八九十百千\d]+章', original_line):
                new_lines.append(line)
                changes.append(f"保留: {original_line}")
            else:
                # 将单个#标题改为四级标题####
                new_line = re.sub(r'^\s*#\s+', '#### ', line)
                new_lines.append(new_line)
                changes.append(f"修改: {original_line} -> {new_line.strip()}")
        else:
            new_lines.append(line)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    # 显示修改记录
    if changes:
        print("修改记录：")
        for change in changes:
            print(change)
        modified_count = len([c for c in changes if '修改' in c])
        retained_count = len([c for c in changes if '保留' in c])
        print(f"\n统计：修改了 {modified_count} 个标题，保留了 {retained_count} 个章节标题")
    else:
        print("没有需要修改的标题")

def preview_single_hash_headings(file_path):
    """
    预览将要进行的修改
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("=== 预览修改（单个#标题 -> ####）===")
    preview_changes = []
    
    for line in lines:
        original_line = line.rstrip()
        
        # 检查是否是以单个#开头的标题行
        if re.match(r'^\s*#\s+', original_line) and not re.match(r'^\s*#{2,}', original_line):
            # 检查是否包含"第X章"字样
            if re.search(r'第[零一二三四五六七八九十百千\d]+章', original_line):
                preview_changes.append(f"保留: {original_line}")
            else:
                new_line = re.sub(r'^\s*#\s+', '#### ', original_line)
                preview_changes.append(f"修改: {original_line}")
                preview_changes.append(f"  -> {new_line}")
                preview_changes.append("---")
    
    if preview_changes:
        for change in preview_changes:
            print(change)
    else:
        print("没有找到需要修改的单个#标题")

# 使用方法
if __name__ == "__main__":
    file_path = "./船舶建造工艺学2/full.md"  # 替换为你的文件路径
    
    print("单个#标题修复工具")
    print("=" * 50)
    
    # 先预览
    preview_single_hash_headings(file_path)
    
    # 确认是否执行修改
    if input("\n是否执行修改？(y/n): ").lower() == 'y':
        fix_single_hash_headings(file_path)
        print("\n修改完成！")
    else:
        print("取消修改")