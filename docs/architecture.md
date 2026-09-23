# Architecture

`engine.py` owns state, metadata, retrieval, QA and provider contracts. The CLI only loads synthetic fixtures. `MockProvider` writes a JSON render manifest; `LocalFFmpegProvider` renders a blank synthetic MP4 for adapter testing; `ExternalProviderInterface` always raises `NOT_CONFIGURED`. Missing material produces `GAP`, render errors produce `FAILED` and increment retries, mechanical QA produces `HUMAN_REVIEW`, and a separate explicit call to `approve` produces `APPROVED`. There is no automatic publish.
