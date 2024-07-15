from bcc import BPF
import os

# 判断系统是否为 NUMA
def is_numa():
    nodes_path = "/sys/devices/system/node/"
    try:
        nodes = [node for node in os.listdir(nodes_path) if node.startswith("node")]
        if len(nodes) > 1:
            return True
    except FileNotFoundError:
        pass
    return False

isUMA = not is_numa()

# BPF 程序
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/mm.h>
#include <linux/gfp.h>

// 内存节点信息结构
struct pgdat_info {
    u64 pgdat_ptr;
    int nr_zones;
    int node_id;
};

// 区域信息结构
struct zone_info {
    u64 zone_ptr;
    u64 zone_start_pfn;
    u64 spanned_pages;
    u64 present_pages;
    char name[32];
    int order;
    int score_a;
    int score_b;
};

struct contig_page_info {
    unsigned long free_pages;
    unsigned long free_blocks_total;
    unsigned long free_blocks_suitable;
};

// 定义事件
BPF_PERF_OUTPUT(pgdat_events);
BPF_PERF_OUTPUT(zone_events);

static int unusable_free_index(unsigned int order, struct contig_page_info *info)
{
    if (info->free_pages == 0)
        return 1000;

    return div_u64((info->free_pages - (info->free_blocks_suitable << order)) * 1000ULL, info->free_pages);
}

static int __fragmentation_index(unsigned int order, struct contig_page_info *info)
{
    unsigned long requested = 1UL << order;

    if (WARN_ON_ONCE(order > MAX_ORDER))
        return 0;

    if (!info->free_blocks_total)
        return 0;

    if (info->free_blocks_suitable)
        return -1000;

    return 1000 - div_u64((1000 + (div_u64(info->free_pages * 1000ULL, requested))), info->free_blocks_total);
}

static void fill_contig_page_info(struct zone *zone, unsigned int suitable_order, struct contig_page_info *info)
{
    unsigned int order;

    info->free_pages = 0;
    info->free_blocks_total = 0;
    info->free_blocks_suitable = 0;

    for (order = 0; order <= MAX_ORDER; order++) {
        unsigned long blocks;
        unsigned long nr_free;

        bpf_probe_read_kernel(&nr_free, sizeof(nr_free), &zone->free_area[order].nr_free);
        blocks = nr_free;
        info->free_blocks_total += blocks;

        info->free_pages += blocks << order;

        if (order >= suitable_order)
            info->free_blocks_suitable += blocks << (order - suitable_order);
    }
}

// kprobe 钩子函数
int kprobe__rmqueue_bulk(struct pt_regs *ctx, struct zone *zone, unsigned int order, unsigned long count, struct list_head *list, int migratetype, unsigned int alloc_flags) {
    struct pgdat_info pgdat_data = {};
    struct zone_info zone_data = {};
    struct pglist_data *pgdat;
    struct zone *z;
    int i, tmp, index;
    unsigned int a_order;

    pgdat = zone->zone_pgdat;
    pgdat_data.pgdat_ptr = (u64)pgdat;
    pgdat_data.nr_zones = pgdat->nr_zones;
    pgdat_data.node_id = pgdat->node_id;

    pgdat_events.perf_submit(ctx, &pgdat_data, sizeof(pgdat_data));

    for (i = 0; i < MAX_NR_ZONES; i++) {
        if (i >= pgdat_data.nr_zones) {
            break;
        }

        z = &pgdat->node_zones[i];
        zone_data.zone_ptr = (u64)z;
        zone_data.zone_start_pfn = z->zone_start_pfn;
        zone_data.spanned_pages = z->spanned_pages;
        zone_data.present_pages = z->present_pages;
        bpf_probe_read_kernel_str(&zone_data.name, sizeof(zone_data.name), z->name);

        for (a_order = 0; a_order <= MAX_ORDER; ++a_order) {
            zone_data.order = a_order;

            struct contig_page_info ctg_info;
            fill_contig_page_info(z, a_order, &ctg_info);
            tmp = unusable_free_index(a_order, &ctg_info);
            zone_data.score_b = tmp;
            index = __fragmentation_index(a_order, &ctg_info);
            zone_data.score_a = index;
            zone_events.perf_submit(ctx, &zone_data, sizeof(zone_data));
        }
    }

    return 0;
}
"""

# 加载 BPF 程序
b = BPF(text=bpf_text)

# 定义输出回调函数
def print_pgdat_event(cpu, data, size):
    event = b["pgdat_events"].event(data)
    if isUMA:
        print("Your system is UMA!\n")
    else:
        print("Your system is NUMA\n")

    print("Node{} pgdat_ptr: 0x{:x}  nr_zones: {}    \n".format(event.node_id, event.pgdat_ptr, event.nr_zones))
    print(" COMM   START_PFN  SUM_PAGES FACT_PAGES  ORDER   SCORE1      SCORE2    ")

def print_zone_event(cpu, data, size):
    event = b["zone_events"].event(data)
    zone_name = event.name.decode('utf-8', 'replace').rstrip('\x00')
    score_b_int_part = event.score_b // 1000
    score_b_dec_part = event.score_b % 1000
    score_a_int_part = event.score_a // 1000
    score_a_dec_part = event.score_a % 1000
    print(f" {zone_name}       {event.zone_start_pfn}          {event.spanned_pages}     {event.present_pages}        {event.order}       {score_a_int_part:2d}.{score_a_dec_part:03d}      {score_b_int_part}.{score_b_dec_part:03d}     ")

# 监听事件并输出结果
b["pgdat_events"].open_perf_buffer(print_pgdat_event)
b["zone_events"].open_perf_buffer(print_zone_event)

print("Tracing... Press Ctrl-C to end.")

while True:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()
