from parsimonious.nodes import NodeVisitor
from grammar import grammar


def unpack(value, layers=1):
    for _ in range(layers):
        value = value[0]
    return value


class Assembler(NodeVisitor):
    def generic_visit(self, node, visited_children):
        return visited_children or node

    def visit_main(self, _, visited_children):
        first_block, other_blocks, _ = visited_children
        blocks = [
            unpack(first_block),
            *(unpack(block) for _, block in other_blocks)
        ]
        consec_instructions = []

        functions = dict()
        variables = dict()

        calls = set()
        used_vars = set()

        for block in blocks:
            if block['type'] == 'block':
                consec_instructions.extend(block['body'])
            elif block['type'] == 'func':
                if block['name'] in functions:
                    return None, NameError(
                        f"function '{block['name']}' defined multiple times")

                del block['type']
                name = block['name']
                del block['name']
                functions[name] = block
                functions[name].update({
                    'pos': None,
                    'unused': False
                })
            else:
                return None, ValueError(f"invalid block type '{block['type']}'")

            for inst in block['body']:
                if inst['type'] == 'op'\
                        and inst['name'].startswith('PUSH')\
                        and inst['value']['type'] == 'var':
                    used_vars.add(inst['value']['name'])
                elif inst['type'] == 'var_def':
                    if inst['name'] in variables:
                        return None, NameError(
                            f"variable '{inst['name']}' already defined")
                    variables[inst['name']] = {
                        'pos': None,
                        'unused': False
                    }
                elif inst['type'] == 'call':
                    calls.add(inst['name'])

        var_diff = used_vars - set(variables)
        if var_diff:
            return None, NameError(
                f"undefined vars: {', '.join(map(repr, var_diff))}")
        func_diff = calls - set(functions)
        if func_diff:
            return None, NameError(
                f"undefined functions: {', '.join(map(repr, func_diff))}")

        var_diff = set(variables) - used_vars
        if var_diff:
            for var in var_diff:
                variables[var]['unused'] = True
            print('Warning: unused vars:', ', '.join(map(repr, var_diff)))

        func_diff = set(functions) - calls
        if func_diff:
            for func in func_diff:
                functions[func]['unused'] = True
            print('Warning: unused functions:',
                  ', '.join(map(repr, func_diff)))

        return {
            'functions': functions,
            'variables': variables,
            'main_code': consec_instructions
        }, None

    def visit_instructs(self, _, visited_children):
        first_op, other_ops = visited_children
        return {
            'type': 'block',
            'body': [
                unpack(first_op, 1),
                *(unpack(op, 1) for _, op in other_ops)
            ]
        }

    def visit_function(self, _, visited_children):
        (name, in_args, out_args), body = visited_children
        return {
            'type': 'func',
            'name': name,
            'in_args': in_args,
            'out_args': out_args,
            'body': body
        }

    def visit_f_header(self, _, visited_children):
        name, _, in_args, _, _, out_args,  _ = visited_children

        return name.text, int(in_args.text), int(out_args.text)

    def visit_f_body(self, _, visited_children):
        all_ops = []
        for line in visited_children:
            all_ops.extend(line)
        return all_ops

    def visit_f_line(self, _, visited_children):
        _, first_op, other_ops, _ = visited_children
        all_stuff = [
            unpack(first_op),
            *(unpack(op) for _, op in other_ops)
        ]
        return all_stuff

    def visit_op(self, _, visited_children):
        return unpack(visited_children)

    def visit_push_op(self, _, visited_children):
        push_type, _, (push_val,) = visited_children
        return {'type': 'op', 'name': push_type, 'value': push_val}

    def visit_normal_op(self, node, _):
        return {'type': 'op', 'name': node.text}

    def visit_bytes(self, node, _):
        _, bytes_ = node.children

        return {'type': 'bytes_literal', 'value': bytes_.text}

    def visit_var(self, _, visited_children):
        _, name = visited_children
        return {'type': 'var', 'name': name.text}

    def visit_call(self, _, visited_children):
        name, _ = visited_children
        return {'type': 'call', 'name': name.text}

    def visit_var_def(self, _, visited_children):
        _, name = visited_children
        return {'type': 'var_def', 'name': name.text}

    def visit_push_op_id(self, node, _):
        return node.text


def parse(code: str):
    tree = grammar.parse(code)
    res, error = Assembler().visit(tree)

    if error:
        raise error

    return res
