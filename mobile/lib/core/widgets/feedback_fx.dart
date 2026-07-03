import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

/// Horizontal shake (wrong answer). Increment [trigger] to replay.
class ShakeX extends StatelessWidget {
  const ShakeX({super.key, required this.trigger, required this.child});

  final int trigger;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (trigger == 0) return child;
    return child
        .animate(key: ValueKey('shake$trigger'))
        .shake(hz: 6, offset: const Offset(8, 0), rotation: 0);
  }
}

/// Brief colored tint flash (green for correct, red for wrong). Increment
/// [trigger] to replay.
class FlashGlow extends StatelessWidget {
  const FlashGlow({
    super.key,
    required this.trigger,
    required this.color,
    required this.child,
  });

  final int trigger;
  final Color color;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (trigger == 0) return child;
    return child
        .animate(key: ValueKey('flash$trigger'))
        .tint(color: color, begin: 0, end: 0.30, duration: 160.ms)
        .then()
        .tint(color: color, begin: 0.30, end: 0, duration: 280.ms);
  }
}

/// Gentle infinite pulse (the current phase dot).
class Pulse extends StatelessWidget {
  const Pulse({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return child
        .animate(onPlay: (c) => c.repeat(reverse: true))
        .scale(
          begin: const Offset(1, 1),
          end: const Offset(1.18, 1.18),
          duration: 600.ms,
          curve: Curves.easeInOut,
        );
  }
}
