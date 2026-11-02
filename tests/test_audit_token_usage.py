import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("audit_token_usage", Path(__file__).parents[1] / "scripts/audit_token_usage.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def meta(sid="root", parent=None):
    source = {"subagent": {"thread_spawn": {"parent_thread_id": parent}}} if parent else "vscode"
    return {"type": "session_meta", "payload": {"id": sid, "source": source}}


def usage(inp, cached=0, output=10, reasoning=2):
    values = {"input_tokens": inp, "output_tokens": output, "reasoning_output_tokens": reasoning}
    if cached is not None:
        values["cached_input_tokens"] = cached
    return {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": values}}}


def tool(kind, name=None, call_id="one", output="secret-output"):
    return {"type": "response_item", "payload": {"type": kind, "name": name, "call_id": call_id,
                                                   "arguments": "secret-arguments", "input": "secret-input", "output": output}}


class AuditTokenUsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, events):
        path = self.root / name
        path.write_text("\n".join(json.dumps(x) for x in events) + "\n")
        return path

    def test_latest_snapshot_not_sum_and_reasoning_not_double_counted(self):
        path = self.write("a.jsonl", [meta(), usage(100, 80), usage(100, 80), usage(200, 150, 30, 5)])
        rec = audit.audit_paths([path])["sessions"][0]
        self.assertEqual(rec["usage_latest"]["total_tokens"], 230)
        self.assertEqual(rec["usage_latest"]["noncached_input_tokens"], 50)
        self.assertEqual(rec["phases"]["unattributed"]["input_tokens"], 200)

    def test_missing_and_invalid_cache_are_unknown(self):
        for cached in (None, 101, -1, True):
            with self.subTest(cached=cached):
                path = self.write("a.jsonl", [meta(), usage(100, cached)])
                rec = audit.audit_paths([path])["sessions"][0]
                self.assertIsNone(rec["usage_latest"]["noncached_input_tokens"])
                self.assertIn("missing_or_invalid_cache_counts", rec["warnings"])

    def test_reset_reports_latest_epoch_with_warning(self):
        path = self.write("a.jsonl", [meta(), usage(200, 100, 30), usage(20, 10, 5)])
        rec = audit.audit_paths([path])["sessions"][0]
        self.assertEqual(rec["counter_resets"], 1)
        self.assertEqual(rec["usage_latest"]["input_tokens"], 20)
        self.assertIn("counter_resets_latest_epoch_only", rec["warnings"])

    def test_malformed_lines_do_not_leak(self):
        path = self.write("a.jsonl", [meta(), usage(100)])
        with path.open("ab") as f:
            f.write(b"secret-malformed\n[]\n\xff\n")
        report = audit.audit_paths([path])
        self.assertEqual(report["sessions"][0]["warnings"]["malformed_lines"], 2)
        self.assertNotIn("secret-malformed", json.dumps(report))

    def test_both_tool_formats_and_repeated_events(self):
        event = tool("function_call", "functions.spawn_agent")
        path = self.write("a.jsonl", [meta(), usage(100), event, event,
                          tool("function_call_output", output='{"agent_id":"child"}'),
                          tool("custom_tool_call", "exec", "two"),
                          tool("custom_tool_call_output", call_id="two", output="secret-custom")])
        report = audit.audit_paths([path])
        rec = report["sessions"][0]
        self.assertEqual(rec["coordination"]["spawn_agent"], 1)
        self.assertEqual(rec["tool_output_events"], 2)
        self.assertEqual(rec["tool_output_chars"], len('{"agent_id":"child"}') + len("secret-custom"))
        for secret in ("secret-custom", "secret-input", "secret-arguments"):
            self.assertNotIn(secret, json.dumps(report))
        self.assertEqual(report["teams"][0]["coverage"], "incomplete")

    def test_same_session_copies_are_not_added(self):
        first = self.write("a.jsonl", [meta(), usage(100)])
        self.write("b.jsonl", [meta(), usage(100)])
        report = audit.audit_paths([first, self.root, first])
        self.assertEqual(len(report["sessions"]), 1)
        self.assertEqual(report["duplicate_session_copies"], 1)

    def test_conflicting_copies_are_flagged(self):
        self.write("a.jsonl", [meta(), usage(100)])
        self.write("b.jsonl", [meta(), usage(100), usage(200)])
        report = audit.audit_paths([self.root])
        self.assertEqual(report["conflicting_session_copies"], 1)
        self.assertEqual(report["sessions"][0]["usage_latest"]["input_tokens"], 200)

    def test_linked_team_sum_and_missing_children(self):
        self.write("a.jsonl", [meta(), usage(100), tool("function_call", "spawn_agent"),
                              tool("function_call_output", output='{"agent_id":"child"}')])
        missing = audit.audit_paths([self.root])["teams"][0]
        self.assertIsNone(missing["reported_session_sum"])
        self.assertEqual(missing["missing_or_unverified_children"], ["child"])
        self.write("b.jsonl", [meta("child", "root"), usage(40)])
        linked = audit.audit_paths([self.root])["teams"][0]
        self.assertEqual(linked["coverage"], "linked_logs_complete")
        self.assertEqual(linked["reported_session_sum"]["input_tokens"], 140)

    def test_unrelated_sessions_not_aggregated(self):
        self.write("a.jsonl", [meta("a"), usage(100)])
        self.write("b.jsonl", [meta("b"), usage(40)])
        report = audit.audit_paths([self.root])
        self.assertTrue(all(team["reported_session_sum"] is None for team in report["teams"]))

    def test_orphan_parent_is_incomplete(self):
        path = self.write("a.jsonl", [meta("child", "missing"), usage(40)])
        self.assertEqual(audit.audit_paths([path])["teams"][0]["coverage"], "incomplete")

    def test_no_usage_is_explicit(self):
        path = self.write("a.jsonl", [meta()])
        rec = audit.audit_paths([path])["sessions"][0]
        self.assertIsNone(rec["usage_latest"])
        self.assertIn("no_usage", rec["warnings"])
        self.assertFalse(rec["phase_deltas_complete"])

    def test_only_explicit_phase_markers_attribute_deltas(self):
        phase = {"type": "event_msg", "payload": {"type": "phase_start", "phase": "visual"}}
        path = self.write("a.jsonl", [meta(), usage(100), phase, usage(160, 0, 20),
                                    {"type": "response_item", "payload": {"type": "message", "content": "audio"}},
                                    usage(200, 0, 25)])
        rec = audit.audit_paths([path])["sessions"][0]
        self.assertEqual(rec["phases"]["visual"]["input_tokens"], 100)
        self.assertEqual(rec["phases"]["visual"]["output_tokens"], 15)
        self.assertNotIn("audio", rec["phases"])

    def test_cli_formats_and_read_only(self):
        path = self.write("a.jsonl", [meta(), usage(100)])
        before = path.read_bytes()
        for fmt in ("json", "markdown"):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(audit.main([str(path), "--format", fmt]), 0)
            self.assertIn("root", output.getvalue())
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_cli_missing_path_does_not_echo_input(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            self.assertEqual(audit.main([str(self.root / "secret-path")]), 2)
        self.assertNotIn("secret-path", output.getvalue())

    def test_empty_directory_is_not_a_successful_audit(self):
        with self.assertRaises(ValueError):
            audit.audit_paths([self.root])

    def test_cyclic_parent_links_not_summed(self):
        self.write("a.jsonl", [meta("a", "b"), usage(100)])
        self.write("b.jsonl", [meta("b", "a"), usage(50)])
        report = audit.audit_paths([self.root])
        self.assertEqual(report["teams"], [])
        self.assertEqual(report["unassigned_session_ids"], ["a", "b"])

    def test_missing_core_usage_is_not_complete(self):
        event = usage(100)
        del event["payload"]["info"]["total_token_usage"]["output_tokens"]
        path = self.write("a.jsonl", [meta(), event])
        rec = audit.audit_paths([path])["sessions"][0]
        self.assertIn("missing_core_usage_counts", rec["warnings"])
        self.assertFalse(rec["phase_deltas_complete"])
        self.assertIsNone(rec["phases"]["unattributed"]["output_tokens"])


class TeamAuditTests(unittest.TestCase):
    setUp = AuditTokenUsageTests.setUp
    write = AuditTokenUsageTests.write
    def test_shared_session_id_distinct_thread_ids_and_guardian(self):
        root = meta('root')
        child = meta('child', 'root')
        child['payload']['session_id'] = 'root'
        child['payload']['source']['subagent']['thread_spawn']['agent_role'] = 'visual'
        guardian = meta('guard', 'root')
        guardian['payload'].update(session_id='root', parent_thread_id='root', thread_source='guardian_review', source={'subagent': {'other': 'guardian'}})
        self.write('a.jsonl', [root, usage(100), tool('function_call', 'spawn_agent'), tool('function_call_output', output='{"agent_id":"child"}')])
        self.write('b.jsonl', [child, usage(40), {'type': 'turn_context', 'payload': {'model': 'gpt-6.1-sol', 'encrypted_content': 'secret'}}])
        self.write('c.jsonl', [guardian, usage(500)])
        self.write('d.jsonl', [meta('unrelated'), usage(900)])
        report = audit.audit_paths([self.root], root_session='root')
        self.assertEqual({r['thread_id'] for r in report['sessions']}, {'root', 'child'})
        self.assertEqual(report['teams'][0]['reported_session_sum']['input_tokens'], 140)
        self.assertEqual(report['guardians'][0]['thread_id'], 'guard')
        self.assertEqual(report['summaries']['role']['visual']['threads'], 1)
        self.assertNotIn('secret', json.dumps(report))

    def test_wait_distribution_and_targets_only(self):
        call = tool('function_call', 'wait_agent')
        call['timestamp'] = '2026-11-02T00:00:00Z'
        output = tool('function_call_output', output='secret-body')
        output['timestamp'] = '2026-11-02T00:01:10Z'
        message = tool('function_call', 'followup_task', 'message')
        message['payload']['arguments'] = json.dumps({'target': '/root/visual', 'message': 'secret-text', 'encrypted_content': 'secret-encrypted'})
        self.write('a.jsonl', [meta(), usage(100), call, output, message])
        report = audit.audit_paths([self.root])
        rec = report['sessions'][0]
        self.assertEqual(rec['wait_seconds']['gte_60'], 1)
        self.assertEqual(rec['coordination_targets']['followup_task:/root/visual'], 1)
        self.assertNotIn('secret-', json.dumps(report))

    def test_comparison_with_incomplete_or_incomparable_scope(self):
        path = self.write('a.jsonl', [meta(), usage(100)])
        before = audit.audit_paths([path], 'root')
        path = self.write('a.jsonl', [meta(), usage(80)])
        after = audit.audit_paths([path], 'root')
        result = audit.compare_reports(before, after)
        self.assertEqual(result['comparison']['noncached_input_tokens']['delta'], -20)
        self.assertIsNone(result['comparison']['noncached_input_tokens']['change_rate'])
        for report in (before, after):
            report['comparison_context'] = {'scope': 'same', 'quality': 'all gates passed'}
        self.assertEqual(audit.compare_reports(before, after)['comparison']['noncached_input_tokens']['change_rate'], -.2)
        after['teams'][0]['coverage'] = 'incomplete'
        self.assertIsNone(audit.compare_reports(before, after)['comparison']['noncached_input_tokens']['change_rate'])


if __name__ == "__main__":
    unittest.main()
