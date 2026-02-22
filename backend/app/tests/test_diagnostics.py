from app.services.diagnostics import likely_cause


def test_likely_cause_detects_oomkilled() -> None:
    result = likely_cause([{'state_reason': '', 'last_state_reason': 'OOMKilled', 'message': ''}])
    assert result['signal'] == 'OOMKilled'
