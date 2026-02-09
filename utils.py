# PyAnki ver5:utils.py#修复无法读长文章和闪退的问题
import speech
import opencc
import os
import config
import ui

class PureOfflineConverter:
    def __init__(self, dict_dir):
        self.mapping = {}
        self.max_len = 0
        self._load_dicts(dict_dir)

    def _load_dicts(self, dict_dir):
        files = ['STCharacters.txt', 'STPhrases.txt']
        for f_name in files:
            path = os.path.join(dict_dir, f_name)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) >= 2:
                            key = parts[0]
                            val = parts[1].split(' ')[0]
                            self.mapping[key] = val
                            self.max_len = max(self.max_len, len(key))

    def convert(self, text):
        result = []
        i = 0
        while i < len(text):
            match = None
            for length in range(min(self.max_len, len(text) - i), 0, -1):
                sub = text[i:i+length]
                if sub in self.mapping:
                    match = (sub, self.mapping[sub])
                    break
            if match:
                result.append(match[1])
                i += len(match[0])
            else:
                result.append(text[i])
                i += 1
        return "".join(result)

_offline_cc = None

def convert_chinese_smart(text, mode='s2t'):
    global _offline_cc
    if not text: return ""
    try:
        cc = opencc.OpenCC(mode)
        return cc.convert(text)
    except Exception as e:
        if _offline_cc is None:
            dict_path = config.OFFLINE_DICT_DIR
            if os.path.exists(dict_path):
                _offline_cc = PureOfflineConverter(dict_path)
            else:
                return f"转换失败:OpenCC不可用且未发现离线字典 {dict_path}"
        return "[离线] " + _offline_cc.convert(text)

def is_contains_chinese(string):
    if not string: return False
    for char in string:
        if '\u4e00' <= char <= '\u9fa5':
            return True
    return False

def speak_text(text, lang_pref='auto', default_chinese='zh-HK'):
    """TTS 发音逻辑 (原生队列版：读完所有长文且不闪退)"""
    import speech
    import time

    if not text:
        return
    
    # 1. 环境准备
    lang_code = 'en-US'
    if lang_pref and lang_pref != 'auto':
        lang_code = lang_pref
    elif is_contains_chinese(text):
        lang_code = default_chinese
        
    # 2. 物理重置：先停掉之前的，给硬件 0.1s 反应时间
    speech.stop()
    time.sleep(0.1)

    # 3. 智能切割：将长文切成 400 字左右的小块（这是繁体字最安全的缓冲区长度）
    # 我们按“句号”切割，确保语意连贯
    def get_safe_chunks(raw_text, limit=400):
        # 统一标点符号
        temp_text = raw_text.replace('。', '。|').replace('.', '.|').replace('\n', ' |')
        parts = temp_text.split('|')
        
        chunks = []
        current_chunk = ""
        for p in parts:
            if len(current_chunk) + len(p) < limit:
                current_chunk += p
            else:
                if current_chunk: chunks.append(current_chunk)
                current_chunk = p
        if current_chunk: chunks.append(current_chunk)
        return chunks

    chunks = get_safe_chunks(text)

    # 4. 一次性注入原生队列
    # iOS 会自动管理：读完 chunks[0]，接着读 chunks[1]，以此类推
    # 这种方式不会闪退，因为每一块都在 iOS 的内存容错范围内
    try:
        for chunk in chunks:
            if chunk.strip():
                speech.say(chunk, lang_code, 0.45)
    except Exception as e:
        print(f"TTS Queue Error: {e}")
