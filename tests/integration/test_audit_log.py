import json

from src.qnwis.data.audit.audit_log import FileAuditLog


def test_file_audit_log(tmp_path):
    log = FileAuditLog(str(tmp_path / 'audit' / 'events.ndjson'))
    log.append({'event_type': 'query_execute', 'payload': {'id': 'q'}})
    log.append({'event_type': 'query_execute', 'payload': {'id': 'q2'}})
    data = (tmp_path / 'audit' / 'events.ndjson').read_text(encoding='utf-8').strip().splitlines()
    assert len(data) == 2
    for line in data:
        obj = json.loads(line)
        assert 'ts' in obj and 'payload' in obj
