import json
from parsimonious.grammar import Grammar

with open('opcodes.json', 'r') as OP_CODES:
    OP_CODES = json.load(OP_CODES)


def get_grammar():

    normal_ops = [f'"{op}"' for op in sorted(
        list(OP_CODES), reverse=True) if not op.startswith('PUSH')]
    all_ops = ' / '.join(normal_ops)

    raw_grammar = f'''
        main = block (block_sep block)* "\\n"?

        block = instructs / function
        block_sep = sep*
        instructs = instruction (sep instruction)*
        function = f_header f_body


        f_header = identifier "(" arg_num "," " "? arg_num "):\\n"
        f_body = f_line+
        f_line = "  " f_instruction (" " f_instruction)* "\\n"
        arg_num = ~"\\d*"


        instruction = op / var_def / call
        f_instruction = op / call

        op = push_op / normal_op
        normal_op = {all_ops}
        push_op = push_op_id sep (bytes / var)
        push_op_id = "PUSH" n32
        call = identifier "()"
        var_def = "#" identifier
        var = "@" identifier

        identifier = ~"\\w+"
        sep = " " / "\\n"
        n32 = (("3" ~"[0-2]") / (~"[0-2][0-9]") / ~"[1-9]")
        bytes = "0x" (hex_dig hex_dig)+
        hex_dig = ~"[0-9A-Fa-f]"
    '''

    return Grammar(raw_grammar)


grammar = get_grammar()
