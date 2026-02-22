from app.services.diagnostics import likely_cause


def test_likely_cause_detects_oomkilled() -> None:
    result = likely_cause([{'state_reason': '', 'last_state_reason': 'OOMKilled', 'message': ''}])
    assert result['signal'] == 'OOMKilled'


def test_likely_cause_detects_crashloop_from_event_signal() -> None:
    result = likely_cause([], ['Back-off restarting failed container app in pod demo'])
    assert result['signal'] == 'CrashLoopBackOff'


def test_likely_cause_detects_crashloop_from_restarts() -> None:
    result = likely_cause([{'state_reason': '', 'last_state_reason': '', 'message': '', 'restart_count': 5}])
    assert result['signal'] == 'CrashLoopBackOff'
