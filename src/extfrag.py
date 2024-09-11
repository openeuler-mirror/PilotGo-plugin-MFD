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
        elif not self.isNUMA:
            self.b = BPF(src_file="./bpf/fraginfo.c")
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

    def print_event(self, cpu, data, size):
        event = self.b["events"].event(data)
        print(" %4d %10lu %12d %15d %18d %18d %18d" % (
            event.index,
            event.pfn,
            event.alloc_order,
            event.fallback_order,
            event.alloc_migratetype,
            event.fallback_migratetype,
            event.change_ownership,
        ))

    def get_event_data(self):
        events_data = []

        def collect_event(cpu, data, size):
            event = self.b["events"].event(data)
            event_dict = {
                'index': event.index,
                'pfn': event.pfn,
                'alloc_order': event.alloc_order,
                'fallback_order': event.fallback_order,
                'alloc_migratetype': event.alloc_migratetype,
                'fallback_migratetype': event.fallback_migratetype,
                'change_ownership': event.change_ownership,
            }
            events_data.append(event_dict)

        if self.output_count:
            try:
                self.b["events"].open_perf_buffer(collect_event)
                self.b.perf_buffer_poll(timeout=100)
            except KeyboardInterrupt:
                print("Event collection interrupted by user.")
            except Exception as e:
                print(f"An error occurred while collecting events: {e}")

        return events_data

    def run(self):
        if self.output_count:
            print("%-7s %-10s %-12s %-15s %-18s %-18s %-18s" % (
                "CALLS", "PFN", "ALLOC_ORDER", "FALLBACK_ORDER", "ALLOC_MIGRATETYPE", "FALLBACK_MIGRATYPE", "CHANGE_OWNERSHIP"
            ))
            self.b["events"].open_perf_buffer(self.print_event)
        while True:
            try:
                self.b.perf_buffer_poll(timeout=100)
                time.sleep(self.interval)
            except KeyboardInterrupt:
                exit()
