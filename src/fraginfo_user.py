#!/usr/bin/env python3
import argparse
import urwid
from extfrag import ExtFrag

# 定义颜色调色板
palette = [
    ('header', 'light blue', ''),
    ('body', 'light green', ''),
    ('highlight', 'light red', ''),
    ('reversed', 'standout', ''),
]

# 列标题的解释字典
column_explanations = {
    "Node ID": "The unique identifier of the memory node.",
    "Number of Zones": "The number of memory zones associated with this node.",
    "PGDAT Pointer": "The memory address of the pgdat structure for this node."
}

# 定义不同数据值的解释
value_explanations = {
    "Node ID": lambda value: f"Unique identifier of this node: {value}",
    "Number of Zones": lambda value: f"Number of memory zones: {value}",
    "PGDAT Pointer": lambda value: f"Memory address of pgdat structure: {value}",
}

def show_tooltip(text):
    """ 显示提示信息 """
    tooltip = urwid.Filler(urwid.Text(text, align='center'))
    overlay = urwid.Overlay(urwid.LineBox(tooltip),
                            loop.widget, align='center', width=('relative', 60),
                            valign='middle', height=('relative', 20),
                            min_width=40, min_height=5)
    
    loop.widget = overlay
    loop.draw_screen()  # 确保立即重绘屏幕以显示提示框

def item_clicked(column, value):
    """ 处理点击事件 """
    if column in column_explanations:
        explanation = column_explanations[column]
        if column in value_explanations:
            explanation += f"\n\nCurrent Value: {value}\n{value_explanations[column](value)}"
        else:
            explanation += f"\n\nCurrent Value: {value}"
        show_tooltip(explanation)

def handle_tooltip_input(key):
    """处理提示框输入，按任意键返回主界面"""
    loop.widget = main_widget  # 返回主界面

def create_table(extfrag, args):
    rows = []
    
    if args.node_info:
        # 输出 Node 信息
        header = ["Node ID", "Number of Zones", "PGDAT Pointer"]
        header_widgets = [urwid.AttrMap(ClickableText(urwid.Text(col, align='center'), col, col), 'header') for col in header]
        header_row = urwid.Columns(header_widgets)
        rows.append(header_row)

        node_data = extfrag.get_node_data()
        sorted_node_ids = sorted(node_data.keys())
        
        for node_id in sorted_node_ids:
            node = node_data[node_id]
            columns = ["node_id", "nr_zones", "pgdat_ptr"]
            cell_widgets = []
            for col in columns:
                value = str(node.get(col, ""))
                text = urwid.Text(value, align='center')
                clickable_text = urwid.AttrMap(ClickableText(text, col, value), 'body', focus_map='reversed')
                cell_widgets.append(clickable_text)
            row = urwid.Columns(cell_widgets)
            rows.append(row)
    
    else:
        # 输出 Zone 信息
        if args.score_a or args.score_b:
            header = ["COMM", "ZONE_PFN", "SUM_PAGES", "FACT_PAGES", 
                      "ORDER", "TOTAL", "SUITABLE", "FREE", "SCORE"]
            if args.bar:
                header.append("FRAG_BAR")
        else:
            header = ["COMM", "ZONE_PFN", "SUM_PAGES", "FACT_PAGES", 
                      "ORDER", "TOTAL", "SUITABLE", "FREE", "SCORE1", "SCORE2"]
            if args.bar:
                header.append("FRAG_BAR")

        header_widgets = [urwid.AttrMap(ClickableText(urwid.Text(col, align='center'), col, col), 'header') for col in header]
        header_row = urwid.Columns(header_widgets)
        rows.append(header_row)

        zone_data = extfrag.get_zone_data()
        
        for comm, zones in zone_data.items():
            if args.comm and comm != args.comm:
                continue  
            for zone in zones:
                columns = ["comm", "zone_pfn", "spanned_pages", "present_pages", 
                           "order", "free_blocks_total", "free_blocks_suitable", "free_pages"]
                if args.score_a:
                    columns.append("scoreA")
                elif args.score_b:
                    columns.append("scoreB")
                else:
                    columns.extend(["scoreA", "scoreB"])

                # 根据条件设置颜色
                color = 'body'
                order = int(zone.get('order', 0))
                scoreB = float(zone.get('scoreB', 0))
                if order > 5 and scoreB > 0.5:
                    color = 'highlight'

                cell_widgets = []
                for col in columns:
                    value = str(zone.get(col, ""))
                    text = urwid.Text(value, align='center')
                    clickable_text = urwid.AttrMap(ClickableText(text, col, value), color, focus_map='reversed')
                    cell_widgets.append(clickable_text)

                if args.bar:
                    score = float(zone.get("scoreA" if args.score_a else "scoreB", 0))
                    frag_bar = generate_fragmentation_bar(score)
                    bar_text = urwid.Text(frag_bar, align='center')
                    cell_widgets.append(urwid.AttrMap(bar_text, color))
                
                row = urwid.Columns(cell_widgets)
                rows.append(row)
    
    table = urwid.Pile(rows)
    # 添加外层滚动
    table_with_scroll = urwid.Filler(table, valign='top')
    return table_with_scroll

def generate_fragmentation_bar(score, max_length=20):
    """生成用于显示碎片化程度的条形图"""
    proportion = min(max(score, 0), 1)
    bar_length = int(proportion * max_length)
    return '[' + '#' * bar_length + '-' * (max_length - bar_length) + ']'

def refresh_data(loop, user_data):
    """刷新数据并更新界面"""
    global main_widget
    extfrag, args = user_data
    main_widget = create_table(extfrag, args)
    loop.widget = main_widget
    loop.set_alarm_in(args.delay, refresh_data, user_data)  # 再次设置定时器

def handle_input(key):
    """处理键盘输入以关闭提示框"""
    if isinstance(loop.widget, urwid.Overlay):
        handle_tooltip_input(key)  # 处理提示框输入
    else:
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

class ClickableText(urwid.WidgetWrap):
    """自定义可点击文本Widget"""
    def __init__(self, text_widget, column, value):
        super().__init__(text_widget)
        self.column = column
        self.value = value

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

    def mouse_event(self, size, event, button, x, y, focus):
        if event == 'mouse press' and button == 1:
            item_clicked(self.column, self.value)
            return True
        return False

def main():
    try:
        parser = argparse.ArgumentParser(description='Watch memory fragmentation with real-time updates')
        parser.add_argument('-d', '--delay', type=int,  help='Delay between updates in seconds')
        parser.add_argument('-n', '--node_info', action='store_true', help='Output node information')
        parser.add_argument('-c', '--comm', type=str, help='Filter by comm name')
        parser.add_argument('-e', '--score_a', action='store_true', help='Only output score_a')
        parser.add_argument('-u', '--score_b', action='store_true', help='Only output score_b')
        parser.add_argument('-s', '--output_count', action='store_true', help='Output fragmentation count')
        parser.add_argument('-b', '--bar', action='store_true', help='Display fragmentation bar')  
        args = parser.parse_args()

        extfrag = ExtFrag(interval=args.delay if args.delay else 0, output_count=args.output_count,
                          output_score_a=args.score_a, output_score_b=args.score_b)

        global loop, main_widget
        main_widget = create_table(extfrag, args)
        loop = urwid.MainLoop(main_widget, palette, unhandled_input=handle_input)

        # 设置定时刷新
        loop.set_alarm_in(args.delay, refresh_data, (extfrag, args))

        loop.run()
    except KeyboardInterrupt:
        pass  # 捕获Ctrl+C并安静地退出

if __name__ == "__main__":
    main()
