import re
from pathlib import Path

def debug_image_renaming(md_file_path, images_folder="./船舶建造工艺学2/images"):
    """
    调试图片重命名问题
    """
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    print("调试信息：")
    print("=" * 60)
    
    for i, line in enumerate(lines):
        if '![](' in line and 'images/' in line:
            print(f"\n第{i+1}行发现图片引用:")
            print(f"内容: {repr(line)}")
            
            # 提取哈希文件名
            match = re.search(r'!\[\]\(images/([a-f0-9]+\.(?:jpg|png|jpeg|gif))\)', line)
            if match:
                image_hash = match.group(1)
                print(f"提取的哈希: {image_hash}")
                
                # 检查下一行
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    print(f"下一行内容: {repr(next_line)}")
                    print(f"下一行去除空白: {repr(next_line.strip())}")
                    
                    # 检查是否以"图"开头
                    stripped_next = next_line.strip()
                    if stripped_next.startswith('图'):
                        print("✓ 下一行以'图'开头")
                        
                        # 尝试提取描述
                        description_match = re.match(r'图[\d\.\-]+\s+(.+)', stripped_next)
                        if description_match:
                            description = description_match.group(1)
                            print(f"✓ 提取的描述: {description}")
                            print(f"新文件名: {description}.jpg")
                        else:
                            print("✗ 无法提取描述内容")
                            # 尝试其他模式
                            alt_match = re.match(r'图([^ ]+)\s+(.+)', stripped_next)
                            if alt_match:
                                print(f"备选匹配 - 描述: {alt_match.group(2)}")
                    else:
                        print("✗ 下一行不以'图'开头")
                else:
                    print("✗ 没有下一行")
                
                # 检查文件是否存在
                file_path = Path(images_folder) / image_hash
                print(f"文件存在: {file_path.exists()}")
    
    print("\n" + "=" * 60)

# 修复版本的重命名函数
def fix_image_renaming(md_file_path, images_folder="./船舶建造工艺学2/images"):
    """
    修复版的图片重命名函数
    """
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    updated_content = content
    
    for i, line in enumerate(lines):
        if '![](' in line and 'images/' in line:
            match = re.search(r'!\[\]\(images/([a-f0-9]+\.(?:jpg|png|jpeg|gif))\)', line)
            if match and i + 1 < len(lines):
                image_hash = match.group(1)
                next_line = lines[i + 1].strip()
                
                # 更灵活的模式匹配
                if next_line.startswith('图'):
                    # 匹配 "图X-X 描述" 或 "图X 描述" 等格式
                    description_match = re.match(r'图[\d\.\-]+\s+(.+)', next_line)
                    if description_match:
                        description = description_match.group(1).strip()
                        
                        # 清理文件名
                        clean_description = re.sub(r'[<>:"/\\|?*]', '', description)
                        clean_description = clean_description.replace(' ', '_')
                        
                        new_filename = f"{clean_description}.jpg"
                        old_path = Path(images_folder) / image_hash
                        new_path = Path(images_folder) / new_filename
                        
                        if old_path.exists():
                            try:
                                # 重命名文件
                                old_path.rename(new_path)
                                print(f"✓ 重命名: {image_hash} -> {new_filename}")
                                
                                # 更新内容
                                old_ref = f"images/{image_hash}"
                                new_ref = f"images/{new_filename}"
                                updated_content = updated_content.replace(old_ref, new_ref)
                                
                            except Exception as e:
                                print(f"✗ 重命名失败: {e}")
                        else:
                            print(f"⚠ 文件不存在: {image_hash}")
    
    # 保存更新后的内容
    if updated_content != content:
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print("✓ Markdown文件已更新")
    else:
        print("⚠ 没有进行任何更改")

# 使用示例
if __name__ == "__main__":
    md_file = "./船舶建造工艺学2/full.md"  # 替换为您的文件路径
    
    print("调试模式：")
    debug_image_renaming(md_file)
    
    if input("\n是否执行修复？(y/n): ").lower() == 'y':
        fix_image_renaming(md_file)