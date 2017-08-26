from collections import namedtuple
from typing import Iterable


Arg = namedtuple("Arg", "type name")
Type = namedtuple("Type", "check convert wrap")
Class = namedtuple("Class", "name type construct ref unref")


class Typ:
    def __init__(self, c_type, name, is_out: bool):
        self.c_type = c_type
        self.is_out = is_out
        self.name = name
        self.c_name = "_c_%s_" % name
        self.js_name = "_js_%s_" % name

    def skip(self, i, args):
        return i

    def get_c_args_for_func_call(self):
        prefix = '&' if self.is_out else ''
        yield prefix + self.c_name

    def get_js_args_for_js_func_call(self):
        yield self.js_name

    def check(self, source) -> str:
        pass

    def get_js_values_from_js_arg(self, source) -> Iterable[str]:
        pass

    def get_c_values_from_js(self, typ=None) -> Iterable[str]:
        pass

    def create_js_values_from_c_args(self) -> Iterable[str]:
        yield '    v8::Local<v8::Object> %s_obj = v8::Object::New(isolate);\n' % self.js_name
        yield '    %s::Factory(*obj, %s);\n' % (self.c_type.rstrip('*'), self.c_name)

    def cast_js_value_to_c(self) -> str:
        pass

    def add_assertions(self, i, args) -> Iterable[str]:
        pass

    def declare_empty_c_arg(self):
        raise NotImplementedError

    def take_source_args(self, i, expl_args):
        return i


class SimpleTyp(Typ):
    def declare_empty_c_arg(self):
        yield '    %s %s;\n' % (self.c_type, self.c_name)

    def __init__(self, c_type, name, is_out, js_check, js_type, js_cast, js_to_c_cast, c_to_js_cast):
        super().__init__(c_type, name, is_out)
        self.c_to_js_cast = c_to_js_cast
        self.js_check = js_check
        self.js_type = js_type
        self.js_cast = js_cast
        self.js_to_c_cast = js_to_c_cast

    def check(self, source):
        return self.js_check % source

    def get_js_values_from_js_arg(self, source):
        yield '    %s %s = %s;\n' % (self.js_type, self.js_name, self.js_cast % source)

    def get_c_values_from_js(self, typ=None):
        if not typ:
            typ = self.c_type
        yield '    %s %s = (%s) %s;\n' % (typ, self.c_name, typ, self.js_to_c_cast % self.js_name)

    def create_js_values_from_c_args(self):
        yield '    %s %s = %s;\n' % (self.js_type, self.js_name, self.c_to_js_cast % self.c_name)

    def cast_js_value_to_c(self):
        return self.js_to_c_cast % self.js_name


class BytesTyp(Typ):

    def declare_empty_c_arg(self):
        raise NotImplementedError

    def __init__(self, c_type, name, is_out: bool):
        super().__init__(c_type, name, is_out)
        self.length = None

    def check(self, source):
        return '%s->IsArrayBuffer()' % source

    def take_source_args(self, i, args):
        self.length = args[i + 1]
        return i + 1

    def get_js_values_from_js_arg(self, source):
        yield '    v8::ArrayBuffer* %s_buf_ = v8::ArrayBuffer::Cast(*%s);\n' % (self.js_name, source)
        yield '    v8::ArrayBuffer::Contents %s = %s_buf_->GetContents();\n' % (self.js_name, self.js_name)

    def get_c_values_from_js(self, typ=None):
        if not typ:
            typ = self.c_type
        yield '    %s %s = (%s) %s.Data();\n' % (typ, self.c_name, typ, self.js_name)
        yield '    size_t %s_len_ = %s.ByteLength();\n' % (self.c_name, self.js_name)

    def add_assertions(self, i, args):
        arg = args[i + 1]
        yield i + 1, "%s <= %s_len_" % (arg.c_name, self.c_name), "Buffer overflow."

    def create_js_values_from_c_args(self, ):
        # It is necessary to create a copy of the data!
        yield '    v8::Local<v8::ArrayBuffer> %s = v8::ArrayBuffer::New(isolate, (size_t) %s);\n' % (
            self.js_name, self.length.c_name)
        yield '    void* %s_buf = %s->GetContents().Data();\n' % (
            self.js_name, self.js_name)
        yield '    memcpy(%s_buf, %s, (size_t) %s);\n' % (self.js_name, self.c_name, self.length.c_name)


class CallbackTyp(Typ):
    def __init__(self, c_type, name, is_out):
        super().__init__(c_type, name, is_out)
        self.target = None
        self.destroy_func = None
        assert not is_out

    def declare_empty_c_arg(self):
        raise NotImplementedError

    def check(self, source):
        return '%s->IsFunction()' % source

    def skip(self, i, args):
        self.target = args[i + 1]
        self.destroy_func = args[i + 2]
        return i + 2

    def get_c_args_for_func_call(self):
        yield self.c_name
        yield from self.target.get_c_args_for_func_call()
        yield from self.destroy_func.get_c_args_for_func_call()

    def get_js_values_from_js_arg(self, source):
        js_name = self.target.js_name
        yield '    WrappedCallbackFunc* %s = new WrappedCallbackFunc;\n' % js_name
        yield '    %s->isolate = isolate;\n' % js_name
        yield '    v8::Local<v8::Function> %s_func = v8::Local<v8::Function>::Cast(%s);\n' % (js_name, source)
        yield '    %s->func.Reset(isolate, %s_func);\n' % (js_name, js_name)

    def get_c_values_from_js(self, typ=None):
        if not typ:
            typ = self.c_type
        yield '    %s %s = reinterpret_cast<%s>(Callback_%s);\n' % (typ, self.c_name, typ, self.c_type)
        yield '    %s %s = reinterpret_cast<%s>(%s);\n' % (
            self.target.c_type, self.target.c_name, self.target.c_type, self.target.js_name)
        yield '    GDestroyNotify %s = reinterpret_cast<GDestroyNotify>(destroy_wrapped_callback_func);\n' % (
            self.destroy_func.c_name)


class PointerTyp(SimpleTyp):
    def __init__(self, c_type, name, is_out):
        super().__init__(c_type, name, is_out, '%s->IsExternal()', 'v8::Local<v8::External>', "v8::External::Cast(%s)",
                         "%s->ExternalValue()", "v8::External::New(isolate, %s)")


class UnknownTyp(SimpleTyp):
    def __init__(self, c_type, name, is_out):
        super().__init__(c_type, name, is_out, '%s->Is?????()', '// v8::Local<v8::?????>', "v8::?????::Cast(%s)",
                         "%s->?????Value()", "v8::?????::New(isolate, %s)")

    def create_js_values_from_c_args(self) -> Iterable[str]:
        yield '    v8::Local<v8::Object> %s = %sNodejsWrapper::Factory(isolate, %s);\n' % (
            self.js_name, self.c_type.rstrip('*'), self.c_name)


class BooleanTyp(SimpleTyp):
    def __init__(self, c_type, name, is_out):
        super().__init__(c_type, name, is_out, '%s->IsBoolean()', 'v8::Local<v8::Boolean>', "%s->ToBoolean()",
                         "%s->BooleanValue()", "v8::Boolean::New(isolate, (bool) %s)")


class IntegerTyp(SimpleTyp):
    def __init__(self, c_type, name, is_out):
        super().__init__(c_type, name, is_out, '%s->IsNumber()', 'v8::Local<v8::Integer>', "%s->ToInteger()",
                         "%s->IntegerValue()", "v8::Integer::New(isolate, %s)")


class StringTyp(SimpleTyp):
    def __init__(self, c_type, name, is_out):
        super().__init__(c_type, name, is_out, '%s->IsString()', 'v8::Local<v8::String>', "%s->ToString()",
                         "*%s_utf8", "v8::String::NewFromUtf8(isolate, %s)")

    def get_js_values_from_js_arg(self, source):
        yield '    %s %s = %s;\n' % (self.js_type, self.js_name, self.js_cast % source)
        yield '    v8::String::Utf8Value %s_utf8(%s);\n' % (self.js_name, self.js_name)

    # def get_c_values_from_js(self, typ=None):
    #     if not typ:
    #         typ = self.c_type
    #     yield '    %s %s = (%s) %s;\n' % (typ, self.c_name, typ, self.js_to_c_cast % self.js_name)


G_ERROR = 'GError**'
Args = namedtuple("Args", "all expl out impl")
TYPES_MAP = {
    "const gchar*": StringTyp,
    'void*': PointerTyp,
    'GDestroyNotify': UnknownTyp,
    'guint8*': BytesTyp,
    'int': IntegerTyp,
    'gboolean': BooleanTyp,
    'const gchar *': StringTyp,
}
