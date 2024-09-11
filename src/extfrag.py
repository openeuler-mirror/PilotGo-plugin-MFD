#!/usr/bin/env python3
from bpfcc import BPF
import os
import time
import ctypes

def get_node_data_addr():
    with open("/proc/kallsyms", "r") as f:
        for line in f:
            if "node_data" in line:
                return int(line.split()[0], 16)
    return None
class ExtFrag:
    def __init__(self, interval=2, output_score_a=False, output_score_b=False,output_count=False):
        self.isNUMA = self.is_numa()
        self.interval = interval
        self.output_score_a = output_score_a
        self.output_score_b = output_score_b
        self.output_count = output_count
        
 

        if self.output_count:
            self.b = BPF(src_file="./bpf/extfraginfo.c")
        else:
            self.b = BPF(src_file="./bpf/numafraginfo.c")
        delay_key = 0
        self.b["delay_map"][delay_key] = ctypes.c_int(interval)

    def is_numa(self):
        nodes_path = "/sys/devices/system/node/"
        try:
            nodes = [node for node in os.listdir(nodes_path) if node.startswith("node")]
            return len(nodes) > 1
        except FileNotFoundError:
            return False

    def calculate_scoreA(self, score_a):
        score_a_int_part = int(score_a) // 1000
        score_a_dec_part = int(score_a) % 1000
        return f"{score_a_int_part:2d}.{score_a_dec_part:03d}"

    def calculate_scoreB(self, score_b):
        score_b_int_part = int(score_b) // 1000
        score_b_dec_part = int(score_b) % 1000
        return f"{score_b_int_part:2d}.{score_b_dec_part:03d}"

    def get_zone_data(self):
        zone_data_dict = {}
        zone_map = self.b["zone_map"]

        for key, value in zone_map.items():
            comm = value.name.decode('utf-8', 'replace').rstrip('\x00')
            data = {
                'comm': comm,
                'zone_pfn': value.zone_start_pfn,
                'spanned_pages': value.spanned_pages,
                'present_pages': value.present_pages,
                'order': value.order,
                'free_blocks_total': value.free_blocks_total,
                'free_blocks_suitable': value.free_blocks_suitable,
                'free_pages': value.free_pages,
                'scoreA': self.calculate_scoreA(value.score_a),
                'scoreB': self.calculate_scoreB(value.score_b),
                'node_id': value.node_id  
            }
            if comm not in zone_data_dict:
                zone_data_dict[comm] = []
            zone_data_dict[comm].append(data)
            for comm in zone_data_dict:
                zone_data_dict[comm].sort(key=lambda x: x['order'])

        return zone_data_dict

    def get_node_data(self):
        node_data_dict = {}
        pgdat_map = self.b["pgdat_map"]

        for key, value in pgdat_map.items():
            data = {
                'pgdat_ptr': value.pgdat_ptr,
                'nr_zones': value.nr_zones,
                'node_id': value.node_id
            }
            node_id = value.node_id
            node_data_dict[node_id] = data

        return node_data_dict
    def get_count_data(self):
        count_data_list = []
        counts_map = self.b["counts_map"]  # 'counts_map' 是 BPF 程序中的哈希表名

        # 从BPF哈希表中提取所有数据
        for key, value in counts_map.items():
            data = {
                'pcomm':value.pcomm,
                'pid': value.pid,
                'pfn': value.pfn,
                'alloc_order': value.alloc_order,
                'fallback_order': value.fallback_order,
                'count': value.count
                
            }
            count_data_list.append(data)

        # 根据 'count' 字段进行降序排序
        count_data_list.sort(key=lambda x: x['count'], reverse=True)

        return count_data_list

    def run(self):
        # if self.output_count:
        #     print("%-7s %-10s %-12s %-15s %-18s %-22s" % (
        #       "COMM",  "PID", "PFN", "ALLOC_ORDER", "FALLBACK_ORDER","COUNT"
        #     ))
        while True:
            try:
                # self.b.perf_buffer_poll(timeout=100)
                time.sleep(self.interval)
            except KeyboardInterrupt:
                exit()
