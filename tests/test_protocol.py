import time

from src.acquisition.protocol import (
    FRAME_SIZE,
    FRAME_SYNC,
    BinaryStreamParser,
    CSVProtocolParser,
    Sample,
    SampleRateEstimator,
)


def _build_frame(counter: int, ecg: int, resp: int, status: int = 0) -> bytes:
    body = bytearray()
    body += FRAME_SYNC
    body += counter.to_bytes(4, "little", signed=False)
    body += (ecg & 0xFFFFFF).to_bytes(3, "little", signed=False)
    body += (resp & 0xFFFFFF).to_bytes(3, "little", signed=False)
    body.append(status & 0xFF)
    checksum = 0
    for b in body:
        checksum ^= b
    body.append(checksum)
    assert len(body) == FRAME_SIZE
    return bytes(body)


def test_csv_parser_parses_valid_line():
    parser = CSVProtocolParser()
    samples = parser.feed(b"1250,-138422,5021,0\n")
    assert samples == [Sample(1250, -138422, 5021, 0)]


def test_csv_parser_rejects_malformed_line():
    parser = CSVProtocolParser()
    samples = parser.feed(b"garbage,not,a,number,extra\n")
    assert samples == []
    assert parser.malformed_line_count == 1


def test_csv_parser_handles_partial_lines_across_feeds():
    parser = CSVProtocolParser()
    assert parser.feed(b"100,1,2,0") == []
    samples = parser.feed(b"\n200,3,4,0\n")
    assert [s.timestamp_ms for s in samples] == [100, 200]


def test_binary_parser_decodes_valid_frame():
    parser = BinaryStreamParser()
    frame = _build_frame(counter=42, ecg=-1000, resp=500, status=0)
    samples = parser.feed(frame)
    assert len(samples) == 1
    sample = samples[0]
    assert sample.timestamp_ms == 42
    assert sample.ecg_raw == -1000
    assert sample.resp_raw == 500
    assert parser.valid_frame_count == 1
    assert parser.corrupt_frame_count == 0


def test_binary_parser_resyncs_after_corruption():
    parser = BinaryStreamParser()
    good_frame = _build_frame(counter=1, ecg=100, resp=200, status=0)
    corrupted = bytearray(_build_frame(counter=2, ecg=300, resp=400, status=0))
    corrupted[-1] ^= 0xFF  # break the checksum
    stream = bytes(corrupted) + good_frame

    samples = parser.feed(stream)

    assert len(samples) == 1
    assert samples[0].timestamp_ms == 1
    assert parser.corrupt_frame_count >= 1


def test_sample_rate_estimator_reports_a_positive_rate():
    estimator = SampleRateEstimator(window_s=5.0)
    for _ in range(5):
        estimator.register_samples(50)
        time.sleep(0.02)

    assert estimator.total_samples == 250
    hz = estimator.estimated_hz
    assert hz is not None
    assert hz > 0
