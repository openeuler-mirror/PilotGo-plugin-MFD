#!/usr/bin/env python3
from bcc import BPF
import os
import time


class ExtFrag:
    def __init__(self, interval=5, output_score_a=False, output_score_b=False, output_count=False,isNUMA=False):
        self.isNUMA =  self.is_numa()
        self.interval = interval
        self.output_score_a = output_score_a
        self.output_score_b = output_score_b
        self.output_count = output_count
        if self.output_count:
            self.b = BPF(src_file="./bpf/extfraginfo.c")
        elif not self.isNUMA:
            self.b=BPF(src_file="./bpf/fraginfo.c")
        else:
            self.b=BPF(src_file="./bpf/numafraginfo.c")

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
        print("Your system is {}!\n".format("NUMA" if self.isNUMA else "UMA"))
        if self.isNUMA:
            self.output_numa_info()
        else:
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
                print(f"{'COMM':>6} {'ZONE_PFN':>23} {'SUM_PAGES':>25} {'FACT_PAGES':>30} {'ORDER':>20} {'TOTAL':>23} {'SUITABLE':>15} {'FREE':>15} {'SCORE':>23}")
            else:
                print(f"{'COMM':>6} {'ZONE_PFN':>23} {'SUM_PAGES':>25} {'FACT_PAGES':>30} {'ORDER':>20} {'TOTAL':>23} {'SUITABLE':>15} {'FREE':>15} {'SCOREA':>23} {'SCOREB':>23}")

            for comm, zone_data_list in zone_data_dict.items():
                sorted_zone_data_list = sorted(zone_data_list, key=lambda x: x.order)
                for v in sorted_zone_data_list:
                    score_b_int_part = v.score_b // 1000
                    score_b_dec_part = v.score_b % 1000
                    score_a_int_part = v.score_a // 1000
                    score_a_dec_part = v.score_a % 1000
                    if self.output_score_a:
                        print(f" {comm:<15}       {v.zone_start_pfn:<15}          {v.spanned_pages:<25}     {v.present_pages:<20}        {v.order:<15}   {v.free_blocks_total:<15}   {v.free_blocks_suitable:<15}  {v.free_pages:<15}      {score_a_int_part:2d}.{score_a_dec_part:03d}")
                    elif self.output_score_b:
                        print(f" {comm:<15}       {v.zone_start_pfn:<15}          {v.spanned_pages:<25}     {v.present_pages:<20}        {v.order:<15}      {v.free_blocks_total:<15}   {v.free_blocks_suitable:<15}  {v.free_pages:<15}    {score_b_int_part:2d}.{score_b_dec_part:03d}")
                    else:
                        print(f" {comm:<15}       {v.zone_start_pfn:<15}          {v.spanned_pages:<25}     {v.present_pages:<20}        {v.order:<15}     {v.free_blocks_total:<15}   {v.free_blocks_suitable:<15}  {v.free_pages:<15}     {score_a_int_part:2d}.{score_a_dec_part:03d}                  {score_b_int_part:2d}.{score_b_dec_part:03d}")
        
    
    def output_data1(self):
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
            print(f"{'COMM':>6} {'ZONE_PFN':>23} {'SUM_PAGES':>25} {'FACT_PAGES':>30} {'ORDER':>20} {'TOTAL':>23} {'SUITABLE':>15} {'FREE':>15} {'SCORE':>23}")
        else:
            print(f"{'COMM':>6} {'ZONE_PFN':>23} {'SUM_PAGES':>25} {'FACT_PAGES':>30} {'ORDER':>20} {'TOTAL':>23} {'SUITABLE':>15} {'FREE':>15} {'SCOREA':>23} {'SCOREB':>23}")

        for comm, zone_data_list in zone_data_dict.items():
            sorted_zone_data_list = sorted(zone_data_list, key=lambda x: x.order)
            for v in sorted_zone_data_list:
                score_b_int_part = v.score_b // 1000
                score_b_dec_part = v.score_b % 1000
                score_a_int_part = v.score_a // 1000
                score_a_dec_part = v.score_a % 1000
                if self.output_score_a:
                    print(f" {comm:<15}       {v.zone_start_pfn:<15}          {v.spanned_pages:<25}     {v.present_pages:<20}        {v.order:<15}   {v.free_blocks_total:<15}   {v.free_blocks_suitable:<15}  {v.free_pages:<15}      {score_a_int_part:2d}.{score_a_dec_part:03d}")
                elif self.output_score_b:
                    print(f" {comm:<15}       {v.zone_start_pfn:<15}          {v.spanned_pages:<25}     {v.present_pages:<20}        {v.order:<15}      {v.free_blocks_total:<15}   {v.free_blocks_suitable:<15}  {v.free_pages:<15}    {score_b_int_part:2d}.{score_b_dec_part:03d}")
                else:
                    print(f" {comm:<15}       {v.zone_start_pfn:<15}          {v.spanned_pages:<25}     {v.present_pages:<20}        {v.order:<15}     {v.free_blocks_total:<15}   {v.free_blocks_suitable:<15}  {v.free_pages:<15}     {score_a_int_part:2d}.{score_a_dec_part:03d}                  {score_b_int_part:2d}.{score_b_dec_part:03d}")
    
    
    def output_numa_info(self):
        print("NUMA Node Information:")
        print("Node ID     Start PFN    NRZONE")
        for node_id, pgdat_data in self.b["pgdat_map"].items():
            print(f" {pgdat_data.node_id:>3}    {pgdat_data.pgdat_ptr:>10} {pgdat_data.nr_zones:>14}    ")
        zone_data_dict = {}
        for k, v in self.b["zone_map"].items():
            comm = v.name.decode('utf-8', 'replace').rstrip('\x00')
            if comm not in zone_data_dict:
                zone_data_dict[comm] = []
            zone_data_dict[comm].append(v)

        print("/n/nZone data:")
    
        print(f"{'COMM':>3} {'ZONE_PFN':>17} {'SUM_PAGES':>17} {'FACT_PAGES':>17} {'ORDER':>8} {'TOTAL':>12} {'SUITABLE':>12} {'FREE':>15} {'SCOREA':>15} {'SCOREB':>20}")

        for comm, zone_data_list in zone_data_dict.items():
            sorted_zone_data_list = sorted(zone_data_list, key=lambda x: x.order)
            for v in sorted_zone_data_list:
                score_b_int_part = v.score_b // 1000
                score_b_dec_part = v.score_b % 1000
                score_a_int_part = v.score_a // 1000
                score_a_dec_part = v.score_a % 1000
                
                print(f" {comm:<5}       {v.zone_start_pfn:<8}          {v.spanned_pages:<10}     {v.present_pages:<10}        {v.order:<5}     {v.free_blocks_total:<12}   {v.free_blocks_suitable:<12}  {v.free_pages:<8}     {score_a_int_part:2d}.{score_a_dec_part:03d}                  {score_b_int_part:2d}.{score_b_dec_part:03d}")
    
        
 # 定义输出回调函数
    def print_event(self,cpu, data, size):
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
    def run(self):
        if self.output_count:
            print("%-7s %-10s %-12s %-15s %-18s %-18s %-18s" % (
         "CALLS", "PFN", "ALLOC_ORDER", "FALLBACK_ORDER", "ALLOC_MIGRATETYPE", "FALLBACK_MIGRATETYPE", "CHANGE_OWNERSHIP"
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