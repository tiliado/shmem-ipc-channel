include config.mk
PREFIX ?= /usr
DESTDIR ?=
LIB_NAME := $(PROJECT)
LIB_GIRNAME := Shmch-1.0.gir
LIB_TYPELIB := Shmch-1.0.typelib
LIB_VAPINAME := $(PROJECT).vapi
LIB_LIBNAME := lib$(PROJECT).so
LIB_HEADERNAME := $(PROJECT).h
LIB_VALA_FILES := $(wildcard lib/src/*.vala)
LIB_VAPI_FILES := $(wildcard lib/src/*.vapi)
LIB_VALA_ALL := $(addprefix $(OUT)/,$(LIB_GIRNAME) $(LIB_VAPINAME) $(LIB_HEADERNAME) $(LIB_LIBNAME))

PROG_BINNAME := example
PROG_VALA_FILES := $(wildcard lib/examples/*.vala)
PROG_VAPI_FILES := $(wildcard lib/examples/*.vapi)
PROG_VALA_ALL := $(OUT)/$(PROG_BINNAME)

all: $(LIB_VALA_ALL) $(OUT)/$(LIB_TYPELIB) $(PROG_VALA_ALL)

$(OUT):
	mkdir -pv $@

$(LIB_VALA_ALL): $(LIB_VALA_FILES) $(LIB_VAPI_FILES) | $(OUT)
	valac --save-temps -v -d $(OUT) --vapi=$(LIB_VAPINAME) --vapi-comments --gir=$(LIB_GIRNAME) \
		--library=$(LIB_NAME) --shared-library=$(LIB_LIBNAME)  -H $(OUT)/$(LIB_HEADERNAME) \
		--target-glib $(TARGET_GLIB) --pkg posix \
		-X -fPIC -X -shared -X -lrt  -X -lpthread \
		$(VALAFLAGS) $^ -o $(LIB_LIBNAME)

$(OUT)/$(LIB_TYPELIB): $(OUT)/$(LIB_GIRNAME)
	g-ir-compiler --output=$@ $^

$(OUT)/$(PROG_BINNAME): $(PROG_VALA_FILES) $(PROG_VAPI_FILES) | $(OUT) $(OUT)/$(LIB_LIBNAME)
	valac --save-temps -v -d $(OUT) $(VALAFLAGS) $^ --target-glib $(TARGET_GLIB) \
	--pkg posix --pkg $(PROJECT) -X -l$(LIB_NAME) -o ../$@

typelib-symlink:
	ln -sv "$(PWD)/$(OUT)/$(LIB_TYPELIB)" "/usr/lib/girepository-1.0/$(LIB_TYPELIB)"

install: all
	mkdir -p $(DESTDIR)$(PREFIX)/lib/girepository-1.0
	cp -v $(OUT)/$(LIB_TYPELIB) $(DESTDIR)$(PREFIX)/lib/girepository-1.0/

clean:
	rm -rf $(OUT)

distclean: clean
	rm -rf config.mk
