
#include <uapi/linux/ptrace.h>
#include <linux/mm.h>
#include <linux/gfp.h>

struct data_t {
    u64 pfn;
    int alloc_order;
    int fallback_order;
    int alloc_migratetype;
    int fallback_migratetype;
    int change_ownership;
    u64 index;
};

// 定义 perf_event 输出
BPF_PERF_OUTPUT(events);
BPF_HASH(counts_map, u32, u64);

TRACEPOINT_PROBE(kmem, mm_page_alloc_extfrag) {
    u32 cpu_id = bpf_get_smp_processor_id();  // 获取当前 CPU ID
    u64 *count = counts_map.lookup(&cpu_id);
    if (count) {
        (*count)++;
    } else {
        u64 zero = 1;
        counts_map.update(&cpu_id, &zero);
    }

    struct data_t data = {};
    data.pfn = args->pfn;
    data.alloc_order = args->alloc_order;
    data.fallback_order = args->fallback_order;
    data.alloc_migratetype = args->alloc_migratetype;
    data.fallback_migratetype = args->fallback_migratetype;
    data.change_ownership = args->change_ownership;

    // 读取当前 CPU 的计数值
    u64 *count_updated = counts_map.lookup(&cpu_id);
    data.index = count_updated ? *count_updated : 0;

    events.perf_submit(args, &data, sizeof(data));

    return 0;
}