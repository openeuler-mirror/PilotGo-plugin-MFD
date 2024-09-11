
#include <uapi/linux/ptrace.h>
#include <linux/mm.h>
#include <linux/gfp.h>
#include <linux/sched.h>

struct data_t {
    u64 pfn;
    int alloc_order;
    int fallback_order;
    pid_t pid;
    u64 count;
    char pcomm[32];
};

BPF_HASH(counts_map, pid_t, struct data_t );
BPF_HASH(last_time_map, u64, u64);
BPF_ARRAY(delay_map, int, 1);
TRACEPOINT_PROBE(kmem, mm_page_alloc_extfrag) {
    u64 *last_time, current_time;
  current_time = bpf_ktime_get_ns();  // 获取当前时间
  last_time = last_time_map.lookup(&current_time);
  int key = 0;
    int *delay_ptr = delay_map.lookup(&key);
    int delay;
    if (delay_ptr) {
        delay = *delay_ptr;
    }
  if (last_time && (current_time - *last_time < delay*1000000000)) {
    return 0; 
  }
  
    struct data_t *data, zero = {};
    pid_t pid = bpf_get_current_pid_tgid() >> 32; // 获取当前进程的PID

    // 尝试获取已有数据
    data = counts_map.lookup(&pid);
    if (!data) {
        // 如果没有对应PID的数据，初始化一个新的结构体
        zero.pid = pid;
        zero.pfn = args->pfn;
        zero.alloc_order =  args->alloc_order;
        zero.fallback_order = args->fallback_order;
        zero.count = 1;  // 初始化计数为1
         bpf_get_current_comm(&zero.pcomm, sizeof(zero.pcomm));
        counts_map.update(&pid, &zero);
    } else {
        // 如果找到了，更新结构体中的计数
        data->count += 1;
        data->pfn = args->pfn; // 更新最新的物理页框号
        data->alloc_order =  args->alloc_order;// 更新最新的请求内存阶数
        data->fallback_order = args->fallback_order; // 更新最新的实际分配内存阶数
         bpf_get_current_comm(&data->pcomm, sizeof(data->pcomm)); 
        counts_map.update(&pid, data);
    }
  
    return 0;
}

