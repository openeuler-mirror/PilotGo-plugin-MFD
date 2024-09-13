#include <linux/gfp.h>
#include <linux/mm.h>
#include <uapi/linux/ptrace.h>
#define MAX_ORDER 10

struct pgdat_info {
  u64 pgdat_ptr;
  int nr_zones;
  int node_id;
};

struct zone_info {
  u64 zone_ptr;
  u64 zone_start_pfn;
  u64 spanned_pages;
  u64 present_pages;
  unsigned long free_pages;
  unsigned long free_blocks_total;
  unsigned long free_blocks_suitable;
  char name[32];
  int order;
  int score_a;
  int score_b;
  int node_id;
};
struct alloc_context {
	struct zonelist *zonelist;
	nodemask_t *nodemask;
	struct zoneref *preferred_zoneref;
	int migratetype;
	enum zone_type highest_zoneidx;
	bool spread_dirty_pages;
};
struct contig_page_info {
  unsigned long free_pages;
  unsigned long free_blocks_total;
  unsigned long free_blocks_suitable;
};


BPF_HASH(pgdat_map, u32, struct pgdat_info);
BPF_HASH(zone_map, u32, struct zone_info);
BPF_HASH(last_time_map, u64, u64);
BPF_ARRAY(delay_map, int, 1);

static int unusable_free_index(unsigned int order,
                               struct contig_page_info *info) {
  if (info->free_pages == 0)
    return 1000;
  return div_u64(
      (info->free_pages - (info->free_blocks_suitable << order)) * 1000ULL,
      info->free_pages);
}

static int __fragmentation_index(unsigned int order,
                                 struct contig_page_info *info) {
  unsigned long requested = 1UL << order;
  if (WARN_ON_ONCE(order > MAX_ORDER))
    return 0;
  if (!info->free_blocks_total)
    return 0;
  if (info->free_blocks_suitable)
    return -1000;
  return 1000 -
         div_u64((1000 + (div_u64(info->free_pages * 1000ULL, requested))),
                 info->free_blocks_total);
}

static void fill_contig_page_info(struct zone *zone,
                                  unsigned int suitable_order,
                                  struct contig_page_info *info) {
  unsigned int order;
  info->free_pages = 0;
  info->free_blocks_total = 0;
  info->free_blocks_suitable = 0;
  for (order = 0; order <= MAX_ORDER; order++) {
    unsigned long blocks;
    unsigned long nr_free;
    bpf_probe_read_kernel(&nr_free, sizeof(nr_free),
                          &zone->free_area[order].nr_free);
    blocks = nr_free;
    info->free_blocks_total += blocks;
    info->free_pages += blocks << order;
    if (order >= suitable_order)
      info->free_blocks_suitable += blocks << (order - suitable_order);
  }
}

int kprobe__get_page_from_freelist(struct pt_regs *ctx, gfp_t gfp_mask, unsigned int order, int alloc_flags,const struct alloc_context *ac) {
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
  struct pgdat_info pgdat_data = {};
  struct zone_info zone_data = {};
  struct pglist_data *pgdat;
  struct zone *z;
  int i, tmp, index;
  unsigned int a_order;
  u32 node_key = 0;

  pgdat=ac->preferred_zoneref->zone->zone_pgdat;
  pgdat_data.pgdat_ptr = (u64)pgdat;
  pgdat_data.nr_zones = pgdat->nr_zones;
  pgdat_data.node_id = pgdat->node_id;

  pgdat_map.update(&node_key, &pgdat_data);

  for (i = 0; i < MAX_NR_ZONES; i++) {
    if (i >= pgdat_data.nr_zones) {
      break;
    }
    z = &pgdat->node_zones[i];
    zone_data.zone_ptr = (u64)z;
    zone_data.zone_start_pfn = z->zone_start_pfn;
    zone_data.spanned_pages = z->spanned_pages;
    zone_data.present_pages = z->present_pages;
    zone_data.node_id = z->zone_pgdat->node_id;
    bpf_probe_read_kernel_str(&zone_data.name, sizeof(zone_data.name), z->name);
    for (a_order = 0; a_order <= MAX_ORDER; ++a_order) {
      zone_data.order = a_order;
      struct contig_page_info ctg_info;
      fill_contig_page_info(z, a_order, &ctg_info);
      zone_data.free_blocks_suitable = ctg_info.free_blocks_suitable;
      zone_data.free_blocks_total = ctg_info.free_blocks_total;
      zone_data.free_pages = ctg_info.free_pages;
  
      tmp = unusable_free_index(a_order, &ctg_info);
      zone_data.score_b = tmp;
      index = __fragmentation_index(a_order, &ctg_info);
      zone_data.score_a = index;
      zone_map.update(&key, &zone_data);
      key++;
    }
  }
  last_time_map.update(&current_time, &current_time);
  return 0;
}