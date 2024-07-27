#!/usr/bin/env python3
import argparse
from extfrag import ExtFrag

def main():
    parser = argparse.ArgumentParser(description='watche mem frag')
    parser.add_argument('-d', '--interval', type=int, default=5, help='Set output interval in seconds')
    parser.add_argument('-e', '--score_a', action='store_true', help='Only output score_a ')
    parser.add_argument('-u', '--score_b', action='store_true', help='Only output score_b')

    args = parser.parse_args()


    if args.score_a:
        extfrag = ExtFrag(interval=args.interval, output_score_a=True, output_score_b=False)
    elif args.score_b:
        extfrag = ExtFrag(interval=args.interval, output_score_a=False, output_score_b=True)
    else:
        extfrag = ExtFrag(interval=args.interval)

    extfrag.run()

if __name__ == "__main__":
    main()
