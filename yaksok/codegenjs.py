"""
    codegen
    ~~~~~~~

    Extension to ast that allow ast -> python code generation.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.

    Modified by ipkn to support python3 ast.arg
"""
import string
from ast import *

BINOP_SYMBOLS = {}
BINOP_SYMBOLS[Add] = '+'
BINOP_SYMBOLS[Sub] = '-'
BINOP_SYMBOLS[Mult] = '*'
BINOP_SYMBOLS[Div] = '/'
BINOP_SYMBOLS[Mod] = '%'
BINOP_SYMBOLS[Pow] = '**'
BINOP_SYMBOLS[LShift] = '<<'
BINOP_SYMBOLS[RShift] = '>>'
BINOP_SYMBOLS[BitOr] = '|'
BINOP_SYMBOLS[BitXor] = '^'
BINOP_SYMBOLS[BitAnd] = '&'
BINOP_SYMBOLS[FloorDiv] = '//'

BOOLOP_SYMBOLS = {}
BOOLOP_SYMBOLS[And] = '&&'
BOOLOP_SYMBOLS[Or] = '||'

CMPOP_SYMBOLS = {}
CMPOP_SYMBOLS[Eq] = '=='
CMPOP_SYMBOLS[NotEq] = '!='
CMPOP_SYMBOLS[Lt] = '<'
CMPOP_SYMBOLS[LtE] = '<='
CMPOP_SYMBOLS[Gt] = '>'
CMPOP_SYMBOLS[GtE] = '>='
CMPOP_SYMBOLS[Is] = '==='
CMPOP_SYMBOLS[IsNot] = '!=='
CMPOP_SYMBOLS[In] = 'in'
CMPOP_SYMBOLS[NotIn] = 'not in'

UNARYOP_SYMBOLS = {}
UNARYOP_SYMBOLS[Invert] = '~'
UNARYOP_SYMBOLS[Not] = '!'
UNARYOP_SYMBOLS[UAdd] = '+'
UNARYOP_SYMBOLS[USub] = '-'

function_helper = '''
var ____find_and_call_function = function (matcher, scope, functions) {
    var has_variable = function (x) {
        try {
            eval(x);
        }
        catch(e) {
            return false;
        };
        return true;
    };

    var get_variable_value = function (x) {
        return eval(x);
    };

    var try_match = function (matcher, proto) {
        if (matcher.length == 0 && proto.length == 0)
            return [[]];
        if (matcher.length == 0)
            return [];
        if (proto.length == 0)
            return [];
        if (matcher[0][0] == 'EXPR') {
            if (proto[0][0] == 'IDENTIFIER') {
                var skip = 1;
                if (proto.length >= 2 && proto[1][0] == 'WS')
                    skip = 2;
                var ret = try_match(____slice(matcher,1,null,null), ____slice(proto,skip,null,null));
                for(var i=0; i < ret.length; i ++) {
                    ret[i] = [matcher[0][1]].concat(ret[i]);
                }
                return ret;
            }
            return [];
        } else { // matcher[0][0] == 'NAME'
            if (proto[0][0] == 'IDENTIFIER') {
                var sole_variable_exists = false;
                var to_ret = [];
                // 전체 이름에 해당하는 변수가 존재
                if (has_variable(matcher[0][1])) {
                    sole_variable_exists = true;
                    var skip = 1;
                    if (proto.length >= 2 && proto[1][0] == 'WS')
                        skip = 2;
                    var ret = try_match(____slice(matcher,1,null,null), ____slice(proto,skip,null,null));
                    for(var i = 0; i < ret.length; i ++) {
                        to_ret.push([get_variable_value(matcher[0][1])].concat(ret[i]));
                    }
                }

                // 정의에 빈칸 없는 경우, 잘라서 시도해본다
                if (proto.length >= 2 && proto[1][0] != 'WS') {
                    var try_sliced_str_match = function (each_str) {
                        var to_ret = [];
                        if (matcher[0][1].endsWith(each_str)) {
                            var variable_name = matcher[0][1].substr(0, matcher[0][1].length-each_str.length);
                            if (has_variable(variable_name)) {
                                var skip = 2;
                                if (proto.length >= 3 && proto[2][0] == 'WS')
                                    skip = 3;
                                var ret = try_match(____slice(matcher,1,null,null), ____slice(proto,skip,null,null));
                                for(var i = 0; i < ret.length; i ++) {
                                    var sub_candidate = ret[i];
                                    if (sole_variable_exists)
                                        throw "헷갈릴 수 있는 변수명이 사용됨: " + matcher[0][1] + " / " + variable_name + "+" + each_str;
                                    to_ret.push([get_variable_value(variable_name)].concat(sub_candidate));
                                }
                            }
                        }
                        return to_ret;
                    };
                    if (proto[1][0] == 'STRS') {
                        for(var i = 0; i < proto[1][1].length; i ++) {
                            var each_str = proto[1][1][i];
                            to_ret.concat(try_sliced_str_match(each_str));
                        }
                    } else if (proto[1][0] == 'STR') {
                        to_ret.concat(try_sliced_str_match(proto[1][1]));
                    }
                }
                return to_ret;
            } else if (proto[0][0] == 'STR') {
                if (matcher[0][1] == proto[0][1]) {
                    var skip = 1;
                    if (proto.length >= 2 && proto[1][0] == 'WS')
                        skip = 2;
                    return try_match(____slice(matcher, 1), ____slice(proto, skip));
                }
                return [];
            } else if (proto[0][0] == 'STRS') {
                var to_ret = [];
                for(var i = 0; i < proto[0][1].length; i ++) {
                    var each_str = proto[0][1][i];
                    if (matcher[0][1] == each_str) {
                        var skip = 1;
                        if (proto.length >= 2 && proto[1][0] == 'WS')
                            skip = 2;
                        to_ret.concat(try_match(____slice(matcher, 1), ____slice(proto, skip)));
                    }
                }
                return to_ret;
            }
        }
    };

    var candidates = [];
    for(var i = 0; i < functions.length; i ++) {
        var func = functions[i][0];
        var proto = functions[i][1];
        var ret = try_match(matcher, proto);
        for(var j = 0; j < ret.length; j ++) {
            candidates.push([func, ret[j]])
        }
    }

    if (candidates.length == 0)
        throw "해당하는 약속을 찾을 수 없습니다.";
    if (candidates.length >= 2)
        throw "적용할 수 있는 약속이 여러개입니다.";

    func = candidates[0][0];
    args = candidates[0][1];
    return func.apply(null, args);
}
'''

def to_source(node, indent_with=' ' * 4, add_line_information=False):
    """This function can convert a node tree back into python sourcecode.
    This is useful for debugging purposes, especially if you're dealing with
    custom asts not generated by python itself.

    It could be that the sourcecode is evaluable when the AST itself is not
    compilable / evaluable.  The reason for this is that the AST contains some
    more data than regular sourcecode does, which is dropped during
    conversion.

    Each level of indentation is replaced with `indent_with`.  Per default this
    parameter is equal to four spaces as suggested by PEP 8, but it might be
    adjusted to match the application's styleguide.

    If `add_line_information` is set to `True` comments for the line numbers
    of the nodes are added to the output.  This can be used to spot wrong line
    number information of statement nodes.
    """
    generator = SourceGenerator(indent_with, add_line_information)
    generator.visit(node)

    return ''.join(generator.result)

class SourceGenerator(NodeVisitor):
    """This visitor is able to transform a well formed syntax tree into python
    sourcecode.  For more details have a look at the docstring of the
    `node_to_source` function.
    """

    def __init__(self, indent_with, add_line_information=False):
        self.result = []
        self.indent_with = indent_with
        self.add_line_information = add_line_information
        self.indentation = 0
        self.new_lines = 0
        self.sym_idx = 0

    def gensym(self):
        self.sym_idx += 1
        return '____js_gs_{}'.format(self.sym_idx)

    def write(self, x):
        if self.new_lines:
            if self.result:
                self.result.append('\n' * self.new_lines)
            self.result.append(self.indent_with * self.indentation)
            self.new_lines = 0
        self.result.append(x)

    def newline(self, node=None, extra=0):
        self.new_lines = max(self.new_lines, 1 + extra)
        if node is not None and self.add_line_information:
            self.write('# line: %s' % node.lineno)
            self.new_lines = 1

    def body(self, statements):
        self.new_line = True
        self.indentation += 1
        for stmt in statements:
            self.visit(stmt)
        self.indentation -= 1

    def body_or_else(self, node):
        self.body(node.body)
        if node.orelse:
            self.newline()
            self.write('else:')
            self.body(node.orelse)

    def signature(self, node):
        want_comma = []
        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        padding = [None] * (len(node.args) - len(node.defaults))
        for arg, default in zip(node.args, padding + node.defaults):
            write_comma()
            self.visit(arg)
            if default is not None:
                self.write('=')
                self.visit(default)
        if node.vararg is not None:
            write_comma()
            self.write('*' + node.vararg)
        if node.kwarg is not None:
            write_comma()
            self.write('**' + node.kwarg)

    def decorators(self, node):
        for decorator in node.decorator_list:
            self.newline(decorator)
            self.write('@')
            self.visit(decorator)

    # Statements

    def visit_Assert(self, node):
        self.newline(node)
        self.write('assert ')
        self.visit(node.test)
        if node.msg is not None:
           self.write(', ')
           self.visit(node.msg)

    def visit_Assign(self, node):
        self.newline(node)
        if len(node.targets) == 1 and isinstance(node.targets[0], Name) and node.targets[0].id == '____BODY':
            self.write(node.value.s)
            return
        for idx, target in enumerate(node.targets):
            if idx:
                self.write(', ')
            self.visit(target)
        self.write(' = ')
        self.visit(node.value)

    def visit_AugAssign(self, node):
        self.newline(node)
        self.visit(node.target)
        self.write(' ' + BINOP_SYMBOLS[type(node.op)] + '= ')
        self.visit(node.value)

    def visit_ImportFrom(self, node):
        self.newline(node)
        self.write('from %s%s import ' % ('.' * node.level, node.module))
        for idx, item in enumerate(node.names):
            if idx:
                self.write(', ')
            self.write(item)

    def visit_Import(self, node):
        self.newline(node)
        for item in node.names:
            self.write('import ')
            self.visit(item)

    def visit_Expr(self, node):
        self.newline(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.newline(extra=1)
        self.decorators(node)
        self.newline(node)
        self.write('function %s(' % node.name)
        self.visit(node.args)
        self.write(') {')
        self.write(function_helper)
        self.body(node.body)
        self.write('}')

    def visit_ClassDef(self, node):
        have_args = []
        def paren_or_comma():
            if have_args:
                self.write(', ')
            else:
                have_args.append(True)
                self.write('(')

        self.newline(extra=2)
        self.decorators(node)
        self.newline(node)
        self.write('class %s' % node.name)
        for base in node.bases:
            paren_or_comma()
            self.visit(base)
        # XXX: the if here is used to keep this module compatible
        #      with python 2.6.
        if hasattr(node, 'keywords'):
            for keyword in node.keywords:
                paren_or_comma()
                self.write(keyword.arg + '=')
                self.visit(keyword.value)
            if node.starargs is not None:
                paren_or_comma()
                self.write('*')
                self.visit(node.starargs)
            if node.kwargs is not None:
                paren_or_comma()
                self.write('**')
                self.visit(node.kwargs)
        self.write(have_args and '):' or ':')
        self.body(node.body)

    def visit_If(self, node):
        self.newline(node)
        self.write('if (')
        self.visit(node.test)
        self.write(') {')
        self.body(node.body)
        self.write('}')
        while True:
            else_ = node.orelse
            if len(else_) == 0:
                break
            elif len(else_) == 1 and isinstance(else_[0], If):
                node = else_[0]
                self.newline()
                self.write('else if ( ')
                self.visit(node.test)
                self.write(') {')
                self.body(node.body)
                self.write('}')
            else:
                self.newline()
                self.write('else {')
                self.body(else_)
                self.write('}')
                break

    def visit_For(self, node):
        self.newline(node)
        self.write('for (var ')
        g = self.gensym();
        self.write(g)
        self.write(' in ')
        self.visit(node.iter)
        self.write(') { var ')
        self.visit(node.target)
        self.write('=')
        self.visit(node.iter)
        self.write('[')
        self.write(g)
        self.write('];')
        self.newline()
        self.body_or_else(node)
        self.write('}')

    def visit_While(self, node):
        self.newline(node)
        self.write('while (')
        self.visit(node.test)
        self.write(') {')
        self.body_or_else(node)
        self.write('}')

    def visit_With(self, node):
        self.newline(node)
        self.write('with ')
        self.visit(node.context_expr)
        if node.optional_vars is not None:
            self.write(' as ')
            self.visit(node.optional_vars)
        self.write(':')
        self.body(node.body)

    def visit_Pass(self, node):
        self.newline(node)
        self.write(';')

    def visit_Delete(self, node):
        self.newline(node)
        self.write('delete ')
        for idx, target in enumerate(node):
            if idx:
                self.write(', ')
            self.visit(target)

    def visit_Try(self, node):
        "python3 try block"
        self.newline(node)
        self.write('try{')
        self.body(node.body)
        self.write('}')
        for handler in node.handlers:
            self.visit(handler)

    def visit_Global(self, node):
        self.newline(node)
        #self.write('global ' + ', '.join(node.names))

    def visit_Nonlocal(self, node):
        self.newline(node)
        #self.write('nonlocal ' + ', '.join(node.names))

    def visit_Return(self, node):
        self.newline(node)
        if node.value is None:
            self.write('return')
        else:
            self.write('return ')
            self.visit(node.value)

    def visit_Break(self, node):
        self.newline(node)
        self.write('break;')

    def visit_Continue(self, node):
        self.newline(node)
        self.write('continue;')

    def visit_Raise(self, node):
        # XXX: Python 2.6 / 3.0 compatibility
        self.newline(node)
        self.write('throw')
        if hasattr(node, 'exc') and node.exc is not None:
            self.write(' ')
            self.visit(node.exc)
            if node.cause is not None:
                self.write(' from ')
                self.visit(node.cause)
        elif hasattr(node, 'type') and node.type is not None:
            self.visit(node.type)
            if node.inst is not None:
                self.write(', ')
                self.visit(node.inst)
            if node.tback is not None:
                self.write(', ')
                self.visit(node.tback)

    # Expressions

    def visit_Attribute(self, node):
        self.visit(node.value)
        self.write('.' + node.attr)

    def visit_Call(self, node):
        want_comma = []
        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        if isinstance(node.func, Name) and node.func.id == '____vars':
            self.write('var ')
            for arg in node.args:
                write_comma()
                self.visit(arg)
            return

        self.visit(node.func)
        self.write('(')
        for arg in node.args:
            write_comma()
            self.visit(arg)
        for keyword in node.keywords:
            write_comma()
            self.write(keyword.arg + '=')
            self.visit(keyword.value)
        if node.starargs is not None:
            write_comma()
            self.write('*')
            self.visit(node.starargs)
        if node.kwargs is not None:
            write_comma()
            self.write('**')
            self.visit(node.kwargs)
        self.write(')')

    def visit_arg(self, node):
        "python3 arg"
        self.write(node.arg)

    def visit_NameConstant(self, node):
        if node.value is None:
            self.write('null')
        elif node.value is True:
            self.write('true')
        elif node.value is False:
            self.write('false')
        else:
            assert False, repr(node.value)
            self.write(repr(node.value))

    def visit_Name(self, node):
        self.write(node.id)

    def visit_Str(self, node):
        self.write(repr(node.s))

    def visit_Bytes(self, node):
        self.write(repr(node.s))

    def visit_Num(self, node):
        self.write(repr(node.n))

    def visit_Tuple(self, node):
        self.write('[')
        idx = -1
        for idx, item in enumerate(node.elts):
            if idx:
                self.write(', ')
            self.visit(item)
        self.write(idx and ']' or ',]')

    def sequence_visit(left, right):
        def visit(self, node):
            self.write(left)
            for idx, item in enumerate(node.elts):
                if idx:
                    self.write(', ')
                self.visit(item)
            self.write(right)
        return visit

    visit_List = sequence_visit('[', ']')
    visit_Set = sequence_visit('{', '}')
    del sequence_visit

    def visit_Dict(self, node):
        self.write('{')
        for idx, (key, value) in enumerate(zip(node.keys, node.values)):
            if idx:
                self.write(', ')
            self.visit(key)
            self.write(': ')
            self.visit(value)
        self.write('}')

    def visit_BinOp(self, node):
        self.write('(')
        self.visit(node.left)
        self.write(' %s ' % BINOP_SYMBOLS[type(node.op)])
        self.visit(node.right)
        self.write(')')

    def visit_BoolOp(self, node):
        self.write('(')
        for idx, value in enumerate(node.values):
            if idx:
                self.write(' %s ' % BOOLOP_SYMBOLS[type(node.op)])
            self.visit(value)
        self.write(')')

    def visit_Compare(self, node):
        self.write('(')
        self.visit(node.left)
        for op, right in zip(node.ops, node.comparators):
            self.write(' %s ' % CMPOP_SYMBOLS[type(op)])
            self.visit(right)
        self.write(')')

    def visit_UnaryOp(self, node):
        self.write('(')
        op = UNARYOP_SYMBOLS[type(node.op)]
        self.write(op)
        if op == 'not':
            self.write(' ')
        self.visit(node.operand)
        self.write(')')

    def visit_Subscript(self, node):
        self.visit(node.value)
        self.write('[')
        self.visit(node.slice)
        self.write(']')

    def visit_Slice(self, node):
        if node.lower is not None:
            self.visit(node.lower)
        self.write(':')
        if node.upper is not None:
            self.visit(node.upper)
        if node.step is not None:
            self.write(':')
            if not (isinstance(node.step, Name) and node.step.id == 'None'):
                self.visit(node.step)

    def visit_ExtSlice(self, node):
        for idx, item in node.dims:
            if idx:
                self.write(', ')
            self.visit(item)

    def visit_Yield(self, node):
        self.write('yield ')
        self.visit(node.value)

    def visit_Lambda(self, node):
        self.write('lambda ')
        self.visit(node.args)
        self.write(': ')
        self.visit(node.body)

    def visit_Ellipsis(self, node):
        self.write('Ellipsis')

    def generator_visit(left, right):
        def visit(self, node):
            self.write(left)
            self.visit(node.elt)
            for comprehension in node.generators:
                self.visit(comprehension)
            self.write(right)
        return visit

    visit_ListComp = generator_visit('[', ']')
    visit_GeneratorExp = generator_visit('(', ')')
    visit_SetComp = generator_visit('{', '}')
    del generator_visit

    def visit_DictComp(self, node):
        self.write('{')
        self.visit(node.key)
        self.write(': ')
        self.visit(node.value)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.write('}')

    def visit_IfExp(self, node):
        self.visit(node.body)
        self.write(' if ')
        self.visit(node.test)
        self.write(' else ')
        self.visit(node.orelse)

    def visit_Starred(self, node):
        self.write('*')
        self.visit(node.value)

    def visit_Repr(self, node):
        # XXX: python 2.6 only
        self.write('`')
        self.visit(node.value)
        self.write('`')

    # Helper Nodes

    def visit_alias(self, node):
        self.write(node.name)
        if node.asname is not None:
            self.write(' as ' + node.asname)

    def visit_comprehension(self, node):
        self.write(' for ')
        self.visit(node.target)
        self.write(' in ')
        self.visit(node.iter)
        if node.ifs:
            for if_ in node.ifs:
                self.write(' if ')
                self.visit(if_)

    def visit_ExceptHandler(self, node):
        "python3 exception handler"
        self.newline(node)
        self.write('except')
        if node.type is not None:
            self.write(' ')
            self.visit(node.type)
            if node.name is not None:
                self.write(' as ')
                self.visit(node.name)
        self.write(':')
        self.body(node.body)

    def visit_excepthandler(self, node):
        self.newline(node)
        self.write('except')
        if node.type is not None:
            self.write(' ')
            self.visit(node.type)
            if node.name is not None:
                self.write(' as ')
                self.visit(node.name)
        self.write(':')
        self.body(node.body)

    def visit_arguments(self, node):
        self.signature(node)
