from typing import Any

RULES: list[tuple[str, str]] = [
    ('ImagePullBackOff', 'Image pull failed. Check image name/tag and registry access.'),
    ('ErrImagePull', 'Container image could not be pulled from registry.'),
    ('OOMKilled', 'Container was OOMKilled. Review memory requests/limits and runtime usage.'),
    ('CrashLoopBackOff', 'Pod is crash looping. App process likely exits or startup checks fail.'),
    ('CreateContainerConfigError', 'Container config error. ConfigMap/Secret/env reference may be invalid.'),
]


def likely_cause(container_statuses: list[dict[str, Any]], extra_signals: list[str] | None = None) -> dict[str, str]:
    signals: list[str] = []
    for status in container_statuses:
        signals.extend([
            str(status.get('state_reason', '')),
            str(status.get('last_state_reason', '')),
            str(status.get('message', '')),
        ])
        if int(status.get('restart_count', 0) or 0) >= 3:
            signals.append('CrashLoopBackOff')

    if extra_signals:
        signals.extend(str(signal) for signal in extra_signals)

    lowered = [signal.lower() for signal in signals]
    for keyword, diagnosis in RULES:
        needle = keyword.lower()
        if any(needle in signal for signal in lowered):
            return {'signal': keyword, 'diagnosis': diagnosis}

    if any('back-off restarting failed container' in signal for signal in lowered):
        return {'signal': 'CrashLoopBackOff', 'diagnosis': 'Pod is crash looping. App process likely exits or startup checks fail.'}

    return {'signal': 'None', 'diagnosis': 'No clear crash-loop signal detected from container states.'}
