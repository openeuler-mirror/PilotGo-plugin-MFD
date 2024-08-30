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
    "PGDAT Pointer": "The memory address of the pgdat structure for this node.",
    "COMM": "The name of the memory zone, e.g., DMA, Normal.",
    "ZONE_PFN": "Starting page frame number of the memory zone.",
    "SUM_PAGES": "Total number of pages in the zone.",
    "FACT_PAGES": "Number of pages in the zone currently in use.",
    "ORDER": "The order of the allocation request.",
    "TOTAL": "Total number of free blocks in this zone.",
    "SUITABLE": "Number of blocks suitable for the allocation.",
    "FREE": "Total number of free pages in the zone.",
    "SCORE": "Score representing fragmentation (higher is worse).",
    "SCORE1": "Score A: Score representing fragmentation based on metric A.",
    "SCORE2": "Score B: Score representing fragmentation based on metric B.",
    'NODE_ID':"zone is in this node",
    "FRAG_BAR": "A visual representation of the fragmentation score."
}

# 定义不同数据值的解释
value_explanations = {
    "Node ID": lambda value: f"Unique identifier of this node: {value}",
    "Number of Zones": lambda value: f"Number of memory zones: {value}",
    "PGDAT Pointer": lambda value: f"Memory address of pgdat structure: {value}",
}

all_node_data = []

def show_tooltip(text):
    """ 显示提示信息 """
    tooltip = urwid.Filler(urwid.Text(text, align='center'))
    overlay = urwid.Overlay(urwid.LineBox(tooltip),
                            loop.widget, align='center', width=('relative', 60),
                            valign='middle', height=('relative', 20),
                            min_width=40, min_height=5)
    
    loop.widget = overlay
    loop.draw_screen()  # 确保立即重绘屏幕以显示提示框

def add_or_update_node_data(node_data):
    """通过node_id来确保节点信息的唯一性并更新全局数组"""
    global all_node_data
    for new_node in node_data:
        existing_node = next((node for node in all_node_data if node['node_id'] == new_node['node_id']), None)
        if existing_node:
            # 如果已经存在该node_id的信息，更新数据
            existing_node.update(new_node)
        else:
            # 如果是新node_id，添加到全局数组
            all_node_data.append(new_node)

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

def create_node_table(extfrag, args):
    """构建并显示所有 Node 信息"""
    rows = []
    
    # 定义表头
    header = ["Node ID", "Number of Zones", "PGDAT Pointer"]
    header_widgets = [urwid.AttrMap(urwid.Text(col, align='center'), 'header') for col in header]
    header_row = urwid.Columns(header_widgets)
    rows.append(header_row)  # 添加表头行
    
    # 获取节点数据并更新全局数组
    node_data = extfrag.get_node_data()
    add_or_update_node_data(node_data.values())

    # 遍历全局数组中的所有节点并将其数据添加到表格行中
    for node in all_node_data:
        cell_widgets = [
            urwid.Text(str(node['node_id']), align='center'),
            urwid.Text(str(node['nr_zones']), align='center'),
            urwid.Text(str(node['pgdat_ptr']), align='center')
        ]
        row = urwid.Columns(cell_widgets)
        rows.append(row)  # 将每个节点的信息添加为一行

    # 将所有行组合成一个表格
    table = urwid.Pile(rows)
    table_with_scroll = urwid.Filler(table, valign='top')
    return table_with_scroll

def create_zone_table(extfrag, args):
    """构建并显示Zone信息"""
    rows = []
    if args.score_a:
        header = ["COMM", "ZONE_PFN", "SUM_PAGES", "FACT_PAGES", 
                  "ORDER", "TOTAL", "SUITABLE", "FREE", "SCORE1","NODE_ID"]
        if args.bar:
            header.append("FRAG_BAR")
    elif args.score_b:
        header = ["COMM", "ZONE_PFN", "SUM_PAGES", "FACT_PAGES", 
                  "ORDER", "TOTAL", "SUITABLE", "FREE", "SCORE2","NODE_ID"]
        if args.bar:
            header.append("FRAG_BAR")
    else:
        header = ["COMM", "ZONE_PFN", "SUM_PAGES", "FACT_PAGES", 
                  "ORDER", "TOTAL", "SUITABLE", "FREE", "SCORE1", "SCORE2","NODE_ID"]
        if args.bar:
            header.append("FRAG_BAR")

    header_widgets = [urwid.AttrMap(ClickableText(urwid.Text(col, align='center'), col, col), 'header') for col in header]
    header_row = urwid.Columns(header_widgets)
    rows.append(header_row)

    zone_data = extfrag.get_zone_data()

    for comm, zones in zone_data.items():
        for zone in zones:
            if args.node_id is not None and zone.get('node_id') != args.node_id:
                continue
            if args.comm is not None and zone.get('comm') != args.comm:
                continue
            if args.score_a:
                columns = ["comm", "zone_pfn", "spanned_pages", "present_pages", 
                           "order", "free_blocks_total", "free_blocks_suitable", "free_pages", "scoreA","node_id"]
            elif args.score_b:
                columns = ["comm", "zone_pfn", "spanned_pages", "present_pages", 
                           "order", "free_blocks_total", "free_blocks_suitable", "free_pages", "scoreB","node_id"]
            else:
                columns = ["comm", "zone_pfn", "spanned_pages", "present_pages", 
                           "order", "free_blocks_total", "free_blocks_suitable", "free_pages", "scoreA", "scoreB","node_id"]

            cell_widgets = []
            for col in columns:
                value = str(zone.get(col, ""))
                text = urwid.Text(value, align='center')
                clickable_text = urwid.AttrMap(ClickableText(text, col, value), 'body', focus_map='reversed')
                cell_widgets.append(clickable_text)
            if args.bar:
                score = float(zone.get("scoreB" , 0))
                frag_bar = generate_fragmentation_bar(score)
                bar_widget = urwid.Text(frag_bar, align='center')
                cell_widgets.append(bar_widget)
            row = urwid.Columns(cell_widgets)
            rows.append(row)

    table = urwid.Pile(rows)
    table_with_scroll = urwid.Filler(table, valign='top')
    return table_with_scroll

def generate_fragmentation_bar(score, max_length=20):
    """生成用于显示碎片化程度的条形图"""
    proportion = min(max(score, 0), 1)
    bar_length = int(proportion * max_length)
    return  '#' * bar_length + '-' * (max_length - bar_length) 

def refresh_data(loop, user_data):
    """刷新数据并更新界面"""
    global main_widget
    extfrag, args = user_data
    if args.node_info:
        main_widget = create_node_table(extfrag, args)
    else:
        main_widget = create_zone_table(extfrag, args)
    loop.widget = main_widget
    loop.set_alarm_in(args.delay, refresh_data, user_data) 

def handle_input(key):
    """处理键盘输入以关闭提示框"""
    if isinstance(loop.widget, urwid.Overlay):
        handle_tooltip_input(key)  # 处理提示框输入
    else:
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

class ClickableText(urwid.WidgetWrap):
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
        parser.add_argument('-d', '--delay', type=int, help='Delay between updates in seconds', default=2)
        parser.add_argument('-n', '--node_info', action='store_true', help='Output node information')
        parser.add_argument('-i', '--node_id', type=int, help='Specify Node ID to get zone information')
        parser.add_argument('-c', '--comm', type=str, help='Filter by comm name')
        parser.add_argument('-e', '--score_a', action='store_true', help='Only output score_a')
        parser.add_argument('-u', '--score_b', action='store_true', help='Only output score_b')
        parser.add_argument('-s', '--output_count', action='store_true', help='Output fragmentation count')
        parser.add_argument('-b', '--bar', action='store_true', help='Display fragmentation bar')
        args = parser.parse_args()

        extfrag = ExtFrag(interval=args.delay if args.delay else 0, output_count=args.output_count,
                          output_score_a=args.score_a, output_score_b=args.score_b)

        global loop, main_widget

        if args.node_info:
            main_widget = create_node_table(extfrag, args)
        else:
            main_widget = create_zone_table(extfrag, args)

        loop = urwid.MainLoop(main_widget, palette, unhandled_input=handle_input)

        loop.set_alarm_in(args.delay, refresh_data, (extfrag, args))

        loop.run()
    except KeyboardInterrupt:
        pass  

if __name__ == "__main__":
    main()
