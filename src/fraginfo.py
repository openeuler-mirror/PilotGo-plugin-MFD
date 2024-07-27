#!/usr/bin/env python3
from bcc import BPF
import os
import time


class ExtFrag:
    def __init__(self, interval=5, output_score_a=False, output_score_b=False, output_count=False):
        self.isUMA = not self.is_numa()
        self.interval = interval
        self.output_score_a = output_score_a
        self.output_score_b = output_score_b
        self.output_count = output_count
        if self.output_count:
            self.b = BPF(src_file="./bpf/extfraginfo.c")
        else:
            self.b = BPF(src_file="./bpf/fraginfo.c")

    def is_numa(self):
        nodes_path = "/sys/devices/system/node/"
        try:
            nodes = [node for node in os.listdir(nodes_path) if node.startswith("node")]
            if len(nodes) > 1:
                return True
        except FileNotFoundError:
            pass
        return False

    def output_data(self):
        print("Your system is {}!\n".format("UMA" if self.isUMA else "NUMA"))

        print("Node pgdat data:")
        for k, v in self.b["pgdat_map"].items():
            print("Node{} pgdat_ptr: 0x{:x}  nr_zones: {}\n".format(v.node_id, v.pgdat_ptr, v.nr_zones))

        zone_data_dict = {}
        for k, v in self.b["zone_map"].items():
            comm = v.name.decode('utf-8', 'replace').rstrip('\x00')
            if comm not in zone_data_dict:
                zone_data_dict[comm] = []
            zone_data_dict[comm].append(v)

        print("Zone data:")
        if self.output_score_a or self.output_score_b:
            print(f"{'COMM':>6} {'ZONE_PFN':>23} {'SUM_PAGES':>25} {'FACT_PAGES':>30} {'ORDER':>22} {'SCORE':>23}")
        else:
            print(f"{'COMM':>6} {'ZONE_PFN':>23} {'SUM_PAGES':>25} {'FACT_PAGES':>30} {'ORDER':>22} {'SCOREA':>23} {'SCOREB':>23}")

        for comm, zone_data_list in zone_data_dict.items():
            sorted_zone_data_list = sorted(zone_data_list, key=lambda x: x.order)
            for v in sorted_zone_data_list:
                score_b_int_part = v.score_b // 1000
                score_b_dec_part = v.score_b % 1000
                score_a_int_part = v.score_a // 1000
                score_a_dec_part = v.score_a % 1000
                if self.output_score_a:
                    print(f" {comm:<15}       {v.zone_start_pfn:<15}          {v.spanned_pages:<25}     {v.present_pages:<20}        {v.order:<15}       {score_a_int_part:2d}.{score_a_dec_part:03d}")
                elif self.output_score_b:
                    print(f" {comm:<15}       {v.zone_start_pfn:<15}          {v.spanned_pages:<25}     {v.present_pages:<20}        {v.order:<15}       {score_b_int_part:2d}.{score_b_dec_part:03d}")
                else:
                    print(f" {comm:<15}       {v.zone_start_pfn:<15}          {v.spanned_pages:<25}     {v.present_pages:<20}        {v.order:<15}       {score_a_int_part:2d}.{score_a_dec_part:03d}                  {score_b_int_part:2d}.{score_b_dec_part:03d}")
    
    # 定义输出回调函数
    def print_event(self,cpu, data, size):
        event = self.b["events"].event(data)

        
        print("%2d %4d %10lu %12d %15d %18d %18d %18d" % (
            cpu,
            event.index,
            event.pfn,
            event.alloc_order,
            event.fallback_order,
            event.alloc_migratetype,
            event.fallback_migratetype,
            event.change_ownership,
        ))
    def run(self):
        if self.output_count:
            print("%-4s %-7s %-10s %-12s %-15s %-18s %-18s %-18s" % (
        "CPU", "CALLS", "PFN", "ALLOC_ORDER", "FALLBACK_ORDER", "ALLOC_MIGRATETYPE", "FALLBACK_MIGRATETYPE", "CHANGE_OWNERSHIP"
        ))
            self.b["events"].open_perf_buffer(self.print_event)  
        while True:
            try:
                self.b.perf_buffer_poll(timeout=100)
                time.sleep(self.interval)
                if not self.output_count:
                   self.output_data()
            except KeyboardInterrupt:
                exit()
