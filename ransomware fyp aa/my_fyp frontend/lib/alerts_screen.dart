import 'package:flutter/material.dart';

import 'api_client.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final data = await ApiClient.getJson('/alerts');
    final list = (data['alerts'] as List?) ?? [];
    return list.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Alerts', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.teal[700],
        centerTitle: true,
        actions: [
          IconButton(
            onPressed: () {
              setState(() {
                _future = _load();
              });
            },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: FutureBuilder<List<Map<String, dynamic>>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  'Failed to load alerts.\nTip: Settings > Backend URL',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            );
          }

          final alerts = snap.data ?? const [];
          if (alerts.isEmpty) {
            return const Center(child: Text('No alerts yet.'));
          }

          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: alerts.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, i) {
              final a = alerts[i];
              final kind = (a['kind'] ?? 'info').toString();
              final msg = (a['message'] ?? '').toString();
              final timeRaw = (a['time'] ?? '').toString();
              
              String parsedTime = timeRaw;
              try {
                if (timeRaw.isNotEmpty && timeRaw != 'null') {
                  final parsed = DateTime.parse(timeRaw).toLocal();
                  final hour12 = parsed.hour % 12 == 0 ? 12 : parsed.hour % 12;
                  final period = parsed.hour >= 12 ? 'PM' : 'AM';
                  final minute = parsed.minute.toString().padLeft(2, '0');
                  
                  parsedTime = 'Date: ${parsed.year}-${parsed.month.toString().padLeft(2, '0')}-${parsed.day.toString().padLeft(2, '0')}  Time: $hour12:$minute $period';
                }
              } catch (_) {}

              final isRansom = kind.toLowerCase() == 'ransomware';
              final icon = isRansom ? Icons.warning : Icons.notifications;
              final color = isRansom ? Colors.red : Colors.orange;

              final meta = a['meta'] as Map? ?? {};
              final suspiciousFiles = meta['suspicious_files'] as List? ?? [];
              String subtitleText = parsedTime;
              if (suspiciousFiles.isNotEmpty) {
                subtitleText += '\nSuspicious Files:\n' + suspiciousFiles.map((f) => '- ${f['path']}').join('\n');
              }

              return Card(
                elevation: 5,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                child: ListTile(
                  leading: Icon(icon, color: color),
                  title: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text(subtitleText),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
