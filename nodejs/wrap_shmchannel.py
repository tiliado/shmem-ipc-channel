#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(__file__))

from glibclasswrapper.binder import Binder
from glibclasswrapper.types import IntegerTyp, CallbackTyp, UnknownTyp

SHMCH_SPEC = {
    "target": "_shmchannel",
    "strip_prefix": "Shmch",
    "classes": [
        {
            "name": "ShmchChannel",
            "header": "shmchannel.h",
            "methods": [
                'ShmchChannel* shmch_channel_new (const gchar* name, ShmchMode mode)',
                'void shmch_channel_open (ShmchChannel* self, GError** error)',
                'void shmch_channel_set_request_callback (ShmchChannel* self, ShmchRequestCallback callback, '
                'void* callback_target, GDestroyNotify callback_target_destroy_notify)',
                'void shmch_channel_set_notification_callback(ShmchChannel * self, ShmchDataCallback callback, '
                    'void * callback_target, GDestroyNotify callback_target_destroy_notify)',
                'void shmch_channel_request(ShmchChannel * self, guint8 * data, int data_length1, ShmchDataCallback '
                    'response_callback, void * response_callback_target, GDestroyNotify '
                    'response_callback_target_destroy_notify, GError ** error)',
                'void shmch_channel_notify(ShmchChannel * self, guint8 * data, int data_length1, GError ** error)',
                'gboolean shmch_channel_send_receive(ShmchChannel * self, gboolean wait, GError ** error)',
                'void shmch_channel_close(ShmchChannel * self, GError ** error)',
                'const gchar * shmch_channel_get_name(ShmchChannel * self)',
                'ShmchMode shmch_channel_get_mode(ShmchChannel * self)',
                'gboolean shmch_channel_get_is_opened(ShmchChannel * self)',
            ],
        },
        {
            "name": 'ShmchIncomingRequest',
            'header': 'shmchannel.h',
            "methods": [
                'guint8* shmch_incoming_request_get_data (ShmchIncomingRequest* self, int* result_length1)',
                'void shmch_incoming_request_send_response (ShmchIncomingRequest* self, guint8* data, '
                    'int data_length1, GError** error)'
            ],
        }
    ],
    'callbacks': [
        'void ShmchDataCallback (guint8* data, int data_length1, void* user_data)',
        'void ShmchRequestCallback (ShmchIncomingRequest* request, void* user_data)',
    ],
    "types": {
        "ShmchMode": IntegerTyp,
        'ShmchRequestCallback': CallbackTyp,
        'ShmchDataCallback': CallbackTyp,
        'ShmchIncomingRequest*': UnknownTyp,
    }
}

print(Binder().bind_spec(SHMCH_SPEC).finish())
