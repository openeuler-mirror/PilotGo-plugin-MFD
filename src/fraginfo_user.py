#!/usr/bin/env python3
import argparse
import time
import curses
from extfrag import ExtFrag

def main(screen):
    curses.curs_set(0)  # 隐藏光标 
    screen.nodelay(True) 
    screen.clear()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)


    parser = argparse.ArgumentParser(description='Watch memory fragmentation with real-time updates')
    parser.add_argument('-d', '--delay', type=int, default=5, help='Delay between updates in seconds')
    parser.add_argument('-n', '--node_info', action='store_true', help='Output node information')
    parser.add_argument('-c', '--comm', type=str, help='Filter by comm name')
    parser.add_argument('-e', '--score_a', action='store_true', help='Only output score_a')
    parser.add_argument('-u', '--score_b', action='store_true', help='Only output score_b')
    parser.add_argument('-s', '--output_count', action='store_true', help='Output fragmentation count')
    args = parser.parse_args()

    extfrag = ExtFrag(interval=args.delay if args.delay else 0,output_count=args.output_count,output_score_a=args.score_a,output_score_b=args.score_b)  
    saved_event_data = []  # 用于保存事件数据
    try:
        while True:
            screen.clear()
            row = 0
            max_rows, max_cols = screen.getmaxyx()

            if args.node_info:
                # 获取并打印节点信息
                node_data = extfrag.get_node_data()
                if not node_data:
                    screen.addstr(0, 0, "please wait...",curses.color_pair(4))
                else:
                    header = f"{'Node ID':>10} {'Number of Zones':>20} {'PGDAT Pointer':>25}\n"
                    screen.addstr(row, 0, header,curses.color_pair(4))
                    row += 1
                    for node_id, node in node_data.items():
                        line = f"{node_id:>10} {node['nr_zones']:>20} {node['pgdat_ptr']:>25}\n"
                        if row < max_rows - 1:  # 确保不超出屏幕行数
                            if len(line) < max_cols - 1:  # 确保行内字符数不超出屏幕宽度
                                screen.addstr(row, 0, line)
                                row += 1
                            else:
                                screen.addstr(row, 0, line[:max_cols - 1])
                                row += 1
                    
            elif args.output_count:
                # 打印外碎片化发生的次数
                event_data = extfrag.get_event_data()
                saved_event_data.extend(event_data)
                header = f"{'COUNTS':>5} {'PFN':>10} {'ALLOC_ORDER':>25} {'FALLBACK_ORDER':>15} " \
                         f"{'ALLOC_MIGRATETYPE':>15} {'FALLBACK_MIGRATETYPE':>15} {'CHANGE_OWNERSHIP':>15}  \n"
                screen.addstr(0, 0, header,curses.color_pair(4))
                row =1
                for event in saved_event_data:
                    line = f"{event['index']:>5} {event['pfn']:>15} {event['alloc_order']:>15} {event['fallback_order']:>15} " \
                           f"{event['alloc_migratetype']:>15} {event['fallback_migratetype']:>15} {event['change_ownership']:>15}\n"
                    if row < max_rows - 1:  # 确保不超出屏幕行数
                        if len(line) < max_cols - 1:  # 确保行内字符数不超出屏幕宽度
                            screen.addstr(row, 0, line)
                            row += 1
                        else:
                            screen.addstr(row, 0, line[:max_cols - 1])
                            row += 1
                screen.refresh()
                if args.delay is not None:
                        time.sleep(args.delay)
                else:
                        time.sleep(1) 

            else:
                # 获取并打印区域信息
                zone_data = extfrag.get_zone_data()
                if args.score_a or args.score_b:
                    header = f"{'COMM':>5} {'ZONE_PFN':>15} {'SUM_PAGES':>15} {'FACT_PAGES':>15} " \
                         f"{'ORDER':>15} {'TOTAL':>15} {'SUITABLE':>15} {'FREE':>15} {'SCORE':>15} \n"
                else:
                    header = f"{'COMM':>5} {'ZONE_PFN':>15} {'SUM_PAGES':>15} {'FACT_PAGES':>15} " \
                         f"{'ORDER':>15} {'TOTAL':>15} {'SUITABLE':>15} {'FREE':>15} {'SCORE1':>15} {'SCORE2':>15}\n"
                screen.addstr(0, 0, header,curses.color_pair(4))
                row = 1
                for comm, zones in zone_data.items():
                    if args.comm and comm != args.comm:
                        continue  
                    for zone in zones:
                        color = curses.color_pair(1)
                        if zone['order'] > 5 and float(zone['scoreB']) > 0.5:
                             color = curses.color_pair(2)  # 红色，表示高风险
                        if args.score_a :
                            line = f"{zone['comm']:>5} {zone['zone_pfn']:>15} {zone['spanned_pages']:>15} " \
                               f"{zone['present_pages']:>15} {zone['order']:>15} {zone['free_blocks_total']:>15} " \
                               f"{zone['free_blocks_suitable']:>15} {zone['free_pages']:>15}  {zone['scoreA']:>15} \n"
                        elif  args.score_b:
                            line = f"{zone['comm']:>5} {zone['zone_pfn']:>15} {zone['spanned_pages']:>15} " \
                               f"{zone['present_pages']:>15} {zone['order']:>15} {zone['free_blocks_total']:>15} " \
                               f"{zone['free_blocks_suitable']:>15} {zone['free_pages']:>15}  {zone['scoreB']:>15} \n"
                        else:
                            line = f"{zone['comm']:>5} {zone['zone_pfn']:>15} {zone['spanned_pages']:>15} " \
                               f"{zone['present_pages']:>15} {zone['order']:>15} {zone['free_blocks_total']:>15} " \
                               f"{zone['free_blocks_suitable']:>15} {zone['free_pages']:>15}  {zone['scoreA']:>15} {zone['scoreB']:>15}\n"
                        if row < max_rows - 1:  # 确保不超出屏幕行数
                            if len(line) < max_cols - 1:  # 确保行内字符数不超出屏幕宽度
                                screen.addstr(row, 0, line,color)
                                row += 1
                            else:
                                screen.addstr(row, 0, line[:max_cols - 1],color)
                                row += 1

            screen.refresh()
            time.sleep(args.delay)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    curses.wrapper(main)






