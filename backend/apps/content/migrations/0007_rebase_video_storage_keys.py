"""Rebase Video.storage_key onto MEDIA_ROOT.

VIDEO_PLAYBACK_BASE_URL used to end in /media/videos/, so keys were stored
relative to that directory ("samples/x.m3u8"). It now ends at /media/ so that
one base serves videos, images and audio alike, which means existing keys need
their "videos/" prefix made explicit.

Absolute URLs are left alone — LocalVideoService passes those through untouched.
"""
from django.db import migrations

PREFIX = "videos/"


def _skip(key: str) -> bool:
    return (
        not key
        or key.startswith(PREFIX)
        or key.startswith("http://")
        or key.startswith("https://")
    )


def add_prefix(apps, schema_editor):
    Video = apps.get_model("content", "Video")
    for video in Video.objects.exclude(storage_key="").iterator():
        if _skip(video.storage_key):
            continue
        video.storage_key = PREFIX + video.storage_key.lstrip("/")
        video.save(update_fields=["storage_key"])


def remove_prefix(apps, schema_editor):
    Video = apps.get_model("content", "Video")
    for video in Video.objects.filter(storage_key__startswith=PREFIX).iterator():
        video.storage_key = video.storage_key[len(PREFIX):]
        video.save(update_fields=["storage_key"])


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0006_lesson_import_ref_lesson_uniq_lesson_import_ref"),
    ]

    operations = [
        migrations.RunPython(add_prefix, remove_prefix),
    ]
