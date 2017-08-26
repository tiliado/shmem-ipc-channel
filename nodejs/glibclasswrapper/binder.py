from collections import defaultdict, OrderedDict
from typing import List, Dict

from glibclasswrapper.snippets import PRELUDE, CLASS_DECLARATION_BEGIN_PUBLIC, CLASS_DECLARATION_BEGIN_PRIVATE, \
    CLASS_DECLARATION_END, CLASS_INIT, DESTRUCTOR, CALLBACK_BEGIN, METHOD_BEGIN, NOT_CALLED_AS_CONSTRUCTOR, \
    WRONG_NUMBER_OF_ARGUMENTS, WRONG_TYPE_OF_ARGUMENTS, PRIVATE_CONSTRUCTOR, ASSERTION, UNWRAP, DEF_G_ERROR, WRAP, \
    FACTORY_WRAP, CHECK_G_ERROR, SET_RESULT, METHOD_END, CALL_CALLBACK, END, CHECK_INSTANCE_NOT_NULL, CALLBACK_WRAPPING
from glibclasswrapper.types import Arg, Class, Typ, G_ERROR, Args, TYPES_MAP


def parse(func):
    front, back = func.split("(", 1)
    ret_type, func_name = front.rsplit(None, 1)
    args = [s.strip().rsplit(None, 1) for s in back.rsplit(")", 1)[0].split(",")]
    args = [Arg(typ.replace(" *", "*"), name) for typ, name in args]
    return ret_type, func_name, args


def get_lowercase_base(klass_name):
    return "".join([('_' + c.lower()) if c.isupper() else c for c in klass_name])[1:]


def get_construct_method(klass_name):
    return get_lowercase_base(klass_name) + "_new"


def get_destruct_method(klass_name):
    return get_lowercase_base(klass_name) + "_unref"


def get_type_check_for_js_args(expl_args: Dict[str, Typ]) -> str:
    return ' || '.join('!%s' % arg.check('args[%d]' % i) for i, arg in enumerate(expl_args.values()))


def convert_js_args_to_c_values(expl_args: Dict[str, Typ]):
    all_assertions = defaultdict(list)
    expl_args = tuple(expl_args.values())
    for i, arg in enumerate(expl_args):
        yield from arg.get_js_values_from_js_arg('args[%d]' % i)
        yield from arg.get_c_values_from_js()
        assertions = arg.add_assertions(i, expl_args)
        if assertions:
            for index, *c_assertion in assertions:
                all_assertions[index].append(c_assertion)

        for condition, message in all_assertions[i]:
            yield ASSERTION % (condition, message)


def create_js_values_from_c_args(expl_args: List[Typ]):
    i = 0
    size = len(expl_args)
    while i < size:
        arg = expl_args[i]
        # noinspection PyUnresolvedReferences
        i = arg.take_source_args(i, expl_args) + 1
        yield from arg.create_js_values_from_c_args()


def declare_out_c_args(out_args: Dict[str, Typ]):
    for arg in out_args.values():
        yield from arg.declare_empty_c_arg()


def create_c_func_call(klass, ret_type, func_name, args):
    buf = []
    all_i = 0
    all_args = args.all
    size = len(all_args)
    while all_i < size:
        arg = all_args[all_i]
        name = arg.name
        if arg.type == klass.type:
            buf.append('self')
            all_i += 1
        elif arg.type == G_ERROR:
            buf.append('&__g_error__')
            all_i += 1
        else:
            typ = args.expl.get(name, args.out.get(name))
            assert typ, (func_name, name, args.out, args.expl)
            for param in typ.get_c_args_for_func_call():
                all_i += 1
                buf.append(param)

    call = '%s(%s)' % (func_name, ', '.join(buf))
    if func_name == klass.construct:
        assignment = '    %s self = %%s;\n' % ret_type
    elif ret_type == "void":
        assignment = '    %s;\n'
    else:
        assignment = '    %s _c_return_ = %%s;\n' % ret_type
    return assignment % call


def get_js_args_for_js_func_call(expl_args: List[Typ]):
    i = 0
    size = len(expl_args)
    while i < size:
        arg = expl_args[i]
        # noinspection PyUnresolvedReferences
        i = arg.take_source_args(i, expl_args) + 1
        yield from arg.get_js_args_for_js_func_call()


def lower_camel(string):
    return ''.join(((s[0].upper() + s[1:]) if i else s) for i, s in enumerate(string.split("_")))


def unprefix(value, prefix):
    return value[len(prefix):] if prefix and value.startswith(prefix) else value


class Binder:
    def __init__(self):
        self.strip_prefix = "_"
        self.declarations = []
        self.body = []
        self.headers = set()
        self.target = "addon"
        self.classes = []
        self.types = {}
        self.types.update(TYPES_MAP)

    def get_typ(self, type_name, arg_name) -> "Typ":
        try:
            typ = self.types[type_name](type_name, arg_name, False)
            return typ
        except KeyError as e:
            if type_name.endswith('*'):
                try:
                    real_type = type_name[:-1]
                    return self.types[real_type](real_type, arg_name, True)
                except KeyError:
                    pass
            raise e

    def categorize_args(self, args: List[Arg], klass: Class = None) -> Args:
        expl_args = OrderedDict()
        out_args = OrderedDict()
        impl_args = OrderedDict()
        implicit = (klass.type if klass else None, G_ERROR)
        all_args = [(self.get_typ(arg.type, arg.name) if arg.type not in implicit else arg) for arg in args]
        i = 0
        size = len(all_args)
        while i < size:
            arg = all_args[i]
            if isinstance(arg, Arg):
                impl_args[arg.name] = arg
            else:
                if arg.is_out:
                    out_args[arg.name] = arg
                else:
                    expl_args[arg.name] = arg
                i = arg.skip(i, all_args)
            i += 1
        return Args(args, expl_args, out_args, impl_args)

    def bind_spec(self, spec):
        self.strip_prefix = spec["strip_prefix"]
        self.types.update(spec["types"])
        self.target = spec["target"]
        callbacks = [(x,) + parse(x) for x in spec["callbacks"]]
        self.bind_callbacks(callbacks)

        for klass in spec["classes"]:
            self.bind_class(klass)
        return self

    def bind_class(self, klass_spec):
        try:
            self.headers.add(klass_spec["header"])
        except KeyError:
            pass
        name = klass_spec["name"]
        self.classes.append(name)
        prefix = get_lowercase_base(name)
        prefix_len = len(prefix) + 1

        klass = Class(name, name + '*', get_construct_method(name), prefix + "_ref", prefix + "unref")
        methods = [(x, ) + parse(x) for x in klass_spec["methods"]]

        prototype = []
        for method in methods:
            m_name = method[2]
            if m_name != klass.construct:
                prototype.append('    NODE_SET_PROTOTYPE_METHOD(tpl, "%s", Method_%s);\n' % (
                    lower_camel(m_name[prefix_len:]), m_name))

        self.declarations.append(CLASS_DECLARATION_BEGIN_PUBLIC % name)
        self.create_factory(klass)
        self.declarations.append(CLASS_DECLARATION_BEGIN_PRIVATE % (name, klass.type))
        self.declarations.append('    explicit %sNodejsWrapper(%s* self = NULL);\n' % (name, name))
        without_prefix = unprefix(name, self.strip_prefix)
        self.body.append(CLASS_INIT % (name, name, klass.construct, without_prefix, ''.join(prototype),
                                       without_prefix))
        self.body.append('%sNodejsWrapper::%sNodejsWrapper(%s* self) : instance(self) {}' % (name, name, name))
        self.body.append(DESTRUCTOR % (name, name, get_destruct_method(name)))
        self.bind_methods(klass, methods)
        self.declarations.append(CLASS_DECLARATION_END)

    def create_factory(self, klass):
        factory_declaration = '        static v8::Local<v8::Object> Factory(v8::Isolate* isolate, %s* self);\n'
        self.declarations.append(factory_declaration % klass.name)
        name = klass.name
        self.body.append(FACTORY_WRAP % (name, name, name, name, klass.ref))

    def bind_methods(self, klass, methods):
        found_constructor = False
        for method, ret_type, func_name, args in methods:
            if func_name != klass.construct:
                self.bind_method(klass, method, ret_type, func_name, args)
            else:
                self.bind_constructor(klass, method, ret_type, func_name, args)
                found_constructor = True
        if not found_constructor:
            self.create_private_constructor(klass)

    def bind_method(self, klass, method, ret_type, func_name, args):
        args = self.categorize_args(args, klass)
        expl_args = args.expl
        self.declarations.append('        static void Method_%s(const v8::FunctionCallbackInfo<v8::Value>& args);\n' %
                                 func_name)
        self.body.append(METHOD_BEGIN % (klass.name, func_name, method))
        n_args = len(args.expl)
        self.body.append(WRONG_NUMBER_OF_ARGUMENTS % (n_args, method))
        if n_args:
            self.body.append(WRONG_TYPE_OF_ARGUMENTS % (get_type_check_for_js_args(expl_args), method))
        self.body.append(UNWRAP % (klass.name, klass.name, klass.type))
        self.body.append(CHECK_INSTANCE_NOT_NULL % klass.name)
        self.body.append(DEF_G_ERROR)
        self.body.extend(convert_js_args_to_c_values(expl_args))
        self.body.extend(declare_out_c_args(args.out))
        self.body.append(create_c_func_call(klass, ret_type, func_name, args))
        self.body.append(CHECK_G_ERROR)
        c_args = []
        if ret_type != "void":
            c_args.append(self.get_typ(ret_type, 'return'))
            c_args.extend(args.out.values())
        if c_args:
            self.body.extend(create_js_values_from_c_args(c_args))
            if ret_type != "void":
                self.body.append(SET_RESULT % c_args[0].js_name)
            else:
                raise NotImplementedError(c_args)
        self.body.append(METHOD_END % method)

    def bind_constructor(self, klass, method, ret_type, func_name, args):
        args = self.categorize_args(args, klass)
        self.declarations.append('        static void Method_%s(const v8::FunctionCallbackInfo<v8::Value>& args);\n' %
                                 func_name)
        self.body.append(METHOD_BEGIN % (klass.name, func_name, method))
        self.body.append(NOT_CALLED_AS_CONSTRUCTOR)
        expl_args = args.expl
        n_args = len(expl_args)
        self.body.append(WRONG_NUMBER_OF_ARGUMENTS % (n_args, method))
        if n_args:
            self.body.append(WRONG_TYPE_OF_ARGUMENTS % (get_type_check_for_js_args(expl_args), method))
        self.body.append(DEF_G_ERROR)
        self.body.extend(convert_js_args_to_c_values(expl_args))
        self.body.extend(declare_out_c_args(args.out))
        self.body.append(create_c_func_call(klass, ret_type, func_name, args))
        self.body.append(CHECK_G_ERROR)
        self.body.append(WRAP % (klass.name, klass.name))
        self.body.append(METHOD_END % method)

    def create_private_constructor(self, klass):
        self.declarations.append('        static void Method_%s(const v8::FunctionCallbackInfo<v8::Value>& args);\n' %
                                 klass.construct)
        self.body.append(METHOD_BEGIN % (klass.name, klass.construct, "private construct"))
        self.body.append(PRIVATE_CONSTRUCTOR)
        self.body.append(METHOD_END % "private construct")

    def bind_callbacks(self, callbacks):
        for callback, ret_type, func_name, args in callbacks:
            self.bind_callback(callback, ret_type, func_name, args)

    def bind_callback(self, callback, ret_type, func_name, args):
        user_data = args[-1]
        args = self.categorize_args(args[0:-1])
        expl_args = args.expl
        c_args = ', '.join(['%s %s' % (arg.c_type, arg.c_name) for arg in expl_args.values()]
                           + ['%s %s' % (user_data.type, user_data.name)])
        c_user_data = user_data.name
        self.declarations.append('        static void Callback_%s(%s);\n' % (func_name, c_args))
        self.body.append(CALLBACK_BEGIN % (func_name, c_args, callback, c_user_data))
        expl_args_values = list(expl_args.values())
        self.body.extend(create_js_values_from_c_args(expl_args_values))
        js_args = list(get_js_args_for_js_func_call(expl_args_values))
        self.body.append(CALL_CALLBACK % (len(js_args), ', '.join(js_args)))
        if ret_type != "void":
            raise NotImplementedError
            # typ = self.get_typ(ret_type, 'return')
        self.body.append(METHOD_END % callback)

    def finish(self):
        buf = [
            PRELUDE % "\n".join('#include <%s>' % header for header in self.headers),
            CALLBACK_WRAPPING
        ]
        buf.extend(self.declarations)
        buf.extend(self.body)
        init_all = '\n'.join('    %sNodejsWrapper::Init(exports);' % c for c in self.classes)
        buf.append(END % (init_all, self.target))
        return ''.join(buf)



