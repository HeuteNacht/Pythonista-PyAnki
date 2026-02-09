# 在shortcut py的最开头添加
import os
import sys
#增加转繁体功能
from utils import convert_chinese_smart

# 获取当前 main.py 所在的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 强制将当前目录插入到搜索路径的最前面
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 现在再 import,它会优先找当前文件夹下的 model 和 config
import appex
from model import AnkiManager

import console
import sys
from model import AnkiManager

def get_input():
    # 逻辑 A:如果是从分享菜单启动
    if appex.is_running_extension():
        # 这里是关键:appex 在不同 App 下表现不同
        # 优先取选中的纯文本,其次取 URL,最后取文件内容
        text = appex.get_text()
        if not text:
            # 兼容某些 App 只提供 URL 或复杂对象的情况
            text = appex.get_url()
        return text
    
    # 逻辑 B:如果是从快捷指令 (Shortcuts) 跳转启动
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    return None

def main():
    text = get_input()
    #增加转繁体
    text = convert_chinese_smart(text)
    if not text:
        console.hud_alert("未检测到有效内容", "error")
        appex.finish()
        return

    # --- 在入口处就完成“第一行切割” ---
    # 这样可以绕过所有编码转义的玄学问题
    lines = text.strip().splitlines()
    valid_lines = [l.strip() for l in lines if l.strip()]
    
    if not valid_lines:
        appex.finish()
        return

    front = valid_lines[0]
    # 如果只有一行,背面给个标记;如果多行,合并剩下的
    back = "\n".join(valid_lines[1:]) if len(valid_lines) > 1 else "iOS 快速导入"

    # 调用模型
    manager = AnkiManager()
    
    # 检查重复(直接在入口判断,最稳妥)
    if any(c.front == front for c in manager.cards):
        console.hud_alert("卡片已存在", "error")
    else:
        # 这里直接手动添加,确保不走你那个可能出问题的 quick_add_card
        from model import AnkiCard
        new_card = AnkiCard(front, back)
        manager.cards.append(new_card)
        manager.save_data()
        console.hud_alert(f"已制卡:{front[:10]}...", "success")

    appex.finish()

if __name__ == '__main__':
    main()
