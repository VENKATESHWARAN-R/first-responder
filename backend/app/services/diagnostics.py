from typing import Any

RULES: list[tuple[str, str]] = [
    ('ImagePullBackOff', 'Image pull failed. Check image name/tag and registry access.'),
    ('ErrImagePull', 'Container image could not be pulled from registry.'),
    ('OOMKilled', 'Container was OOMKilled. Review memory requests/limits and runtime usage.'),
    ('CrashLoopBackOff', 'Pod is crash looping. App process likely exits or startup checks fail.'),
    ('CreateContainerConfigError', 'Container config error. ConfigMap/Secret/env reference may be invalid.'),
]


def likely_cause(container_statuses: list[dict[str, Any]]) -> dict[str, str]:
    for status in container_statuses:
        signals = [
            status.get('state_reason', ''),
            status.get('last_state_reason', ''),
            status.get('message', ''),
        ]
        for signal in signals:
            for keyword, diagnosis in RULES:
                if keyword and keyword in signal:
                    return {'signal': keyword, 'diagnosis': diagnosis}
    return {'signal': 'None', 'diagnosis': 'No clear crash-loop signal detected from container states.'}
