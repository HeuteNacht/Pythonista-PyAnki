import ui
import clipboard
import sound
import photos
import console 
import dialogs 
import speech 
import os
import shutil 
import time 
import model 
import utils 
from utils import convert_chinese_smart

class PyAnkiView(ui.View):
    def __init__(self, manager):
        self.manager = manager
        self.current_card = None
        self.current_card_id = None 
        self.showing_back = False
        self.recorder = None
        self.is_recording = False
        self.setup_ui()
        self.update_title_status()
        self.load_next_card()

    def setup_ui(self):
        self.background_color = '#f0f0f0'
        
        # 顶部按钮
        self.btn_menu = ui.ButtonItem(image=ui.Image.named('iob:ios7_gear_24'), action=self.show_menu)
        self.btn_audio_menu = ui.ButtonItem(image=ui.Image.named('iob:mic_a_24'), action=self.show_audio_menu)
        self.btn_camera = ui.ButtonItem(image=ui.Image.named('iob:camera_24'), action=self.add_image_action)
        self.right_button_items = [self.btn_menu, self.btn_audio_menu, self.btn_camera]
        
        # --- 布局优化:统一边距 ---
        # 定义统一的边距和位置变量,确保上下对齐
        margin_x = 15
        top_margin = 15
        bottom_area_height = 140 # 底部按钮区域的高度
        
        # 卡片高度 = 总高度 - 顶部边距 - 底部区域高度
        card_height = self.height - top_margin - bottom_area_height
        card_width = self.width - (margin_x * 2)
        
        # 1. 卡片面板
        self.card_panel = ui.View(frame=(margin_x, top_margin, card_width, card_height))
        self.card_panel.background_color = 'white'
        self.card_panel.corner_radius = 12
        self.card_panel.border_width = 1
        self.card_panel.border_color = '#ddd'
        self.card_panel.flex = 'WH' # 宽高自适应
        self.add_subview(self.card_panel)
        
        # 图片视图
        self.img_view = ui.ImageView(frame=(0, 0, self.card_panel.width, 0))
        self.img_view.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        self.img_view.flex = 'W'
        self.img_view.hidden = True
        self.img_view.touch_enabled = False 
        self.card_panel.add_subview(self.img_view)

        # 文本框
        self.tv_text = ui.TextView(frame=(10, 40, self.card_panel.width-20, self.card_panel.height-100))
        self.tv_text.alignment = ui.ALIGN_CENTER
        self.tv_text.font = ('PingFang SC', 26)
        self.tv_text.editable = False 
        self.tv_text.selectable = True 
        self.tv_text.text_color = '#333'
        self.tv_text.flex = 'WH'
        self.card_panel.add_subview(self.tv_text)
        
        # 播放按钮
        self.btn_play_record = ui.Button(frame=(0, 0, 48, 48))
        self.btn_play_record.image = ui.Image.named('iob:play_32')
        self.btn_play_record.tint_color = '#007aff'
        self.btn_play_record.action = self.play_custom_recording
        self.btn_play_record.hidden = True 
        self.card_panel.add_subview(self.btn_play_record)
        
        # 翻页按钮 (全屏遮罩)
        self.btn_flip = ui.Button(frame=(0, 0, self.card_panel.width, self.card_panel.height))
        self.btn_flip.action = self.reveal_answer
        self.btn_flip.flex = 'WH'
        self.card_panel.add_subview(self.btn_flip)
        self.btn_flip.send_to_back()
        
        # --- 布局优化 2:底部按钮区域 ---
        # 关键点:action_panel 的 x 和 width 必须与 card_panel 完全一致
        action_y = top_margin + card_height + 10 # 卡片下方 10px 处
        self.action_panel = ui.View(frame=(margin_x, action_y, card_width, 100))
        self.action_panel.flex = 'WT' # 宽度自适应,顶部距离固定(跟随卡片底部)
        self.add_subview(self.action_panel)
        
        self.create_grade_buttons()

    def create_grade_buttons(self):
        labels = ['重来', '困难', '良好', '简单']
        colors = ['#ffaaaa', '#ffecb3', '#dcedc8', '#b3e5fc']
        qualities = [0, 3, 4, 5]
        
        self.grade_buttons = []
        for i, label in enumerate(labels):
            btn = ui.Button(title=label)
            btn.background_color = colors[i]
            btn.corner_radius = 12
            btn.tint_color = '#333'
            btn.font = ('<system-bold>', 18)
            btn.quality = qualities[i]
            btn.action = self.submit_grade
            btn.enabled = False
            # 暂时不设置 frame,也不设置 flex
            self.action_panel.add_subview(btn)
            self.grade_buttons.append(btn)

    def refresh_button_layout(self):
        """强制按照当前面板宽度重新排布按钮"""
        if not self.grade_buttons: return
        
        gap = 6
        # 此时获取的宽度是 present 之后的真实宽度
        total_w = self.action_panel.width 
        n = len(self.grade_buttons)
        btn_w = (total_w - (gap * (n + 1))) / n
        
        for i, btn in enumerate(self.grade_buttons):
            btn.frame = (gap + i * (btn_w + gap), 10, btn_w, 70)

    def update_title_status(self):
        lang = "粤" if self.manager.current_dialect == 'zh-HK' else "普"
        self.name = f"PyAnki [{lang}]"

    def _schedule_auto_reveal(self):
        check_id = time.time()
        self.current_card_id = check_id
        def check_time():
            if self.current_card_id == check_id and not self.showing_back:
                self.reveal_answer(None)
                console.hud_alert('时间到,自动显示答案')
        ui.delay(check_time, 60)

    # --- 核心交互逻辑 ---
    
    def load_next_card(self):
        due_cards = self.manager.get_due_cards()
        if due_cards:
            self.current_card = due_cards[0]
            self.showing_back = False
            self.tv_text.touch_enabled = False 
            self.display_current_card()
            self.play_audio(self.current_card.front, self.current_card.audio_path)
            self._schedule_auto_reveal()
        else:
            self.current_card = None
            self.layout_card_content(False)
            self.tv_text.text = "今日完成!"
            self.img_view.hidden = True
            self.btn_play_record.hidden = True
            self.tv_text.touch_enabled = False 
        
        for btn in self.grade_buttons: btn.enabled = False

    def reveal_answer(self, sender):
        if not self.current_card: return
        if self.showing_back: return
        self.showing_back = True
        self.tv_text.touch_enabled = True 
        self.display_current_card()
        if self.current_card.audio_path:
            self.play_audio(None, self.current_card.audio_path)
        else:
            self.play_audio(self.current_card.back, None)
        for btn in self.grade_buttons: btn.enabled = True

    # --- 显示与布局 ---

    def display_current_card(self):
        if not self.current_card: return
        c = self.current_card
        
        has_img = False
        if c.image_path and os.path.exists(c.image_path):
            self.img_view.image = ui.Image.named(c.image_path)
            has_img = True
        self.layout_card_content(has_img)
        
        if self.showing_back:
            self.tv_text.text = f"{c.front}\n\n---\n\n{c.back}\n\n"
        else:
            self.tv_text.text = c.front
            
        if c.audio_path and os.path.exists(c.audio_path):
            self.btn_play_record.hidden = False
            self.btn_play_record.bring_to_front()
            btn_size = 48
            padding = 15
            self.btn_play_record.frame = (
                self.card_panel.width - btn_size - padding, 
                self.card_panel.height - btn_size - padding, 
                btn_size, btn_size
            )
        else:
            self.btn_play_record.hidden = True

    def layout_card_content(self, has_image=False):
        w, h = self.card_panel.width, self.card_panel.height
        if has_image:
            img_h = h * 0.40 
            self.img_view.frame = (0, 0, w, img_h)
            self.img_view.hidden = False
            self.tv_text.frame = (10, img_h + 10, w - 20, h - img_h - 20)
        else:
            self.img_view.hidden = True
            self.tv_text.frame = (15, 30, w-30, h-60)

    # --- 音频播放 ---
    def play_audio(self, text, file_path):
        speech.stop()
        if file_path and os.path.exists(file_path):
            sound.play_effect(file_path)
        elif text:
            utils.speak_text(text, self.current_card.lang, self.manager.current_dialect)

    def play_custom_recording(self, sender):
        if self.current_card and self.current_card.audio_path:
             if os.path.exists(self.current_card.audio_path):
                 speech.stop()
                 sound.play_effect(self.current_card.audio_path)
             else: console.hud_alert('文件已丢失')

    # --- 菜单功能 ---
    @ui.in_background
    def show_menu(self, sender):
        options = ['编辑卡片', '删除卡片', '剪贴板导入', '切换发音(粤/普)', '备份数据 (导出)', '恢复数据 (导入)']
        selection = dialogs.list_dialog('功能菜单', options)
        if selection == '编辑卡片': self.edit_current_card()
        elif selection == '删除卡片': self.delete_current_card()
        elif selection == '剪贴板导入': self.import_text_cards()
        elif selection == '切换发音(粤/普)': self.toggle_dialect()
        elif selection == '备份数据 (导出)': self.export_backup()
        elif selection == '恢复数据 (导入)': self.import_backup_zip()

    @ui.in_background
    def add_image_action(self, sender):
        if not self.current_card: 
            console.hud_alert('没有卡片'); return
        source = dialogs.list_dialog('图片管理', ['相册选取', '拍照', '剪贴板粘贴', '删除图片'])
        if not source: return 
        try:
            if source == '删除图片':
                if self.current_card.image_path:
                    self.current_card.image_path = None
                    self.manager.save_data(); console.hud_alert('图片已删除'); ui.delay(self.display_current_card, 0.1)
                else: console.hud_alert('当前没有图片')
                return
            img = None
            if source == '相册选取': img = photos.pick_image()
            elif source == '拍照': img = photos.capture_image()
            elif source == '剪贴板粘贴': img = clipboard.get_image()
            if img:
                self.manager.save_image(self.current_card, img); console.hud_alert('图片已保存'); ui.delay(self.display_current_card, 0.1)
            elif source == '剪贴板粘贴': console.hud_alert('剪贴板无图片')
        except Exception as e: console.alert('错误', str(e), '好')

    @ui.in_background
    def show_audio_menu(self, sender):
        if not self.current_card: return
        options = ['录制新语音', '从文件导入', '清除录音']
        selection = dialogs.list_dialog('音频选项', options)
        if selection == '录制新语音': ui.delay(self._show_record_panel, 0.1)
        elif selection == '从文件导入': self._import_audio_file()
        elif selection == '清除录音':
            self.current_card.audio_path = None; self.manager.save_data(); console.hud_alert('录音已清除'); self.display_current_card()

    def _show_record_panel(self):
        rec_view = ui.View(name='录音机', bg_color='white', frame=(0, 0, 300, 300))
        lbl = ui.Label(frame=(10, 20, 280, 40), text="准备就绪", alignment=ui.ALIGN_CENTER, font=('<system-bold>', 20)); rec_view.add_subview(lbl)
        btn = ui.Button(frame=(100, 100, 100, 100), bg_color='#ff3b30', corner_radius=50, tint_color='white', image=ui.Image.named('iob:mic_a_32'))
        state = {'rec': False, 'r': None, 'p': os.path.abspath('temp_rec_modal.m4a')}
        def toggle(s):
            if not state['rec']:
                speech.stop(); state['rec']=True; lbl.text="录音中..."; btn.bg_color='#ccc'; btn.image=ui.Image.named('iob:stop_32')
                state['r']=sound.Recorder(state['p']); state['r'].record()
            else:
                state['rec']=False; lbl.text="保存中..."; 
                if state['r']: state['r'].stop(); state['r']=None
                def save():
                    if self.manager.save_recording(self.current_card, state['p']): console.hud_alert('保存成功'); self.display_current_card()
                    rec_view.close()
                ui.delay(save, 0.5)
        btn.action = toggle; rec_view.add_subview(btn); rec_view.present('sheet')

    @ui.in_background
    def _import_audio_file(self):
        path = dialogs.pick_document(types=['public.audio'])
        if path:
            try:
                ext = os.path.splitext(path)[1] or '.m4a'
                dest = os.path.join(self.manager.audio_dir_path(), f"imp_{int(time.time())}{ext}")
                shutil.copy(path, dest)
                self.current_card.audio_path = dest; self.manager.save_data(); console.hud_alert('导入成功'); ui.delay(self.display_current_card, 0.1)
            except Exception as e: console.alert('失败', str(e))

    def submit_grade(self, sender):
        if not self.current_card: return
        self.manager.process_answer(self.current_card, sender.quality)
        self.load_next_card()

    def import_text_cards(self):
        text = clipboard.get()
        #ego:尝试增加中文简体转繁体
        text = convert_chinese_smart(text)
        if text:
            count = self.manager.import_from_text(text); 
            console.hud_alert(f'导入 {count} 张'); 
            self.load_next_card()

    @ui.in_background
    def edit_current_card(self):
        if not self.current_card: return
        def _show():
            v=ui.View(name='编辑', bg_color='white')
            ui.Label(frame=(10,10,200,30),text="正面:").flex='W'; t1=ui.TextView(frame=(10,40,280,100),border_width=1,text=self.current_card.front);v.add_subview(t1)
            ui.Label(frame=(10,150,200,30),text="背面:").flex='W'; t2=ui.TextView(frame=(10,180,280,100),border_width=1,text=self.current_card.back);v.add_subview(t2)
            for s in v.subviews: v.add_subview(s) 
            def save(s):
                self.current_card.front=t1.text; self.current_card.back=t2.text; self.manager.save_data(); self.display_current_card(); v.close(); console.hud_alert('已保存')
            v.right_button_items=[ui.ButtonItem(title='保存', action=save)]; v.present('sheet')
        ui.delay(_show, 0.1)

    @ui.in_background
    def delete_current_card(self):
        if not self.current_card: return
        try: 
            if console.alert('删除','确认?','删除')==1: self.manager.delete_card(self.current_card); console.hud_alert('已删除'); ui.delay(self.load_next_card, 0.1)
        except: pass

    @ui.in_background
    def export_backup(self):
        console.hud_alert('打包中...'); path=self.manager.create_backup(); 
        if path: console.open_in(path)
    
    @ui.in_background
    def import_backup_zip(self):
        path=dialogs.pick_document()
        if path and self.manager.restore_backup(path): console.hud_alert('恢复成功'); ui.delay(self.load_next_card, 0.1)

    def toggle_dialect(self):
        self.manager.current_dialect = 'zh-HK' if self.manager.current_dialect == 'zh-CN' else 'zh-CN'
        console.hud_alert('切换成功'); self.update_title_status()
