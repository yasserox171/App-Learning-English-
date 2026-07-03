import 'package:chewie/chewie.dart';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../../core/theme/app_theme.dart';

/// Plays a lesson video (MP4 over http; cleartext enabled) with optional
/// timed EN/AR subtitles (from Video.script.segments) and playback-speed
/// control (0.75x / 1x / 1.25x). Subtitle rows only appear when segment data
/// exists.
class VideoPlayerWidget extends StatefulWidget {
  const VideoPlayerWidget({
    super.key,
    required this.url,
    this.title,
    this.autoPlay = false,
    this.segments = const [],
  });

  final String url;
  final String? title;
  final bool autoPlay;

  /// [{start, end, narration_en, subtitle_ar}, ...] in seconds.
  final List segments;

  @override
  State<VideoPlayerWidget> createState() => _VideoPlayerWidgetState();
}

class _VideoPlayerWidgetState extends State<VideoPlayerWidget> {
  VideoPlayerController? _video;
  ChewieController? _chewie;
  bool _error = false;
  bool _showEn = true;
  bool _showAr = true;
  double _speed = 1.0;
  Map? _segment;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      final video = VideoPlayerController.networkUrl(Uri.parse(widget.url));
      await video.initialize();
      if (!mounted) {
        video.dispose();
        return;
      }
      video.addListener(_onTick);
      setState(() {
        _video = video;
        _chewie = ChewieController(
          videoPlayerController: video,
          autoPlay: widget.autoPlay,
          looping: false,
          aspectRatio: video.value.aspectRatio == 0
              ? 16 / 9
              : video.value.aspectRatio,
        );
      });
    } catch (_) {
      if (mounted) setState(() => _error = true);
    }
  }

  void _onTick() {
    if (widget.segments.isEmpty || _video == null) return;
    final s = _video!.value.position.inMilliseconds / 1000.0;
    Map? active;
    for (final seg in widget.segments) {
      final start = (seg['start'] ?? 0).toDouble();
      final end = (seg['end'] ?? 0).toDouble();
      if (s >= start && s < end) {
        active = seg as Map;
        break;
      }
    }
    if (!identical(active, _segment) && mounted) {
      setState(() => _segment = active);
    }
  }

  Future<void> _setSpeed(double v) async {
    await _video?.setPlaybackSpeed(v);
    if (mounted) setState(() => _speed = v);
  }

  @override
  void dispose() {
    _video?.removeListener(_onTick);
    _chewie?.dispose();
    _video?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    Widget child;
    if (_error) {
      child = Container(
        height: 200,
        color: scheme.surfaceContainerHighest,
        child: const Center(child: Icon(Icons.error_outline, size: 48)),
      );
    } else if (_chewie == null) {
      child = Container(
        height: 200,
        color: scheme.surfaceContainerHighest,
        child: const Center(child: CircularProgressIndicator()),
      );
    } else {
      child = AspectRatio(
        aspectRatio: _video!.value.aspectRatio == 0
            ? 16 / 9
            : _video!.value.aspectRatio,
        child: Chewie(controller: _chewie!),
      );
    }

    final hasSubs = widget.segments.isNotEmpty;
    final en = (_segment?['narration_en'] ??
            _segment?['text_en'] ??
            _segment?['en'] ??
            '')
        .toString();
    final ar = (_segment?['subtitle_ar'] ??
            _segment?['text_ar'] ??
            _segment?['ar'] ??
            '')
        .toString();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.title != null && widget.title!.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(widget.title!,
                style: Theme.of(context).textTheme.titleMedium),
          ),
        ClipRRect(borderRadius: BorderRadius.circular(14), child: child),
        if (hasSubs && (_showEn && en.isNotEmpty || _showAr && ar.isNotEmpty))
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(top: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: scheme.surfaceContainerHighest.withOpacity(0.6),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: [
                if (_showEn && en.isNotEmpty)
                  Text(
                    en,
                    textAlign: TextAlign.center,
                    textDirection: TextDirection.ltr,
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.w600),
                  ),
                if (_showAr && ar.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      ar,
                      textAlign: TextAlign.center,
                      textDirection: TextDirection.rtl,
                      style: TextStyle(color: scheme.onSurfaceVariant),
                    ),
                  ),
              ],
            ),
          ),
        if (_video != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(
              children: [
                if (hasSubs) ...[
                  _Toggle(
                    label: 'EN',
                    on: _showEn,
                    onTap: () => setState(() => _showEn = !_showEn),
                  ),
                  const SizedBox(width: 8),
                  _Toggle(
                    label: 'AR',
                    on: _showAr,
                    onTap: () => setState(() => _showAr = !_showAr),
                  ),
                ],
                const Spacer(),
                for (final v in const [0.75, 1.0, 1.25])
                  Padding(
                    padding: const EdgeInsetsDirectional.only(start: 6),
                    child: _Toggle(
                      label: v == 1.0 ? '1x' : '${v}x',
                      on: _speed == v,
                      onTap: () => _setSpeed(v),
                    ),
                  ),
              ],
            ),
          ),
      ],
    );
  }
}

class _Toggle extends StatelessWidget {
  const _Toggle({required this.label, required this.on, required this.onTap});

  final String label;
  final bool on;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      borderRadius: BorderRadius.circular(20),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: on ? AppTheme.primary : scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: on ? Colors.white : scheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }
}
