#include <linux/gfp.h>
#include <linux/mm.h>
#include <linux/mmzone.h>  
#include <uapi/linux/ptrace.h>

#define MAX_ORDER 11  // 定义最大的 order

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

struct contig_page_info {
  unsigned long free_pages;
  unsigned long free_blocks_total;
  unsigned long free_blocks_suitable;
};

BPF_HASH(pgdat_map, u64, struct pgdat_info);
BPF_HASH(zone_map, u64, struct zone_info);
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
  for (order = 0; order < MAX_ORDER; order++) {
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

int kprobe__rmqueue_bulk(struct pt_regs *ctx, struct zone *zone,
                         unsigned int order, unsigned long count,
                         struct list_head *list, int migratetype,
                         unsigned int alloc_flags) {
 
  struct pglist_data *pgdat;
  struct zone *z;
  struct zoneref *zref;
  int i, tmp, index;
  unsigned int a_order;

  pgdat = zone->zone_pgdat;

  for (i = 0; i < MAX_NR_ZONES; i++) {
     struct zone_info zone_data = {};
    struct pgdat_info pgdat_data = {};
    struct pgdat_info *a_pgdat;
    struct pglist_data *pgdata;
    u64 node_key,zone_key;
    zref = &pgdat->node_zonelists[ZONELIST_FALLBACK]._zonerefs[i];
    z = zref->zone;  
    if (!z)
      continue;

    //更新node信息
    pgdata = z->zone_pgdat;
    if (!pgdata)
      continue;
    node_key = (u64)pgdata;
    a_pgdat = pgdat_map.lookup(&node_key);
    if (!a_pgdat) {
      pgdat_data.pgdat_ptr = (u64)pgdata->node_start_pfn;
      pgdat_data.nr_zones = pgdata->nr_zones;
      pgdat_data.node_id = pgdata->node_id;
      pgdat_map.update(&node_key, &pgdat_data);
    }
    //更新zone信息
    zone_data.zone_ptr = (u64)z;
    
    zone_data.zone_start_pfn = z->zone_start_pfn;
    zone_data.spanned_pages = z->spanned_pages;
    zone_data.present_pages = z->present_pages;
    zone_data.node_id = z->zone_pgdat->node_id;
    bpf_probe_read_kernel_str(&zone_data.name, sizeof(zone_data.name), z->name);

    for (a_order = 0; a_order < MAX_ORDER; ++a_order) {
      zone_data.order = a_order;
      zone_key =zone_data.zone_ptr+zone_data.order;

      bpf_trace_printk("%s====%llu====%llu", zone_data.name,
                       zone_data.zone_start_pfn, zone_data.node_id);
      struct contig_page_info ctg_info;
      fill_contig_page_info(z, a_order, &ctg_info);
      zone_data.free_blocks_suitable = ctg_info.free_blocks_suitable;
      zone_data.free_blocks_total = ctg_info.free_blocks_total;
      zone_data.free_pages = ctg_info.free_pages;

      bpf_trace_printk("----------%llu====%llu====%llu",
                       zone_data.free_blocks_total,
                       zone_data.free_blocks_suitable, zone_data.free_pages);
      tmp = unusable_free_index(a_order, &ctg_info);
      zone_data.score_b = tmp;
      index = __fragmentation_index(a_order, &ctg_info);
      zone_data.score_a = index;
      bpf_trace_printk("-++++++++++%d===%d", zone_data.score_a,
                       zone_data.score_b);
      zone_map.update(&zone_key, &zone_data);
      zone_key++;
    }
  }
  return 0;
}