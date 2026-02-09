import model
import ui_layer
import ui

if __name__ == '__main__':
    # 1. 初始化数据管理器
    app_manager = model.AnkiManager()
    
    # 2. 初始化界面,并注入管理器
    main_view = ui_layer.PyAnkiView(app_manager)
    main_view.name = 'PyAnki v5.0 (Modular)'
    
    # 3. 显示
    main_view.present('fullscreen')

# --- 关键修复:延迟刷新布局 ---
    # 必须给 UI 一个极短的缓冲时间(0.1秒),确保它已经撑满全屏
    def final_layout():
        main_view.refresh_button_layout()
        
    ui.delay(final_layout, 0.1)
