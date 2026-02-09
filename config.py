#PyAnki ver5:config.py
#增加编辑删除卡片功能
#这个文件定义了“程序在哪里存数据”以及“默认设置”。
import os

# --- 路径配置 ---
# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, 'pyanki_data.json')
AUDIO_DIR = os.path.join(BASE_DIR, 'pyanki_audio')
IMG_DIR = os.path.join(BASE_DIR, 'pyanki_images')
BACKUP_FILE = os.path.join(BASE_DIR, 'PyAnki_Backup.zip')

# --- 默认设置 ---
DEFAULT_DIALECT = 'zh-HK' # 默认粤语
OFFLINE_DICT_DIR= 'my_offline_dicts'

# --- 初始化环境 ---
def init_dirs():
    for path in [AUDIO_DIR, IMG_DIR]:
        if not os.path.exists(path):
            os.makedirs(path)
