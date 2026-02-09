#PyAnki ver5:model.py
#增加编辑删除卡片功能
#这是程序的“大脑”,处理所有的数据读写、算法和备份逻辑。
import json
import os
import time
import zipfile
import config # 导入配置

class AnkiCard:
    def __init__(self, front, back, audio_path=None, image_path=None, lang='auto', next_review=0, interval=1, ease=2.5):
        self.front = front
        self.back = back
        self.audio_path = audio_path
        self.image_path = image_path
        self.lang = lang
        self.next_review = next_review
        self.interval = interval
        self.ease = ease

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data):
        return AnkiCard(**data)

class AnkiManager:
    def __init__(self):
        self.cards = []
        # 初始化时读取默认配置
        self.current_dialect = config.DEFAULT_DIALECT 
        # 确保文件夹存在
        config.init_dirs() 
        self.load_data()

    def load_data(self):
        if os.path.exists(config.DATA_FILE):
            try:
                with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cards = [AnkiCard.from_dict(d) for d in data]
            except:
                self.cards = []
        else:
            self.cards = []

    def save_data(self):
        with open(config.DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in self.cards], f, ensure_ascii=False, indent=2)

    def delete_card(self, card):
        if card in self.cards:
            self.cards.remove(card)
            self.save_data()
            return True
        return False

#从剪贴板导入卡片
    def import_from_text(self, text):
        """支持多种分隔符的文本导入"""
        count = 0
        #ego:尝试修复中间断开的问题
        lines = text.strip().split('€')
        #lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
        
            
            parts = []
            # 兼容多种分割符号
            if '|' in line: parts = line.split('|')
            elif '|' in line: parts = line.split('|') # 中文竖线
            elif '\t' in line: parts = line.split('\t') # Excel Tab
            elif '\n' in line: parts = line.split('\n') # 回车换行
            
            if len(parts) >= 2:
                front = parts[0].strip()
                # 后面所有内容作为背面
                back = "\n".join(parts[1:]).strip()
                
                # 简单查重
                if not any(c.front == front for c in self.cards):
                    self.cards.append(AnkiCard(front, back))
                    count += 1
        self.save_data()
        return count

    def get_due_cards(self):
        now = time.time()
        return [c for c in self.cards if c.next_review <= now]

    def process_answer(self, card, quality):
        # SuperMemo-2 算法简化版
        if quality < 3:
            card.interval = 1
            card.ease = max(1.3, card.ease - 0.2)
        else:
            if card.interval == 1:
                card.interval = 6 if quality > 3 else 3
            else:
                card.interval = round(card.interval * card.ease)
            card.ease = card.ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            if card.ease < 1.3: card.ease = 1.3

        if quality < 3:
             # 如果忘记了,10分钟后重试
             card.next_review = time.time() + 600
        else:
             card.next_review = time.time() + (card.interval * 86400)
        self.save_data()

    def save_recording(self, card, temp_file):
        filename = f"rec_{int(time.time())}.m4a"
        dest_path = os.path.join(config.AUDIO_DIR, filename)
        if os.path.exists(temp_file):
            # 移动并重命名
            os.rename(temp_file, dest_path)
            card.audio_path = dest_path 
            self.save_data()
            return True
        return False

    def save_image(self, card, pil_image):
        filename = f"img_{int(time.time())}.jpg"
        dest_path = os.path.join(config.IMG_DIR, filename)
        # 压缩保存
        pil_image.save(dest_path, quality=85)
        card.image_path = dest_path
        self.save_data()

    # --- 辅助方法 ---
    def audio_dir_path(self):
        """返回音频存储目录,供 UI 层使用"""
        return config.AUDIO_DIR

    # --- 备份功能 ---
    def create_backup(self):
        try:
            with zipfile.ZipFile(config.BACKUP_FILE, 'w', zipfile.ZIP_DEFLATED) as z:
                # 1. 写入 JSON 数据
                if os.path.exists(config.DATA_FILE): 
                    z.write(config.DATA_FILE, os.path.basename(config.DATA_FILE))
                
                # 2. 写入媒体文件
                for folder in [config.AUDIO_DIR, config.IMG_DIR]:
                    if os.path.exists(folder):
                        for root, dirs, files in os.walk(folder):
                            for file in files:
                                abs_path = os.path.join(root, file)
                                # 在 zip 包内保持相对路径结构
                                arcname = os.path.relpath(abs_path, config.BASE_DIR)
                                z.write(abs_path, arcname)
            return config.BACKUP_FILE
        except Exception as e:
            print(f"Backup error: {e}")
            return None

    def restore_backup(self, zip_path):
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # 解压覆盖
                z.extractall(config.BASE_DIR)
            # 重新加载内存数据
            self.load_data()
            return True
        except:
            return False
