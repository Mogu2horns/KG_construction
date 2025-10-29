import re

def fix_markdown_headings(file_path):
    """
    修复Markdown文档中的标题格式
    - X.Y 格式 -> ## X.Y [标题]
    - X.Y.Z 格式 -> ### X.Y.Z [标题]
    """
    
    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义标题模式
    # 匹配 X.Y 格式的二级标题
    pattern_level2 = r'^#\s+(\d+\.\d+)\s+(.+)$'
    # 匹配 X.Y.Z 格式的三级标题  
    pattern_level3 = r'^#\s+(\d+\.\d+\.\d+)\s+(.+)$'
    
    # 替换函数
    def replace_level2(match):
        number = match.group(1)
        title = match.group(2)
        return f"## {number} {title}"
    
    def replace_level3(match):
        number = match.group(1)
        title = match.group(2)
        return f"### {number} {title}"
    
    # 执行替换
    content = re.sub(pattern_level2, replace_level2, content, flags=re.MULTILINE)
    content = re.sub(pattern_level3, replace_level3, content, flags=re.MULTILINE)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("标题格式修复完成！")

def preview_changes(file_path):
    """
    预览将要进行的修改
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern_level2 = r'^#\s+(\d+\.\d+)\s+(.+)$'
    pattern_level3 = r'^#\s+(\d+\.\d+\.\d+)\s+(.+)$'
    
    changes = []
    
    for line in content.split('\n'):
        if re.match(pattern_level2, line):
            match = re.match(pattern_level2, line)
            new_line = f"## {match.group(1)} {match.group(2)}"
            changes.append(f"原: {line}")
            changes.append(f"新: {new_line}")
            changes.append("---")
        elif re.match(pattern_level3, line):
            match = re.match(pattern_level3, line)
            new_line = f"### {match.group(1)} {match.group(2)}"
            changes.append(f"原: {line}")
            changes.append(f"新: {new_line}")
            changes.append("---")
    
    if changes:
        print("预览修改：")
        for change in changes:
            print(change)
    else:
        print("没有找到需要修改的标题")

# 使用方法
if __name__ == "__main__":
    file_path = "./船舶建造工艺学2/full.md"  # 替换为你的文件路径
    
    # 先预览修改
    print("=== 预览修改 ===")
    preview_changes(file_path)
    
    # 确认是否执行修改
    confirm = input("\n是否执行修改？(y/n): ")
    if confirm.lower() == 'y':
        fix_markdown_headings(file_path)
    else:
        print("取消修改")