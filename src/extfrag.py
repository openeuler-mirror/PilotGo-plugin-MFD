#!/usr/bin/env python3
from bpfcc import BPF
import os
import time
import ctypes

class ExtFrag:
    def __init__(self, interval=2, output_extfrag_index=False, output_unusable_index=False,output_count=False,zone_info=False):
        self.interval = interval
        self.output_extfrag_index = output_extfrag_index
        self.output_unusable_index = output_unusable_index
        self.output_count = output_count
        self.zone_info = zone_info
        
 

        if self.output_count:
            self.b = BPF(src_file="./bpf/extfraginfo.c")
        else:
            self.b = BPF(src_file="./bpf/fraginfo.c")
        delay_key = 0
        self.b["delay_map"][delay_key] = ctypes.c_int(interval)

    
    def calculate_scoreA(self, extfrag_index):
        extfrag_index_int_part = int(extfrag_index) // 1000
        extfrag_index_dec_part = int(extfrag_index) % 1000
        return f"{extfrag_index_int_part:2d}.{extfrag_index_dec_part:03d}"

    def calculate_scoreB(self, unusable_index):
        unusable_index_int_part = int(unusable_index) // 1000
        unusable_index_dec_part = int(unusable_index) % 1000
        return f"{unusable_index_int_part:2d}.{unusable_index_dec_part:03d}"

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
    def get_view_data(self, filter_node_id=None):
        zone_data_dict = {}
        ret_dict={}
        zone_map = self.b["zone_map"]

        for key, value in zone_map.items():
            comm = value.name.decode('utf-8', 'replace').rstrip('\x00')
            node_id = value.node_id
            
            if filter_node_id is not None and node_id != filter_node_id:
                continue

            data = {
                'scoreB': self.calculate_scoreB(value.score_b),
                'order': value.order,
            }
            
            # 使用 (node_id, comm) 作为键
            zone_data_dict[(node_id, comm)] = data
        sorted_keys = sorted(zone_data_dict.keys())
        for key in sorted_keys:
            ret_dict[key]= zone_data_dict[key]
        return ret_dict
    def get_nr_zones(self, filter_node_id=None):
        node_zone_map = {} 
        zone_map = self.b["zone_map"]

        for key, value in zone_map.items():
            comm = value.name.decode('utf-8', 'replace').rstrip('\x00')
            node_id = value.node_id
            
            if filter_node_id is not None and node_id != filter_node_id:
                continue

            data = {
                'scoreB': self.calculate_scoreB(value.score_b),
                'order': value.order,
            }
            
            # 使用 (node_id, comm) 作为键
            if node_id not in node_zone_map:
                node_zone_map[node_id] = []  # 初始化列表
            node_zone_map[node_id].append(comm)  # 追加 comm

        return node_zone_map
    def get_node_data(self):
        node_data_dict = {}
        pgdat_map = self.b["pgdat_map"]
        zone_data = self.get_nr_zones()

        for key, value in pgdat_map.items():
            node_id = value.node_id
            nr_zones =  int(len(zone_data.get(node_id, []))/11)
            data = {
                'pgdat_ptr': value.pgdat_ptr,
                'nr_zones': nr_zones,
                'node_id': value.node_id
            }
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
