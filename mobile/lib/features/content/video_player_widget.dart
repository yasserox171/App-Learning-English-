import 'package:chewie/chewie.dart';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

/// Plays a lesson video from a network URL (MP4 over http; cleartext enabled).
class VideoPlayerWidget extends StatefulWidget {
  const VideoPlayerWidget({super.key, required this.url, this.title});

  final String url;
  final String? title;

  @override
  State<VideoPlayerWidget> createState() => _VideoPlayerWidgetState();
}

class _VideoPlayerWidgetState extends State<VideoPlayerWidget> {
  VideoPlayerController? _video;
  ChewieController? _chewie;
  bool _error = false;

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
      setState(() {
        _video = video;
        _chewie = ChewieController(
          videoPlayerController: video,
          autoPlay: false,
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

  @override
  void dispose() {
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
      ],
    );
  }
}
