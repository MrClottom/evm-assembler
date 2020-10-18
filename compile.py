from functools import reduce
import json
import math
from toolz import curry
from parse import parse
from grammar import OP_CODES


def op_code(instruction):
    return int(OP_CODES[instruction], 16)


def check_functions(funcs):
    for name, func in funcs.items():
        if func['in_args'] > 16:
            raise ValueError(f"Error: '{name}' trying to accept\
 {func['in_args']} args, cannot accept more than 16")
        if func['out_args'] > 16:
            raise ValueError(f"Error: '{name}' returning {func['out_args']}\
 args, cannot return more than 16")
        if any(insts['type'] == 'op'
               and insts['name'].startswith('PUSH')
               and insts['value']['type'] == 'var'
               for insts in func['body']):
            raise TypeError(f"Error: cannot use var in function")


def verify_push(push_op):
    if not push_op['name'].startswith('PUSH'):
        raise TypeError('non PUSH op given')

    push_size = (op_code(push_op['name']) & 0x1f) + 1
    literal_size = len(push_op['value']['value'])//2
    if literal_size != push_size:
        raise ValueError(f"Error: bytes literal size {literal_size}\
 != the push size ({push_size}) at instruction [{i}] in {name}()")


def compile_func_data(func, name):
    pre_link_size = 3  # wrapping JUMPDEST _func_ SWAPx JUMP
    links = []
    for i, inst in enumerate(func['body']):
        if inst['type'] == 'op':
            if inst['name'].startswith('PUSH'):
                verify_push(inst)
                pre_link_size += 1 + literal_size
            else:
                pre_link_size += 1
        elif inst['type'] == 'call':
            links.append(inst['name'])
        else:
            raise ValueError(f"Error: invalid type '{inst['type']}'")

    return pre_link_size, links


def create_push(bytes_):
    if len(bytes_) > 32:
        raise ValueError(f'bytestring too long {len(bytes_)} > 32')
    if not bytes_:
        raise ValueError('provided empty bytes')

    push = op_code('PUSH1') | (len(bytes_) - 1)

    return bytes([push, *bytes_])


def byte_size(x):
    return math.floor(math.log(x, 0xff)) + 1


def to_bytes(n):
    return n.to_bytes(byte_size(n), 'big')


def compile_call_alloc(ins, name):
    def compile_call(cur_pos, positions):
        # <?> <-- pos
        # PUSH_x r
        # SWAP_n
        # SWAP_n-1
        #   ...
        # SWAP1
        # PUSH d
        # JUMP
        # JUMPDEST
        dest_pos = positions[name]
        dest_push_size = byte_size(dest_pos) + 1

        return_push_size = 2
        return_jump_pos = cur_pos + return_push_size + ins + dest_push_size + 2
        return_push_size = byte_size(return_jump_pos)
        return_jump_pos = cur_pos + return_push_size + ins + dest_push_size + 2
        return_push_size = byte_size(return_jump_pos)
        return_jump_pos = cur_pos + return_push_size + ins + dest_push_size + 2

        return bytes([
            *create_push(to_bytes(return_jump_pos)),
            *(op_code('SWAP1') | n for n in range(ins-1, -1, -1)),
            *create_push(dest_pos.to_bytes(dest_push_size, 'big')),
            *create_push(to_bytes(dest_pos)),
            op_code('JUMP'),
            op_code('JUMPEST')
        ])

    return compile_call, 2 + ins + 2 + 2


def compile_var_push_alloc(name, var_name):
    push_size = (op_code(name) & 0x1f) + 1
    size = push_size + 1

    def compile_var_push(_, positions):
        if byte_size(positions[var_name]) > push_size:
            print(
                f'Warning: truncating 0x{to_bytes(positions[var_name]).hex()}',
                f'to {push_size} bytes'
            )
        return bytes([
            op_code(name),
            *positions[var_name][-push_size:]
        ])

    return compile_var_push, size


def alloc_compiled_bytes(alloc, bytes_):
    if alloc[-1]['type'] != 'ops':
        alloc.append({
            'type': 'ops',
            'size': 0,
            'compiled': b''
        })

    alloc[-1]['size'] += len(bytes_)
    alloc[-1]['compiled'] += bytes_

    return alloc


@curry
def create_allocs(funcs, alloc, inst):
    if inst['type'] == 'call':
        func = funcs[inst['name']]

        comp, prelim_size = compile_call_alloc(func['in_args'], inst['name'])
        return alloc + [{
            'type': 'call',
            'prelim_size': prelim_size,
            'compile': comp
        }]
    elif inst['type'] == 'op' and inst['name'].startswith('PUSH'):
        if inst['value']['type'] == 'var':
            comp, size = compile_var_push_alloc(
                inst['name'],
                inst['value']['name']
            )
            return alloc + [{
                'type': 'var_push',
                'size': size,
                'compile': comp
            }]
        else:
            verify_push(inst)
            return alloc_compiled_bytes(
                alloc,
                create_push(bytes.fromhex(inst['value']['value']))
            )

    elif inst['type'] == 'op':
        return alloc_compiled_bytes(alloc, bytes([op_code(inst['name'])]))
    elif inst['type'] == 'var_def':
        return alloc + [{
            'type': 'jump_dest',
            'var_name': inst['name'],
            'compiled': bytes([op_code('JUMPDEST')])
        }]

    return alloc


def get_allocs(insts, funcs):
    start = []
    return reduce(create_allocs(funcs), insts, start)


def compile_eca(code):
    parsed = parse(code)
    print('parsed:', json.dumps(parsed, indent=2), sep='\n')
    check_functions(parsed['functions'])
    allocs = get_allocs(parsed['main_code'], parsed['functions'])
    for alloc in allocs:
        print('alloc:', alloc, '0x' + alloc.get('compiled', b'').hex())
    return 'abc'
