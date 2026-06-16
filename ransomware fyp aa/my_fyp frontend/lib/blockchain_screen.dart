import 'package:flutter/material.dart';

import 'api_client.dart';

class BlockchainScreen extends StatefulWidget {
  const BlockchainScreen({super.key});

  @override
  State<BlockchainScreen> createState() => _BlockchainScreenState();
}

class _BlockchainScreenState extends State<BlockchainScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = ApiClient.getJson('/blockchain');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Blockchain', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.teal[700],
        centerTitle: true,
        actions: [
          IconButton(
            onPressed: () {
              setState(() {
                _future = ApiClient.getJson('/blockchain');
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
                  'Failed to load blockchain.\nTip: Settings > Backend URL',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            );
          }

          final data = snap.data ?? const {};
          final chainRaw = (data['chain'] as List?) ?? [];
          final chain = chainRaw.reversed.toList();

          if (chain.isEmpty) {
            return const Center(child: Text('No blocks yet.'));
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: chain.length,
            itemBuilder: (context, i) {
              final b = chain[i] as Map;
              final index = b['index'];
              final timeRaw = b['timestamp'].toString();
              final hash = (b['hash'] ?? '').toString();
              final prev = (b['previous_hash'] ?? '').toString();
              final rawData = b['data'];
              
              String displayData = rawData.toString();
              String timeToDisplay = timeRaw;

              if (rawData is Map) {
                final prediction = rawData['prediction'];
                String predText = prediction.toString();
                if (prediction == 'S' || prediction == 'Suspicious') predText = 'Suspicious';
                if (prediction == 1 || prediction == 'Safe') predText = 'Safe';
                
                final status = rawData['status'] ?? '';
                final user = rawData['username'] ?? '';
                final role = rawData['role'] ?? '';
                
                // If there's an internal timestamp, use it as it's more accurate to the event
                if (rawData.containsKey('timestamp')) {
                  timeToDisplay = rawData['timestamp'].toString();
                }

                displayData = 'Prediction: $predText\nStatus: $status\nUser: $user';
                if (role.toString().isNotEmpty) {
                  displayData += '\nRole: $role';
                }
              }

              // Better timestamp formatting if possible
              String formattedTime = timeToDisplay;
              try {
                // Try to parse the time (handles both ISO and YYYY-MM-DD HH:MM:SS)
                DateTime? parsed;
                try {
                   parsed = DateTime.parse(timeToDisplay).toLocal();
                } catch(_) {
                   // Fallback for non-standard formats if any
                }

                if (parsed != null) {
                  final hour12 = parsed.hour % 12 == 0 ? 12 : parsed.hour % 12;
                  final period = parsed.hour >= 12 ? 'PM' : 'AM';
                  final minute = parsed.minute.toString().padLeft(2, '0');
                  formattedTime = 'Date: ${parsed.year}-${parsed.month.toString().padLeft(2, '0')}-${parsed.day.toString().padLeft(2, '0')}  Time: $hour12:$minute $period';
                } else if (!timeToDisplay.contains('Date:')) {
                  formattedTime = 'Timestamp: $timeToDisplay';
                }
              } catch (_) {
                if (!timeToDisplay.contains('Date:')) {
                   formattedTime = 'Timestamp: $timeToDisplay';
                }
              }

              return Card(
                elevation: 4,
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Block #$index', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Colors.teal)),
                          const Icon(Icons.lock_outline, size: 18, color: Colors.grey),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(formattedTime, style: const TextStyle(fontWeight: FontWeight.w600)),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(8),
                        width: double.infinity,
                        decoration: BoxDecoration(
                          color: Colors.grey[100],
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(displayData, style: const TextStyle(fontFamily: 'monospace', fontSize: 13)),
                      ),
                      const SizedBox(height: 8),
                      Text('Hash: ${_short(hash)}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                      Text('Prev: ${_short(prev)}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }

  String _short(String s) => s.length <= 16 ? s : '${s.substring(0, 8)}…${s.substring(s.length - 6)}';
}
