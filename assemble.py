#!/usr/bin/python3
import sys
import json


def load_opcodes():
    with open('opcodes.json', 'r') as f:
        op_codes = json.load(f)
    return op_codes


def sanitize(inp):
    return ' '.join(
        inp.replace('\n', ' ').replace('0x', '').split()
    )


def compile_main(code):
    OP_CODES = load_opcodes()
    return ''.join([OP_CODES.get(block, block)
                    for block in sanitize(code).split()])


def main():
    with open(sys.argv[1], 'r') as f:
        data = f.read()

    data = compile_main(data)
    data = print('data: 0x', data.lower(), sep='')


if __name__ == '__main__':
    main()
