with open('test_output.txt', 'w') as f:
    f.write('Starting test\n')
    
    try:
        from layer1_development.enhanced_rithmic_admin.admin_core_classes import SystemStatus, TUIComponents
        f.write('Imported core classes\n')
        
        from layer1_development.enhanced_rithmic_admin.admin_display_manager_fixed import DisplayManager
        f.write('Imported DisplayManager\n')
        
        from rich.console import Console
        console = Console()
        status = SystemStatus()
        tui_components = TUIComponents(status)
        f.write('Created objects\n')
        
        display_manager = DisplayManager(console, tui_components, status)
        f.write('Created DisplayManager\n')
        
        layout = display_manager.render_layout()
        f.write('Rendered layout\n')
        
        f.write('Test successful\n')
    except Exception as e:
        f.write(f'Error: {str(e)}\n')
        import traceback
        f.write(traceback.format_exc())