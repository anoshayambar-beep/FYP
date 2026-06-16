import 'package:flutter/material.dart';

import 'api_client.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = ApiClient.getJson('/reports');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Reports', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.teal[700],
        centerTitle: true,
        actions: [
          IconButton(
            onPressed: () {
              setState(() {
                _future = ApiClient.getJson('/reports');
              });
            },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'Failed to load reports.\nTip: Settings > Backend URL',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            );
          }

          final r = snap.data ?? const {};
          final scanEvents = r['scan_events'];
          final ransomwareEvents = r['ransomware_events'];
          final totalScanned = r['total_scanned_files'];
          
          final lastTimeRaw = r['last_event_time'] as String?;
          String lastTime = '—';
          if (lastTimeRaw != null) {
            try {
              final parsed = DateTime.parse(lastTimeRaw).toLocal();
              final hour12 = parsed.hour % 12 == 0 ? 12 : parsed.hour % 12;
              final period = parsed.hour >= 12 ? 'PM' : 'AM';
              final minute = parsed.minute.toString().padLeft(2, '0');
              lastTime = '${parsed.year}-${parsed.month.toString().padLeft(2, '0')}-${parsed.day.toString().padLeft(2, '0')} $hour12:$minute $period';
            } catch (e) {
              lastTime = lastTimeRaw;
            }
          }

          return Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                _reportCard(
                  icon: Icons.bar_chart,
                  title: 'Scan Summary',
                  lines: [
                    'Total scans: $scanEvents',
                    'Ransomware events: $ransomwareEvents',
                    'Total scanned files: $totalScanned',
                  ],
                ),
                const SizedBox(height: 16),
                _reportCard(
                  icon: Icons.schedule,
                  title: 'Last Activity',
                  lines: [
                    'Last event time:',
                    lastTime,
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _reportCard({required IconData icon, required String title, required List<String> lines}) {
    return Card(
      elevation: 5,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: Colors.teal[700]),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  for (final l in lines) Text(l),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
