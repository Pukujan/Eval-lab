from scripts.run_qwen_streaming_retry import _stream_content


class _Response:
    def iter_lines(self) -> list[str]:
        return [
            'data: {"model":"qwen3.8-flash","choices":[{"delta":{"content":"{\\"label\\":\\""}}]}',
            'data: {"choices":[{"delta":{"content":"pass\\"}"}}]}',
            "data: [DONE]",
        ]


def test_stream_content_reassembles_sse_delta_text() -> None:
    content, model = _stream_content(_Response())

    assert content == '{"label":"pass"}'
    assert model == "qwen3.8-flash"
