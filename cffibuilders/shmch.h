// glib.h
typedef char gchar;
typedef unsigned char guint8;
typedef void* gpointer;
typedef int gint;
typedef unsigned long   gulong;
typedef gint gboolean;
typedef struct _GError GError;

extern "Python" void destroy_notify(gpointer);
typedef void (*GDestroyNotify) (gpointer data);

void g_error_free(GError *error);
void g_clear_error(GError **err);

// shmchannel.h

typedef struct _ShmchIncomingRequest ShmchIncomingRequest;
typedef struct _ShmchShmem ShmchShmem;
typedef struct _ShmchChannel ShmchChannel;


extern "Python" void data_callback(guint8*, int, void*);
extern "Python" void request_callback(ShmchIncomingRequest*, void*);

typedef void (*ShmchDataCallback) (guint8* data, int data_length1, void* user_data);
typedef void (*ShmchRequestCallback) (ShmchIncomingRequest* request, void* user_data);

typedef enum  {
	SHMCH_ERROR_ALREADY_OPEN,
	SHMCH_ERROR_CLOSED,
	SHMCH_ERROR_INVALID_NAME,
	SHMCH_ERROR_INVALID_SIZE,
	SHMCH_ERROR_SHM_OPEN_FAILED,
	SHMCH_ERROR_SHM_CLOSE_FAILED,
	SHMCH_ERROR_RESOURCE_LIMIT
} ShmchError;

typedef enum  {
	SHMCH_MODE_SERVER,
	SHMCH_MODE_CLIENT
} ShmchMode;


gpointer shmch_incoming_request_ref (gpointer instance);
void shmch_incoming_request_unref (gpointer instance);
guint8* shmch_incoming_request_get_data (ShmchIncomingRequest* self, int* result_length1);
void shmch_incoming_request_send_response (ShmchIncomingRequest* self, guint8* data, int data_length1, GError** error);

gchar* shmch_get_error_message (GError* e);

gpointer shmch_shmem_ref (gpointer instance);
void shmch_shmem_unref (gpointer instance);
ShmchShmem* shmch_shmem_new (const gchar* name, gulong size, gboolean create, gboolean discard, GError** error);
guint8* shmch_shmem_get_buffer (ShmchShmem* self, int* result_length1);
void shmch_shmem_close (ShmchShmem* self, GError** error);
const gchar* shmch_shmem_get_name (ShmchShmem* self);
gulong shmch_shmem_get_size (ShmchShmem* self);
void* shmch_shmem_get_pointer (ShmchShmem* self);

gpointer shmch_channel_ref (gpointer instance);
void shmch_channel_unref (gpointer instance);
ShmchChannel* shmch_channel_new (const gchar* name, ShmchMode mode);
void shmch_channel_open (ShmchChannel* self, GError** error);
void shmch_channel_set_request_callback (ShmchChannel* self, ShmchRequestCallback callback, void* callback_target, GDestroyNotify callback_target_destroy_notify);
void shmch_channel_set_notification_callback (ShmchChannel* self, ShmchDataCallback callback, void* callback_target, GDestroyNotify callback_target_destroy_notify);
void shmch_channel_request (ShmchChannel* self, guint8* data, int data_length1, ShmchDataCallback response_callback, void* response_callback_target, GDestroyNotify response_callback_target_destroy_notify, GError** error);
void shmch_channel_notify (ShmchChannel* self, guint8* data, int data_length1, GError** error);
gboolean shmch_channel_send_receive (ShmchChannel* self, gboolean wait, GError** error);
void shmch_channel_close (ShmchChannel* self, GError** error);
const gchar* shmch_channel_get_name (ShmchChannel* self);
ShmchMode shmch_channel_get_mode (ShmchChannel* self);
gboolean shmch_channel_get_is_opened (ShmchChannel* self);
