import argparse
import re


class section_size():
    flash = 0
    ram = 0

    def total(self):
        return self.flash + self.ram

    def add_section(self, section, size):
        if section.startswith('.text') or section.startswith('.image_header') or section.startswith('.isr_vector') or section.startswith('.rodata'):
            self.flash += size
        elif section.startswith('.data') or section.startswith('.bss') or section.startswith('.heap'):
            self.ram += size


def print_combine(source, size):
    # base_pattern = r".*\/lib\/(\D*)\/.*\/(src\/.*)\*.o"
    base_pattern = r".*\/lib\/([a-z1-9-]*)\/.*\/(src.*\/)"
    root_pattern = r"(\.).*(src\/.*)\*.o"

    g1 = "app"
    g2 = ""

    if match := re.match(base_pattern, source):
        g1 = match.group(1)
        g2 = match.group(2)
    elif match := re.match(root_pattern, source):
        g2 = match.group(2)

    if (not args.repository or args.repository == g1) and g2:
        print("{: >30} {: >30} {: >30} {: >30} {: >30}".format(
            g1, g2, size.flash, size.ram, size.total()))


def print_raw(source, size):
    base_pattern = r".*\/lib\/([a-z1-9-]*)\/.*src\/(.*)"
    root_pattern = r".*src\/(.*)"

    g1 = "app"
    g2 = ""

    if match := re.match(base_pattern, source):
        g1 = match.group(1)
        g2 = match.group(2)
    elif match := re.match(root_pattern, source):
        g2 = match.group(1)

    if (not args.repository or args.repository == g1) and g2:
        print("{: >30} {: >55} {: >30} {: >30} {: >30}".format(
            g1, g2, size.flash, size.ram, size.total()))


def print_summary(size_by_source, max_flash, max_ram):
    sources = list(size_by_source.keys())
    sources.sort(key=lambda x: size_by_source[x].total())
    size_total = flash_total = ram_total = 0

    if not args.release:
        if args.combine:
            print("{: >30} {: >30} {: >30} {: >30} {: >30}".format("Name", "Location",
                                                                   "Flash Size (bytes)", "RAM Size (bytes)", "Total Size (bytes)"))
        else:
            print("{: >30} {: >55} {: >30} {: >30} {: >30}".format("Name", "Location",
                                                                   "Flash Size (bytes)", "RAM Size (bytes)", "Total Size (bytes)"))
    else:
        print("Release map file provided, unable to properly parse content. For further information, provide a debug map file and remove the release flag.")

    for source in sources:
        section = size_by_source[source]
        flash_total += section.flash
        ram_total += section.ram
        size_total += section.total()

        if not args.release:
            if args.combine:
                print_combine(source, section)
            else:
                print_raw(source, section)

    print("\n{: >30} {: >30} {: >30} {: >30}".format("Memory Region", "Used Size",
                                                     "Region Size", "Percentage Used"))

    percentage = "{:.2f}%".format(100*ram_total/max_ram)
    print("{: >30} {: >30} {: >30} {: >30}".format(
        "RAM", ram_total, max_ram, percentage))

    percentage = "{:.2f}%".format(100*flash_total/max_flash)
    print("{: >30} {: >30} {: >30} {: >30}".format(
        "Flash", flash_total, max_flash, percentage))


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


def parse_memory_map(lines):
    size_by_source = {}
    current_section = None
    split_line = None

    for line in lines:
        line = line.strip('\n')
        if split_line:
            # Glue a line that was split in two back together
            if line.startswith(' ' * 16):
                line = split_line + line
            else:
                print("Warning: discarding line ", split_line)
            split_line = None

        if line.startswith((".", " .", " *fill*")):
            # Don't split paths containing spaces
            pieces = line.split(None, 3)

            if line.startswith("."):
                # Note: this line might be wrapped, with the size of the section
                # on the next line, but we ignore the size anyway and will ignore that line
                current_section = pieces[0]
            elif len(pieces) == 1 and len(line) > 14:
                # ld splits the rest of this line onto the next if the section name is too long
                split_line = line
            elif len(pieces) >= 3 and "=" not in pieces and "before" not in pieces:
                if pieces[0] == "*fill*":
                    source = pieces[0]
                    size = int(pieces[-1], 16)
                else:
                    source = pieces[-1]
                    size = int(pieces[-2], 16)

                if args.combine:
                    if '.a(' in source:
                        # path/to/archive.a(object.o)
                        source = source[:source.index('.a(') + 2]
                    elif source.endswith('.o'):
                        where = max(source.rfind('\\'), source.rfind('/'))
                        if where:
                            source = source[:where + 1] + '*.o'

                if source not in size_by_source:
                    size_by_source[source] = section_size()
                size_by_source[source].add_section(current_section, size)

    return size_by_source


def analyze(args):
    with open(args.map_file) as f:
        lines = iter(f)

        strip_to_memory(lines)
        max_flash, max_ram = retrieve_size_max(lines)

        size_by_source = parse_memory_map(lines)

    print_summary(size_by_source, max_flash, max_ram)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Summarises the size of each object file in an ld linker map.')
    parser.add_argument(
        'map_file', help="A map file generated by passing -M/--print-map to ld during linking.")
    parser.add_argument('--combine', action='store_true',
                        help="All object files in an .a archive or in a directory are combined")
    parser.add_argument('--repository',
                        help="Isolate single repository.")
    parser.add_argument('--release', action='store_true',
                        help="Informs that the map file is of a release build.")
    args = parser.parse_args()

    analyze(args)
