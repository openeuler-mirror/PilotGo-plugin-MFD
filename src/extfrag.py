#!/usr/bin/env python3
from bpfcc import BPF
import os
import time
import ctypes

class ExtFrag:
    def __init__(self, interval=2, output_score_a=False, output_score_b=False,output_count=False,zone_info=False):
        self.interval = interval
        self.output_score_a = output_score_a
        self.output_score_b = output_score_b
        self.output_count = output_count
        self.zone_info = zone_info
        
 

        if self.output_count:
            self.b = BPF(src_file="./bpf/extfraginfo.c")
        else:
            self.b = BPF(src_file="./bpf/fraginfo.c")
        delay_key = 0
        self.b["delay_map"][delay_key] = ctypes.c_int(interval)

    
    def calculate_scoreA(self, score_a):
        score_a_int_part = int(score_a) // 1000
        score_a_dec_part = int(score_a) % 1000
        return f"{score_a_int_part:2d}.{score_a_dec_part:03d}"

    def calculate_scoreB(self, score_b):
        score_b_int_part = int(score_b) // 1000
        score_b_dec_part = int(score_b) % 1000
        return f"{score_b_int_part:2d}.{score_b_dec_part:03d}"

    def get_zone_data(self,filter_node_id=None):
        zone_data_dict = {}
        zone_map = self.b["zone_map"]

        for key, value in zone_map.items():
            comm = value.name.decode('utf-8', 'replace').rstrip('\x00')
            node_id =value.node_id
            if filter_node_id is not None and node_id != filter_node_id:
                continue
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
            _comm = value.pcomm.decode('utf-8', 'replace').rstrip('\x00')
            data = {
                'pcomm':_comm,
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
        while True:
            try:
                time.sleep(self.interval)
            except KeyboardInterrupt:
                exit()
