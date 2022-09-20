#!/usr/bin/env python
# -*- coding: utf-8 -*-


def _print_usage() -> None:
    print(
        "Command line usage :\n"
        "- Download a dataset             : aac-ds-download [--root ROOT] [--verbose VERBOSE] [--force (false|true)] (clotho|audiocaps|macs) [ARGS...]\n"
        "- Check a installation directory : aac-ds-check [--root ROOT] [--verbose VERBOSE]\n"
        "- Print package install info     : aac-ds-info\n"
        "- Show this usage page           : aac-ds\n"
    )


if __name__ == "__main__":
    _print_usage()
