PRELUDE = """
#include <node.h>
#include <node_object_wrap.h>
#include <glib.h>
%s

"""
CLASS_DECLARATION_BEGIN_PUBLIC = """
class %sNodejsWrapper : public node::ObjectWrap {
    public:
        static void Init(v8::Local<v8::Object> exports);
        
"""
CLASS_DECLARATION_BEGIN_PRIVATE = """
    private:
        ~%sNodejsWrapper();
        static v8::Persistent<v8::Function> constructor;
        
        %s instance;
        
"""
CLASS_DECLARATION_END = """
        
};
"""
CLASS_INIT = """
v8::Persistent<v8::Function> %sNodejsWrapper::constructor;


void %sNodejsWrapper::Init(v8::Local<v8::Object> exports) {
    v8::Isolate* isolate = exports->GetIsolate();

    v8::Local<v8::FunctionTemplate> tpl = v8::FunctionTemplate::New(isolate, Method_%s);
    tpl->SetClassName(v8::String::NewFromUtf8(isolate, "%s"));
    tpl->InstanceTemplate()->SetInternalFieldCount(1);

%s

    constructor.Reset(isolate, tpl->GetFunction());
    exports->Set(v8::String::NewFromUtf8(isolate, "%s"), tpl->GetFunction());
}
"""
DESTRUCTOR = """
%sNodejsWrapper::~%sNodejsWrapper() {
    %s(instance);
    instance = NULL;
}
"""
CALLBACK_BEGIN = """
void Callback_%s(%s) {
    // g_warning("Enter method: %s");
    WrappedCallbackFunc* cb = reinterpret_cast<WrappedCallbackFunc*>(%s);
    g_assert(cb != NULL);
    v8::Isolate* isolate = cb->isolate;
"""
METHOD_BEGIN = """
void %sNodejsWrapper::Method_%s(const v8::FunctionCallbackInfo<v8::Value>& args) {
    // g_warning("Enter method: %s");
    v8::Isolate* isolate = args.GetIsolate();
"""
NOT_CALLED_AS_CONSTRUCTOR = """
    if (!args.IsConstructCall()) {
        isolate->ThrowException(v8::Exception::TypeError(
            v8::String::NewFromUtf8(isolate,
                "Must be called as a constructor with `new`: `%s`.")));
    }
"""
WRONG_NUMBER_OF_ARGUMENTS = """
    if (args.Length() != %d) {
        isolate->ThrowException(v8::Exception::TypeError(
            v8::String::NewFromUtf8(isolate,
                "Wrong number of arguments for `%s`.")));
        return;
    }
"""
WRONG_TYPE_OF_ARGUMENTS = """
    if (%s) {
        isolate->ThrowException(v8::Exception::TypeError(
            v8::String::NewFromUtf8(isolate, "Wrong type of arguments for `%s`.")));
        return;
    }
"""
PRIVATE_CONSTRUCTOR = """
    /* isolate->ThrowException(v8::Exception::TypeError(
        v8::String::NewFromUtf8(isolate, "Private constructor")));
    return; */
"""
ASSERTION = """
    if (!(%s)) {
        isolate->ThrowException(v8::Exception::TypeError(
            v8::String::NewFromUtf8(isolate, "%s")));
        return;
    }
"""
CHECK_INSTANCE_NOT_NULL = """
    if (self == NULL) {
        isolate->ThrowException(v8::Exception::TypeError(
            v8::String::NewFromUtf8(isolate, "%s wrapper has empty instance.")));
        return;
    }
"""
UNWRAP = """
    %sNodejsWrapper* wrapper = ObjectWrap::Unwrap<%sNodejsWrapper>(args.Holder());
    g_assert(wrapper != NULL);
    %s self = wrapper->instance;
"""
DEF_G_ERROR = """
    GError* __g_error__ = NULL;
"""
WRAP = """
    %sNodejsWrapper* wrapper = new %sNodejsWrapper();
    wrapper->instance = self;
    wrapper->Wrap(args.This());
    args.GetReturnValue().Set(args.This());
    
"""
FACTORY_WRAP = """
v8::Local<v8::Object> %sNodejsWrapper::Factory(v8::Isolate* isolate, %s* self) {
    v8::EscapableHandleScope handle_scope(isolate);
    const int argc = 0;
    v8::Local<v8::Value> argv[argc] = {};
    v8::Local<v8::Context> context = isolate->GetCurrentContext();
    v8::Local<v8::Function> obj_constructor = v8::Local<v8::Function>::New(isolate, constructor);
    v8::Local<v8::Object> obj_instance = obj_constructor->NewInstance(context, argc, argv).ToLocalChecked();
    %sNodejsWrapper* wrapper = new %sNodejsWrapper();
    %s(self);
    wrapper->instance = self;
    wrapper->Wrap(obj_instance);
    return handle_scope.Escape(obj_instance);
}
"""
CHECK_G_ERROR = """

    if (__g_error__ != NULL) {
        isolate->ThrowException(v8::Exception::TypeError(
            v8::String::NewFromUtf8(isolate, __g_error__->message))); // %s
        g_clear_error(&__g_error__);
        return;
    }
"""
SET_RESULT = """
    args.GetReturnValue().Set(%s);
"""
METHOD_END = """
    // g_warning("Exit method: %s");
}

"""

CALLBACK_WRAPPING = """
struct WrappedCallbackFunc {
    v8::Isolate* isolate;
    v8::Persistent<v8::Function> func;
};

void destroy_wrapped_callback_func(void* pointer) {
    // g_warning("Enter destroy_wrapped_callback_func");
    WrappedCallbackFunc* cb = reinterpret_cast<WrappedCallbackFunc*>(pointer);
    if (cb != NULL) {
        cb->func.Reset();
        delete cb;
    }
    // g_warning("Exit destroy_wrapped_callback_func");
}
"""
CALL_CALLBACK = """
    const unsigned argc = %d;
    v8::Local<v8::Value> argv[argc] = {%s};
    v8::Local<v8::Function> func = v8::Local<v8::Function>::New(isolate, cb->func);
    v8::TryCatch try_catch(isolate);
    v8::Local<v8::Value> _js_return_ = func->Call(v8::Null(isolate), argc, argv);
    if (try_catch.HasCaught()) {
        node::FatalException(isolate, try_catch);
    }
"""
END = """
void InitAll(v8::Local<v8::Object> exports) {
%s
}

NODE_MODULE(%s, InitAll)
"""
