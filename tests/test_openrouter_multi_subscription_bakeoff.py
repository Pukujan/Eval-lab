from scripts.run_openrouter_multi_subscription_bakeoff import _stream_content


class _Response:
    def iter_lines(self) -> list[str]:
        return [
            'data: {"model":"x-ai/grok-4.6","choices":[{"delta":{"content":"{\\"label\\":\\""}}]}',
            'data: {"choices":[{"delta":{"content":"pass\\"}"}}]}',
            "data: [DONE]",
        ]


def test_stream_content_reassembles_openrouter_sse() -> None:
    content, model = _stream_content(_Response())

    assert content == '{"label":"pass"}'
    assert model == "x-ai/grok-4.6"
