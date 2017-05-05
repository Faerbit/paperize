#!/usr/bin/env python3

import argparse
from base64 import b64encode, b64decode
from sys import stderr
from textwrap import fill
import traceback
from os.path import join, isfile
from tempfile import TemporaryDirectory
from hashlib import sha256

PAPERIZE_VERSION = "v1.0.2"

QR_VERSION = 21

MAX_LENGTH = {
    "L": 635,
    "M": 627,
    "Q": 455,
    "H": 369,
}

FILE_HEADER = "---pprzv1:1/{parts}:n:{file_name}---\n"

PART_HEADER = "---pprzv1:{part}/{parts}---\n"

PART_TRAILER = "\n---pprz:end---"

FIND_TRAILER = "---pprz:end---"

CHECKSUM = "\n---sha256sum:{sum}---"

TEMPLATE_HEADER = (
    "# Paperzied Backup\n"
    "_Paperize Version {version}_\n\n"
    "## Backup of file `{file_name}` \n"
    "To restore this file scan the QR codes and "
    "paste them into a plain text file (or several).\n\n"
    "Then use `paperize file FILE [FILE ...]` to restore the file.\n\n"
    "Alternatively, if you don't have the _paperize_ tool handy, you can just "
    "remove the _paperize_ tags and newlines and feed the rest through a "
    "base64 decoding.\n\n"
    "URL to source code: <https://github.com/faerbit/paperize>\n\n"
)

FILE_NAME = "qr_part_{i}.png"

TEMPLATE_PART = (
    "![File `{file_name}` part {part}/{parts}]({file_path}){{width=95%}}\n\n"
)

def mode_file(file_names):
    """Convert file_names contents back into the original file."""
    file_contents = ""
    for file_name in file_names:
        with open(file_name) as file:
            file_contents += file.read()
    parts = []
    file_contents = file_contents.replace("\n", "")
    # extract checksum
    begin = file_contents.find("---sha256sum")
    # find finds the beginning so we have to add 3
    end = file_contents[begin+3:].find("---")
    checksum = file_contents[begin:begin+end+6]
    file_contents = file_contents.replace(checksum, "")
    checksum = checksum.replace("---", "")
    checksum = checksum.split(":")[1]
    # extract parts
    while file_contents:
        end = file_contents.find(FIND_TRAILER)
        end = end + len(FIND_TRAILER)
        parts.append(file_contents[:end])
        file_contents = file_contents[end:]
    data = None
    no_parts = 0
    read_parts = None
    file_name = ""
    for part in parts:
        part_data, part_no, part_no_parts, part_file_name = parse_part(part)
        if (no_parts == 0):
            no_parts = part_no_parts
            data = [""] * no_parts
            read_parts = [0] * no_parts
            data[part_no] = part_data
            read_parts[part_no] = 1
        else:
            if (part_no_parts != no_parts):
                print(f"Number of total parts is inconsistent: "
                    f"{part_no_parts} != {no_parts}. Aborting.", file=stderr)
                exit(2)
            data[part_no] = part_data
            read_parts[part_no] = 1
        if part_file_name:
            file_name = part_file_name
    if (sum(read_parts) != no_parts):
        print("Not all parts present:", file=stderr)
        for i, _ in enumerate(read_parts):
            if read_parts[i] != 1:
                print(f"Part {i+1} is missing.", file=stderr)
        exit(2)
    if (isfile(file_name)):
        print(f"File {file_name} exists already. Aborting.", file=stderr)
        exit(2)
    data = "".join(data)
    data = b64decode(data)
    with open(file_name, "xb") as file:
        file.write(data)
    hash = sha256()
    hash.update(data)
    if (checksum != hash.hexdigest()):
        print("Checksum does not match! File might be corrupt!", file=stderr)
        exit(2)

def parse_part(part):
    """
    Parse one part. Returns (data, part_no, no_parts, file_name).
    file_name will be None for all but the first part.
    """
    # delete trailer
    part = part.replace(FIND_TRAILER, "")
    # extract header
    begin = part.find("---")
    part = part[begin:]
    end = part[3:].find("---")
    header = part[:end+6]
    data = part[end+6:]
    header = header.replace("---", "")
    header = header.split(":")
    part_no, no_parts = header[1].split("/")
    file_name = (lambda x: x[3] if len(x) == 4 else None)(header)
    # subtract one from part_no -> one based index to zero base index
    return (data, int(part_no) - 1, int(no_parts), file_name)


def mode_paper(file_name, ec_level):
    """
    Convert file_name's content into printable pdf using error correction level
    ec_level.
    """
    # import here to enable mode_file to work with stdlib only
    import qrcode
    import pypandoc
    ERROR_CORRECTION = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }
    # read file
    file_name = file_name[0]
    data = ""
    with open(file_name, "rb") as file:
        data = file.read()
    # calculate sha256 hash
    hash = sha256()
    hash.update(data)
    hash_string = hash.hexdigest()
    # convert to base64
    data = b64encode(data).decode("utf-8")
    # split data
    parts = len(data)//MAX_LENGTH[ec_level]
    split_data = prepare_data(data, parts, MAX_LENGTH[ec_level], file_name,
            hash_string)
    if (len(split_data) != parts):
        split_data = prepare_data(data, len(split_data),
                MAX_LENGTH[ec_level], file_name, hash_string)
    with TemporaryDirectory() as tmpdir:
        for i, part in enumerate(split_data, 1):
            img = qrcode.make(part,
                error_correction=ERROR_CORRECTION[ec_level])
            img.save(join(tmpdir, FILE_NAME.format(i=i)))
        markdown = TEMPLATE_HEADER.format(version=PAPERIZE_VERSION,
            file_name=file_name)
        for i in range(1, len(split_data) + 1):
            markdown += TEMPLATE_PART.format(part=i, parts=len(split_data),
                file_name=file_name,
                file_path=join(tmpdir, FILE_NAME.format(i=i)))
        pdf = pypandoc.convert_text(markdown, "pdf", format="md",
                outputfile=f"{file_name}_paperized.pdf",
                extra_args=["-V", "geometry:margin=1.5cm"])

def prepare_data(data, no_parts, part_length, file_name, hashsum):
    """
    Split data into no_parts chunks, while also adding the headers and
    trailers.
    """
    ret = []
    file_header = FILE_HEADER.format(parts=no_parts, file_name=file_name)
    first_part_length = part_length - len(file_header) - len(PART_TRAILER)
    first_part = fill(data, 80)[:first_part_length]
    ret.append(file_header +  first_part + PART_TRAILER)
    data = fill(data, 80)[first_part_length:]
    i = 2
    while data:
        data = data.replace("\n", "")
        part_header = PART_HEADER.format(part=i, parts=no_parts)
        length = part_length - len(part_header) - len(PART_TRAILER)
        part = fill(data, 80)[:length]
        ret.append(part_header + part + PART_TRAILER)
        data = fill(data, 80)[length:]
        i += 1
    checksum = CHECKSUM.format(sum=hashsum)
    if (len(ret[-1]) + len(checksum) < part_length):
        ret[-1] = ret[-1] + checksum
    else:
        ret.append(PART_HEADER.format(part=len(ret)+1, parts=no_parts)[:-1]
                + PART_TRAILER + checksum)
    return ret


def main():
    parser = argparse.ArgumentParser(description =
            "Convert binary file to printable QR codes and back."
            "Will output a printable pdf file",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("mode", metavar="MODE", help=
            "Either \"paper\" or \"file\". Can be shortened. \"paper\" "
            "produces QR codes and \"file\" produces the original file.")
    parser.add_argument("file", metavar="FILE", nargs="+", help=
            "Either the file which should be exported "
            "or the plain text input file(s) for import." )
    parser.add_argument("-l", "--level", default="M", help=
            "Error correction level for QR codes. "
            "Accepts L (7%%), M (15%%), Q (25%%), and H (30%%).",
            choices=["L", "M", "Q", "H",], type=str.upper)
    args = parser.parse_args()
    if not ("paper".find(args.mode.lower()) == 0 or
            "file".find(args.mode.lower()) == 0):
        print("Could not recognize MODE argument. Please use \"paper\" "
        "or \"file\" or a shortened version of these.", file=stderr)
        exit(1)

    if ("file".find(args.mode.lower()) == 0):
        mode_file(args.file)
    else:
        if len(args.file) > 1:
            print("Only one file for \"paper\" mode supported.", file=stderr)
            exit(1)
        mode_paper(args.file, args.level)

if __name__ == "__main__":
    main()

