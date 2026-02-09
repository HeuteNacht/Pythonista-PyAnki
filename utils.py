#PyAnki ver5:utils.py
#增加编辑删除卡片功能
#这里存放独立的辅助函数,它们不需要知道“卡片”是什么,只需要处理输入输出

import speech
#支持简体中文转繁体中文
import opencc
# 支持文件系统
import os
import config

# --- 离线转换器核心逻辑 ---
class PureOfflineConverter:
    def __init__(self, dict_dir):
        self.mapping = {}
        self.max_len = 0
        self._load_dicts(dict_dir)

    def _load_dicts(self, dict_dir):
        # 常见字典文件名列表
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
            for length in range(self.max_len, 0, -1):
                sub = text[i : i + length]
                if sub in self.mapping:
                    match = self.mapping[sub]
                    result.append(match)
                    i += length
                    break
            if not match:
                result.append(text[i])
                i += 1
        return "".join(result)

# --- 智能转换逻辑 ---
_online_cc = None
_offline_cc = None

def convert_chinese_smart(text, mode='s2t'):
    """智能转换:优先 OpenCC,失败则转离线"""
    global _online_cc, _offline_cc
    
    # 1. 尝试使用 OpenCC (在线/原生)
    try:
        if _online_cc is None:
            # 这里的尝试可能会因为没有字典或网络环境而失败
            _online_cc = opencc.OpenCC(mode)
        return _online_cc.convert(text)
    
    except Exception as e:
        # 2. 如果失败,进入离线降级模式
        if _offline_cc is None:
            dict_path = config.OFFLINE_DICT_DIR
            if os.path.exists(dict_path):
                _offline_cc = PureOfflineConverter(dict_path)
            else:
                return f"转换失败:OpenCC不可用且未发现离线字典 {dict_path}"
        
        # 离线转换不需要 mode 参数(通常默认 s2t)
        return "[离线] " + _offline_cc.convert(text)

'''
# 全局缓存转换器实例,避免重复加载字典提高性能
_converter_cache = {}

def convert_chinese(text, mode='s2t'):
    """
    通用中文转换工具
    :param text: 需要转换的文本
    :param mode: 转换模式
        's2t': 简体 -> 繁体 (默认)
        's2twp': 简体 -> 台湾繁体 (带词汇修正)
        't2s': 繁体 -> 简体
    """
    global _converter_cache
    
    # 如果缓存中没有该模式的转换器,则初始化一个
    if mode not in _converter_cache:
        _converter_cache[mode] = opencc.OpenCC(mode)
    
    return _converter_cache[mode].convert(text)
'''

def is_contains_chinese(string):
    """判断字符串是否包含中文"""
    for char in string:
        if '\u4e00' <= char <= '\u9fa5':
            return True
    return False

def speak_text(text, lang_pref='auto', default_chinese='zh-CN'):
    """TTS 发音逻辑 (修正版)"""
    lang_code = 'en-US'
    
    if lang_pref != 'auto':
        lang_code = lang_pref
    elif is_contains_chinese(text):
        lang_code = default_chinese
        
    speech.stop()
    # 修正:直接传递 0.4 作为第三个参数,不使用 rate=
    try:
        speech.say(text, lang_code, 0.4)
    except:
        speech.say(text, lang_code)
