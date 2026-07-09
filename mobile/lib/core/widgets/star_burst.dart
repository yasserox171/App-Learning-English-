import 'dart:math';

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// A one-shot burst of little stars that fly upward and fade out — played
/// over the correct bubble (UX prompt 1.1). Re-key the widget to replay.
class StarBurst extends StatefulWidget {
  const StarBurst({super.key, this.count = 7, this.size = 140});

  final int count;
  final double size;

  @override
  State<StarBurst> createState() => _StarBurstState();
}

class _Star {
  _Star(Random rnd)
      : dx = rnd.nextDouble() * 2 - 1, // -1..1 horizontal drift
        rise = 0.6 + rnd.nextDouble() * 0.4, // how high it flies
        delay = rnd.nextDouble() * 0.25,
        scale = 0.6 + rnd.nextDouble() * 0.8,
        spin = (rnd.nextDouble() * 2 - 1) * pi;

  final double dx;
  final double rise;
  final double delay;
  final double scale;
  final double spin;
}

class _StarBurstState extends State<StarBurst>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..forward();
  late final List<_Star> _stars =
      List.generate(widget.count, (_) => _Star(Random()));

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: SizedBox(
        width: widget.size,
        height: widget.size,
        child: AnimatedBuilder(
          animation: _c,
          builder: (_, __) {
            return Stack(
              clipBehavior: Clip.none,
              alignment: Alignment.center,
              children: [
                for (final s in _stars)
                  _buildStar(s, _c.value),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildStar(_Star s, double t) {
    // Per-star local time with its own start delay.
    final lt = ((t - s.delay) / (1 - s.delay)).clamp(0.0, 1.0);
    if (lt == 0) return const SizedBox.shrink();
    final eased = Curves.easeOut.transform(lt);
    final dy = -widget.size * s.rise * eased;
    final dx = widget.size * 0.35 * s.dx * eased;
    final opacity = (1 - lt).clamp(0.0, 1.0);
    return Positioned(
      top: widget.size / 2 + dy,
      left: widget.size / 2 + dx - 12,
      child: Opacity(
        opacity: opacity,
        child: Transform.rotate(
          angle: s.spin * eased,
          child: Icon(
            Icons.star_rounded,
            size: 24 * s.scale,
            color: Color.lerp(
                AppTheme.accent, Colors.amber.shade300, s.scale - 0.6),
          ),
        ),
      ),
    );
  }
}
