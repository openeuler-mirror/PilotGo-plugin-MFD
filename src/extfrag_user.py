#!/usr/bin/env python3
import argparse
import traceback 
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
    parser.add_argument('-d', '--delay', type=int, help='Delay between updates in seconds', default=2)   
    parser.add_argument('-n', '--node_info', action='store_true', help='Output node information')
    parser.add_argument('-i', '--node_id', type=int, help='Specify Node ID to get zone information')
    parser.add_argument('-c', '--comm', type=str, help='Filter by zone_comm name')
    parser.add_argument('-e', '--score_a', action='store_true', help='Only output extfrag_index')
    parser.add_argument('-u', '--score_b', action='store_true', help='Only output unusable_index')
    parser.add_argument('-s', '--output_count', action='store_true', help='Output fragmentation count')
        # parser.add_argument('-b', '--bar', action='store_true', help='Display fragmentation bar')
    parser.add_argument('-z', '--zone_info', action='store_true', help='Display detailed zone information')
    args = parser.parse_args()

    extfrag = ExtFrag(interval=args.delay if args.delay else 2, output_count=args.output_count,
                          output_score_a=args.score_a, output_score_b=args.score_b,zone_info=args.zone_info)

    try:
        while True:
            screen.clear()
            row = 0
            max_rows, max_cols = screen.getmaxyx()

            if args.node_info:
                # 获取并打印节点信息
                node_data = extfrag.get_node_data()
                if not node_data:
                    screen.addstr(row, 0, header,curses.color_pair(4))
                else:
                    header = f"{'Node ID':>45} {'Number of Zones':>65} {'PGDAT Pointer':>70}\n"
                    screen.addstr(row, 0, header,curses.color_pair(4))
                    row += 1
                    for node_id, node in node_data.items():
                        line = f"{node_id:>40} {node['nr_zones']:>60} {node['pgdat_ptr']:>77}\n"
                        if row < max_rows - 1:  # 确保不超出屏幕行数
                            if len(line) < max_cols - 1:  # 确保行内字符数不超出屏幕宽度
                                screen.addstr(row, 0, line)
                                row += 1
                            else:
                                screen.addstr(row, 0, line[:max_cols - 1])
                                row += 1
            elif args.output_count:
                event_data = extfrag.get_count_data()
                header = f"{'COMM':>25} {'PID':>30} {'PFN':>45}" \
                         f"{'ALLOC_ORDER':>45} {'FALLBACK_ORDER':>45} {'COUNT':>35} \n"
                screen.addstr(0, 0, header,curses.color_pair(4))
                row =1
                for event in event_data:
                    line = f"{event['pcomm']:>25} {event['pid']:>30} {event['pfn']:>45}{event['alloc_order']:>45} {event['fallback_order']:>45} {event['count']:>35} \n"
                    if row < max_rows - 1:  # 确保不超出屏幕行数
                        if len(line) < max_cols - 1:  # 确保行内字符数不超出屏幕宽度
                            screen.addstr(row, 0, line)
                            row += 1
                        else:
                            screen.addstr(row, 0, line[:max_cols - 1])
                            row += 1

            elif args.zone_info:
                # 获取并打印区域信息
                if args.node_id is not None:
                    zone_data = extfrag.get_zone_data(args.node_id)
                else:
                    zone_data = extfrag.get_zone_data()
                if args.score_a:
                     header = f"{'ZONE_COMM':>5} {'ZONE_PFN':>15} {'SUM_PAGES':>25} {'FACT_PAGES':>25} " \
                         f"{'ORDER':>22} {'TOTAL':>25} {'SUITABLE':>25} {'FREE':>25} {'NODE_ID':>25} {'extfrag_index':>25} \n"
                elif args.score_b:
                    header = f"{'ZONE_COMM':>5} {'ZONE_PFN':>15} {'SUM_PAGES':>25} {'FACT_PAGES':>25} " \
                         f"{'ORDER':>22} {'TOTAL':>25} {'SUITABLE':>25} {'FREE':>25} {'NODE_ID':>25} {'unusable_index':>25} \n"
                else:
                    header = f"{'ZONE_COMM':>5} {'ZONE_PFN':>15} {'SUM_PAGES':>25} {'FACT_PAGES':>25} " \
                         f"{'ORDER':>22} {'TOTAL':>25} {'SUITABLE':>25} {'FREE':>25} {'NODE_ID':>25} {'extfrag_index':>25} {'unusable_index':>25}\n"
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
                            line = f"{zone['comm']:^6} {zone['zone_pfn']:^25} {zone['spanned_pages']:^25} " \
                               f"{zone['present_pages']:^25} {zone['order']:^25} {zone['free_blocks_total']:^25} " \
                               f"{zone['free_blocks_suitable']:^25} {zone['free_pages']:^25} {zone['node_id']:^25} {zone['scoreA']:^20} \n"
                        elif  args.score_b:
                            line = f"{zone['comm']:^6} {zone['zone_pfn']:^25} {zone['spanned_pages']:^25} " \
                               f"{zone['present_pages']:^25} {zone['order']:^25} {zone['free_blocks_total']:^25} " \
                               f"{zone['free_blocks_suitable']:^25} {zone['free_pages']:^25} {zone['node_id']:^25} {zone['scoreB']:^20} \n"
                        else:
                            line = f"{zone['comm']:^6} {zone['zone_pfn']:^25} {zone['spanned_pages']:^25} " \
                               f"{zone['present_pages']:^25} {zone['order']:^25} {zone['free_blocks_total']:^25} " \
                               f"{zone['free_blocks_suitable']:^25} {zone['free_pages']:^25} {zone['node_id']:^25} {zone['scoreA']:^20} {zone['scoreB']:^25}\n"
                        if row < max_rows - 1:  # 确保不超出屏幕行数
                            if len(line) < max_cols - 1:  # 确保行内字符数不超出屏幕宽度
                                screen.addstr(row, 0, line)
                                row += 1
                            else:
                                screen.addstr(row, 0, line[:max_cols - 1])
                                row += 1
            else:
                 # 获取并打印关键信息
                if args.node_id is not None:
                    zone_data = extfrag.get_zone_data(args.node_id)
                else:
                    zone_data = extfrag.get_zone_data()
                color = curses.color_pair(1)
                if args.score_a:
                    header =f"{'ZONE_COMM':<30}  {'NODE_ID':<23} {'ORDER':>40} {'extfrag_index':>52} \n"
                elif args.score_b:
                    header = f"{'ZONE_COMM':<30}  {'NODE_ID':<23} {'ORDER':>40}  {'unusable_index':>52} \n"
                else:
                    header = f"{'ZONE_COMM':<30}  {'NODE_ID':<23} {'ORDER':>40} {'extfrag_index':>52} {'unusable_index':>30} \n"
                screen.addstr(row, 0, header,curses.color_pair(4))
                row = 1
                for comm, zones in zone_data.items():
                    if args.comm and comm != args.comm:
                        continue  
                    for zone in zones:
                        if zone['order'] > 5 and float(zone['scoreB']) > 0.5:
                             color = curses.color_pair(2)  # 红色，表示高风险
                        if args.score_a :
                            line = f"{zone['comm']:^7}  {zone['node_id']:^55}  {zone['order']:^55} {zone['scoreA']:^45} \n"
                        elif  args.score_b:
                            line = f"{zone['comm']:^7}  {zone['node_id']:^55}  {zone['order']:^55} {zone['scoreB']:^45} \n"
                        else:
                            line = f"{zone['comm']:^7}  {zone['node_id']:^55}  {zone['order']:^55} {zone['scoreA']:^45}  {zone['scoreB']:^15} \n"
                        if row < max_rows - 1:  # 确保不超出屏幕行数
                            if len(line) < max_cols - 1:  # 确保行内字符数不超出屏幕宽度
                                screen.addstr(row, 0, line)
                                row += 1
                            else:
                                screen.addstr(row, 0, line[:max_cols - 1])
                                row += 1


            screen.refresh()
            time.sleep(args.delay)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    curses.wrapper(main)



