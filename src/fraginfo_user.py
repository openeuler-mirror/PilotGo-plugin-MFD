#!/usr/bin/env python3
import argparse
from extfrag import ExtFrag

def main():
    parser = argparse.ArgumentParser(description='Watch memory fragmentation')
    parser.add_argument('-d', '--interval', type=int, default=5, help='Set output interval in seconds')
    parser.add_argument('-e', '--score_a', action='store_true', help='Only output score_a')
    parser.add_argument('-u', '--score_b', action='store_true', help='Only output score_b')
    parser.add_argument('-s', '--output_count', action='store_true', help='Output fragmentation count')
    parser.add_argument('-n', '--isNUMA', action='store_true', help='judge system is numa')
    args = parser.parse_args()
    if args.output_count:
        extfrag = ExtFrag(interval=args.interval,output_count=True)
    else:
        if not args.isNUMA:
            if args.score_a:
                extfrag = ExtFrag(interval=args.interval, output_score_a=True, output_score_b=False,isNUMA=False)
            elif args.score_b:
                extfrag = ExtFrag(interval=args.interval, output_score_a=False, output_score_b=True,isNUMA=False)
            else:
                extfrag = ExtFrag(interval=args.interval,isNUMA=False)
        else:
            if args.score_a:
                extfrag = ExtFrag(interval=args.interval, output_score_a=True, output_score_b=False,isNUMA=True)
            elif args.score_b:
                extfrag = ExtFrag(interval=args.interval, output_score_a=False, output_score_b=True,isNUMA=True)
            else:
                extfrag = ExtFrag(interval=args.interval,isNUMA=True)

    extfrag.run()

if __name__ == "__main__":
    main()
