#!/usr/bin/env python3
import argparse
import urwid
import traceback 
from extfrag import ExtFrag

# 定义颜色调色板
palette = [
    ('header', 'light blue', ''),
    ('body', 'light green', ''),
    ('highlight', 'light red', ''),
    ('reversed', 'standout', ''),
    ('critical', 'dark red', ''),  
]


# 列标题的解释字典
column_explanations = {
    "Node ID": "The unique identifier of the memory node.",
    "Number of Zones": "The number of memory zones associated with this node.",
    "PGDAT Pointer": "The memory address of the pgdat structure for this node.",
    "ZONE_COMM": "The name of the memory zone, e.g., DMA, Normal.",
    "ZONE_PFN": "Starting page frame number of the memory zone.",
    "SUM_PAGES": "Total number of pages in the zone.",
    "FACT_PAGES": "Number of pages in the zone currently in use.",
    "ORDER": "The order of the allocation request.",
    "TOTAL": "Total number of free blocks in this zone.",
    "SUITABLE": "Number of blocks suitable for the allocation.",
    "FREE": "Total number of free pages in the zone.",
    "SCORE": "Score representing fragmentation (higher is worse).",
    "extfrag_index": "Score A: Score representing fragmentation based on metric A.",
    "unusable_index": "Score B: Score representing fragmentation based on metric B.",
    'NODE_ID': "Unique identifier for the node associated with this zone.",
    "FRAG_BAR": "A visual representation of the fragmentation score, where more '#' characters indicate higher fragmentation.",
    "PCOMM": "The name of the process that triggered the event",
    "PID":"The process ID associated with the event, which uniquely identifies the process that initiated the memory allocation or fallback.",
    "PFN":"Page Frame Number, representing the index of the physical page in memory involved in the allocation or fallback.",
    "ALLOC_ORDER":"The order (in terms of power of 2 pages) of the memory allocation request. For example, an order of 0 refers to a single page, while an order of 2 refers to 4 contiguous pages.",
    "FALLBACK_ORDER":"The order of the memory block that was actually allocated when a fallback occurred, possibly smaller or different than the original request.",
    "COUNT":"The number of occurrences of the event, typically counting how many times this allocation or fallback has happened during the trace.",
}



all_node_data = []
def show_tooltip(text):
    """ 显示提示信息 """
    tooltip = urwid.Filler(urwid.Text(text, align='center'))
    overlay = urwid.Overlay(urwid.LineBox(tooltip),
                            loop.widget, align='center', width=('relative', 40),
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
        show_tooltip(explanation)

def handle_tooltip_input(key):
    """处理提示框输入，按任意键返回主界面"""
    loop.widget = main_widget  # 返回主界面

def create_node_table(extfrag, args):
    """构建并显示所有 Node 信息"""
    rows = []
    
    # 定义表头并使用 ClickableText
    header = ["Node ID", "Number of Zones", "PGDAT Pointer"]
    header_widgets = [urwid.AttrMap(ClickableText(urwid.Text(col, align='center'), col, col), 'header') for col in header]
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
    rows = []
    base_header = ["ZONE_COMM", "ZONE_PFN", "SUM_PAGES", "FACT_PAGES", 
                  "ORDER", "TOTAL", "SUITABLE", "FREE", "NODE_ID"]
    score_columns = []
    if args.score_a:
        score_columns.append("extfrag_index")
    elif args.score_b:
        score_columns.append("unusable_index")
    else:
        score_columns = ["extfrag_index", "unusable_index"]
    if args.bar:
        score_columns.append("FRAG_BAR")
    full_header = base_header + score_columns 

    header_widgets = [urwid.AttrMap(ClickableText(urwid.Text(col, align='center'), col, col), 'header') for col in full_header]
    header_row = urwid.Columns(header_widgets)
    rows.append(header_row)

    zone_data = extfrag.get_zone_data()

    for comm, zones in zone_data.items():
        for zone in zones:
            if args.node_id is not None and zone.get('node_id') != args.node_id:
                continue
            if args.comm is not None and zone.get('comm') != args.comm:
                continue

            # 确定是否整行标红
            try:
                order_value = int(zone.get("order", 0))
                scoreB_value = float(zone.get("scoreB", 0))
                critical_style = order_value >= 5 and scoreB_value >= 0.5
            except ValueError:
                critical_style = False

            style = 'critical' if critical_style else 'body'
            focus_style = 'highlight' if critical_style else 'reversed'
            if args.score_a:
                columns = ["comm", "zone_pfn", "spanned_pages", "present_pages", 
                       "order", "free_blocks_total", "free_blocks_suitable", "free_pages", "node_id", "scoreA"]
            elif args.score_b:
                columns = ["comm", "zone_pfn", "spanned_pages", "present_pages", 
                       "order", "free_blocks_total", "free_blocks_suitable", "free_pages", "node_id", "scoreB"]
            else:
                columns = ["comm", "zone_pfn", "spanned_pages", "present_pages", 
                       "order", "free_blocks_total", "free_blocks_suitable", "free_pages", "node_id", "scoreA", "scoreB"]
            cell_widgets = []
            for col in columns:
                value = str(zone.get(col, ""))
                text = urwid.Text(value, align='center')
                clickable_text = urwid.AttrMap(ClickableText(text, col, value), style, focus_map=focus_style)
                cell_widgets.append(clickable_text)
            if args.bar:
                score = float(zone.get("scoreB", 0))
                frag_bar = generate_fragmentation_bar(score)
                frag_bar_widget = ClickableText(urwid.Text(frag_bar, align='center'), "FRAG_BAR", frag_bar)
                cell_widgets.append(urwid.AttrMap(frag_bar_widget, style, focus_map=focus_style))

            row = urwid.Columns(cell_widgets)
            rows.append(row)

    table = urwid.Pile(rows)
    table_with_scroll = urwid.Filler(table, valign='top')
    return table_with_scroll
def create_score_table(extfrag, args):
    rows = []
    base_header = ["ZONE_COMM",  "NODE_ID","ORDER"]
    score_columns = []
    if args.score_a:
        score_columns.append("extfrag_index")
    elif args.score_b:
        score_columns.append("unusable_index")
    else:
        score_columns = ["extfrag_index", "unusable_index"]
    if args.bar:
        score_columns.append("FRAG_BAR")
    full_header = base_header + score_columns 

    header_widgets = [urwid.AttrMap(ClickableText(urwid.Text(col, align='center'), col, col), 'header') for col in full_header]
    header_row = urwid.Columns(header_widgets)
    rows.append(header_row)

    zone_data = extfrag.get_zone_data()

    for comm, zones in zone_data.items():
        for zone in zones:
            if args.node_id is not None and zone.get('node_id') != args.node_id:
                continue
            if args.comm is not None and zone.get('comm') != args.comm:
                continue

            # 确定是否整行标红
            try:
                order_value = int(zone.get("order", 0))
                scoreB_value = float(zone.get("scoreB", 0))
                critical_style = order_value >= 5 and scoreB_value >= 0.5
            except ValueError:
                critical_style = False

            style = 'critical' if critical_style else 'body'
            focus_style = 'highlight' if critical_style else 'reversed'
            if args.score_a:
                 columns = ["comm", "node_id","order", "scoreA"]
            elif args.score_b:
                columns = ["comm", "node_id","order", "scoreB"]
            else:
                columns = ["comm", "node_id","order", "scoreA", "scoreB"]
            cell_widgets = []
            for col in columns:
                value = str(zone.get(col, ""))
                text = urwid.Text(value, align='center')
                clickable_text = urwid.AttrMap(ClickableText(text, col, value), style, focus_map=focus_style)
                cell_widgets.append(clickable_text)
            if args.bar:
                score = float(zone.get("scoreB", 0))
                frag_bar = generate_fragmentation_bar(score)
                frag_bar_widget = ClickableText(urwid.Text(frag_bar, align='center'), "FRAG_BAR", frag_bar)
                cell_widgets.append(urwid.AttrMap(frag_bar_widget, style, focus_map=focus_style))

            row = urwid.Columns(cell_widgets)
            rows.append(row)

    table = urwid.Pile(rows)
    table_with_scroll = urwid.Filler(table, valign='top')
    return table_with_scroll

def create_event_table(extfrag,args):
    event_data = extfrag.get_count_data()
    rows = []
    headers = ["PCOMM", "PID", "PFN", "ALLOC_ORDER", "FALLBACK_ORDER","COUNT"]
    header_widgets = [urwid.AttrMap(ClickableText(urwid.Text(col, align='center'), col, col), 'header') for col in headers]
    header_row = urwid.Columns(header_widgets)
    rows.append(header_row)

    for event in event_data:
        cell_widgets = [urwid.Text(str(event[col.lower()]), align='center') for col in headers]
        row = urwid.Columns(cell_widgets)
        rows.append(row)

    table = urwid.Pile(rows)
    return urwid.Filler(table, valign='top')

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
    elif args.output_count:
        main_widget = create_event_table(extfrag,args)
    elif args.zone_info:
        main_widget = create_zone_table(extfrag,args)
    else:
        main_widget = create_score_table(extfrag,args)

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
        parser.add_argument('-c', '--comm', type=str, help='Filter by zone_comm name')
        parser.add_argument('-e', '--score_a', action='store_true', help='Only output extfrag_index')
        parser.add_argument('-u', '--score_b', action='store_true', help='Only output unusable_index')
        parser.add_argument('-s', '--output_count', action='store_true', help='Output fragmentation count')
        parser.add_argument('-b', '--bar', action='store_true', help='Display fragmentation bar')
        parser.add_argument('-z', '--zone_info', action='store_true', help='Display detailed zone information')

        args = parser.parse_args()
        
        extfrag = ExtFrag(interval=args.delay if args.delay else 2, output_count=args.output_count,
                          output_score_a=args.score_a, output_score_b=args.score_b,zone_info=args.zone_info)

        global loop, main_widget

        if args.node_info:
            main_widget = create_node_table(extfrag, args)
        elif args.output_count:
            main_widget = create_event_table(extfrag,args)
        elif args.zone_info:
            main_widget = create_zone_table(extfrag,args)
        else:
            main_widget = create_score_table(extfrag,args)

        loop = urwid.MainLoop(main_widget, palette, unhandled_input=handle_input)
        if args.output_count:
            loop.set_alarm_in(args.delay, refresh_data, (extfrag,args))
        else:
            loop.set_alarm_in(args.delay, refresh_data, (extfrag, args))

        loop.run()
    except KeyboardInterrupt:
        print("Exiting program...")
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # 打印出完整的堆栈跟踪信息

if __name__ == "__main__":
    main()