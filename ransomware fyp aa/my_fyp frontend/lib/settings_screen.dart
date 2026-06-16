import 'package:flutter/material.dart';

import 'api_client.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _baseUrlCtrl = TextEditingController();
  final _maxFilesCtrl = TextEditingController();
  final _timeLimitCtrl = TextEditingController();
  final _pathsCtrl = TextEditingController();

  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final baseUrl = await ApiClient.getBaseUrl();
    _baseUrlCtrl.text = baseUrl;

    try {
      final s = await ApiClient.getJson('/settings');
      _maxFilesCtrl.text = (s['max_files'] ?? '').toString();
      _timeLimitCtrl.text = (s['time_limit_seconds'] ?? '').toString();
      final paths = (s['scan_paths'] as List?)?.map((e) => e.toString()).toList() ?? [];
      _pathsCtrl.text = paths.join('\n');
    } catch (_) {
      // Backend not reachable yet; user can still set URL.
    }

    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _baseUrlCtrl.dispose();
    _maxFilesCtrl.dispose();
    _timeLimitCtrl.dispose();
    _pathsCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await ApiClient.setBaseUrl(_baseUrlCtrl.text.trim());

      final paths = _pathsCtrl.text
          .split('\n')
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();

      final maxFiles = int.tryParse(_maxFilesCtrl.text.trim());
      final timeLimit = int.tryParse(_timeLimitCtrl.text.trim());

      await ApiClient.postJson('/settings', {
        if (paths.isNotEmpty) 'scan_paths': paths,
        if (maxFiles != null) 'max_files': maxFiles,
        if (timeLimit != null) 'time_limit_seconds': timeLimit,
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Settings saved')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to save. Check Backend URL.')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.teal[700],
        centerTitle: true,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('Backend', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          TextField(
            controller: _baseUrlCtrl,
            decoration: const InputDecoration(
              labelText: 'Backend URL',
              hintText: 'http://127.0.0.1:5000',
              prefixIcon: Icon(Icons.link),
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          const Text('Scan Settings', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _maxFilesCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Max files',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _timeLimitCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Time limit (sec)',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _pathsCtrl,
            minLines: 4,
            maxLines: 8,
            decoration: const InputDecoration(
              labelText: 'Scan paths (one per line)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save),
              label: Text(_saving ? 'Saving...' : 'Save'),
            ),
          ),
        ],
      ),
    );
  }
}
