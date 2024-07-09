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



// 事件采集的数据
struct data_t {
    u64 zone_ptr;
    u64 pgdat_ptr;
    int nr_zones;
    int node_id;
};

// 定义 event
BPF_PERF_OUTPUT(events);



int kprobe__rmqueue_bulk(struct pt_regs *ctx, struct zone *zone, unsigned int order, unsigned long count, struct list_head *list, int migratetype, unsigned int alloc_flags) {
    struct data_t data = {};
    struct pglist_data *pgdat;

    // 获取 pgdat 结构和信息
    data.zone_ptr = (u64)zone;
    pgdat = zone->zone_pgdat;
    data.pgdat_ptr = (u64)pgdat;
    data.nr_zones = pgdat->nr_zones;
    data.node_id = pgdat->node_id;

    // 提交数据到用户空间
    events.perf_submit(ctx, &data, sizeof(data));

    return 0;
}
"""

# 加载 BPF 程序
b = BPF(text=bpf_text)

# 输出函数
def print_event(cpu, data, size):
    event = b["events"].event(data)
    if isUMA:
        print("Your system is UMA!\n")
    else:
        print("Your system is NUMA\n")

    print("内存节点的信息：")
    print("pgdat_ptr: 0x{:x}  nr_zones: {}  node_id: {}".format(event.pgdat_ptr, event.nr_zones, event.node_id))


b["events"].open_perf_buffer(print_event)

print("Tracing... Press Ctrl-C to end.")

while True:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        break
