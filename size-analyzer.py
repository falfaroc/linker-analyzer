#!/usr/bin/env python3

import sys
import argparse

flash_addr_begin = 0x8000000
flash_length = 0xF0000
flash_addr_end = flash_addr_begin + flash_length

ram_addr_begin = 0x20000000
ram_length = 0x20000
ram_addr_end = ram_addr_begin + ram_length


def parse_lines(lines, max_flash, max_ram):
    flash_total = 0
    ram_total = 0

    for line in lines:
        if "addr" in line:
            break

    for line in lines:
        line = line.split()

        if len(line) != 3:
            continue

        if ".data" in line[0]:
            flash_total += int(line[1], 16)
            ram_total += int(line[1], 16)
            continue

        if int(line[2], 16) > flash_addr_begin and int(line[2], 16) < flash_addr_end:
            flash_total += int(line[1], 16)
        elif int(line[2], 16) > ram_addr_begin and int(line[2], 16) < ram_addr_end:
            ram_total += int(line[1], 16)

    percentage = "{:.2f}%".format(100*flash_total/max_flash)
    print("Flash Total:", flash_total, "/", max_flash, "(", percentage, ")")

    percentage = "{:.2f}%".format(100*ram_total/max_ram)
    print("RAM Total:", ram_total, "/", max_ram, "(", percentage, ")")


def strip_to_memory(lines):
    for line in lines:
        if line.strip() == "Memory Configuration":
            break


def retrieve_size_max(lines):
    max_flash = 0
    max_ram = 0

    for line in lines:
        if line.startswith("RAM"):
            section = line.split()
            max_ram = int(section[2], 16)
        elif line.startswith("FLASH"):
            section = line.split()
            max_flash = int(section[2], 16)
        elif line.strip() == "Linker script and memory map":
            break

    return max_flash, max_ram


def parse_map_file(lines):
    strip_to_memory(lines)
    return retrieve_size_max(lines)


def analyze(args):
    max_flash = flash_length
    max_ram = ram_length

    with open(args.map_file) as f:
        lines = iter(f)

        max_flash, max_ram = parse_map_file(lines)

    with open(args.size_file) as f:
        lines = iter(f)

        parse_lines(lines, max_flash, max_ram)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Summarises the size of each object file in an ld linker map.')
    parser.add_argument(
        'size_file', help="A size file generated using the size command.")
    parser.add_argument(
        'map_file', help="A map file generated to retrieve extra content from the map file.")
    args = parser.parse_args()

    analyze(args)
