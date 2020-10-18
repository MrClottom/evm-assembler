#!/usr/bin/python3

# ECA stands for Ethereum Code Assembly

import sys
from compile import compile_eca


def main():
    with open(sys.argv[1], 'r') as f:
        code = f.read()

    res = compile_eca(code)

    print('res:', res)


if __name__ == '__main__':
    main()
