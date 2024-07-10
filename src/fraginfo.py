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

// 区域信息结构
struct zone_info {
    u64 pgdat_ptr;
    u64 zone_ptr;
    u64 zone_start_pfn;
    u64 spanned_pages;
    u64 present_pages;
    char name[32];
};

// 内存节点信息结构
struct pgdat_info {
    u64 pgdat_ptr;
    int nr_zones;
    int node_id;
};

// 定义 event
BPF_PERF_OUTPUT(pgdat_events);
BPF_PERF_OUTPUT(zone_events);

int kprobe__rmqueue_bulk(struct pt_regs *ctx, struct zone *zone, unsigned int order, unsigned long count, struct list_head *list, int migratetype, unsigned int alloc_flags) {
    struct pgdat_info pgdat_data = {};
    struct zone_info zone_data = {};
    struct pglist_data *pgdat;
    struct zone *z;
    int i;

    // 获取 pgdat 结构及信息
    pgdat = zone->zone_pgdat;
    pgdat_data.pgdat_ptr = (u64)pgdat;
    pgdat_data.nr_zones = pgdat->nr_zones;
    pgdat_data.node_id = pgdat->node_id;

    // 提交 pgdat 数据到用户空间
    pgdat_events.perf_submit(ctx, &pgdat_data, sizeof(pgdat_data));

    // 采集并提交每个 zone 的信息
    #pragma unroll
    for (i = 0; i < MAX_NR_ZONES; i++) {  // 假设最多有4个zone
        if (i >= pgdat_data.nr_zones) {
            break;
        }
        z = &pgdat->node_zones[i];
        zone_data.pgdat_ptr = (u64)pgdat;
        zone_data.zone_ptr = (u64)z;
        zone_data.zone_start_pfn = z->zone_start_pfn;
        zone_data.spanned_pages = z->spanned_pages;
        zone_data.present_pages = z->present_pages;
        bpf_probe_read_kernel_str(&zone_data.name, sizeof(zone_data.name), z->name);

        // 提交 zone 数据到用户空间
        zone_events.perf_submit(ctx, &zone_data, sizeof(zone_data));
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

    print("内存节点的信息：")
    print("pgdat_ptr: 0x{:x}  nr_zones: {}  node_id: {}  \n".format(event.pgdat_ptr, event.nr_zones, event.node_id))

def print_zone_event(cpu, data, size):
    event = b["zone_events"].event(data)
    zone_name = event.name.decode('utf-8', 'replace').rstrip('\x00')
    print(f"ZONE {zone_name}：")
    print(" zone_start_pfn  包含的页 管理的页")
    print(f"     {event.zone_start_pfn}          {event.spanned_pages}     {event.present_pages}")


# 监听事件并输出结果
b["pgdat_events"].open_perf_buffer(print_pgdat_event)
b["zone_events"].open_perf_buffer(print_zone_event)

print("Tracing... Press Ctrl-C to end.")

while True:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        break
