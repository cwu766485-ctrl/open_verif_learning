"""Unit tests for the architectural tag-state reference model."""

import pytest

from dv.common.transaction import SimpleBusRequest
from dv.common.utils.cmd_code import CMD_READ, CMD_WRITE, CMD_WRITEBST, CMD_WRITELST
from dv.models.reference import CacheReferenceModel, SetAssociativeTagModel
from dv.scoreboard.cache_scoreboard import CacheScoreboard


def _request(addr, cmd=CMD_READ):
    return SimpleBusRequest(addr=addr, cmd=cmd, size=3)


def test_tag_model_checks_hits_misses_and_dirty_state():
    model = SetAssociativeTagModel()
    request = _request(0x12340)

    model.observe_access(request, was_miss=True)
    model.observe_access(_request(0x12348, CMD_WRITE), was_miss=False)

    states = model.candidate_states(0x12340 >> 6 & 0x7F)
    assert len(states) == 1
    line = next(iter(states))[0]
    assert line.tag == 0x12340 >> 13
    assert line.dirty
    assert (model.hits, model.misses) == (1, 1)


def test_tag_model_predicts_unambiguous_hits_and_misses_before_bus_evidence():
    model = SetAssociativeTagModel()
    request = _request(0x22000)

    assert model.predict_access(request).outcome == "miss"
    model.observe_access(request, was_miss=True)
    assert model.predict_access(_request(request.addr + 8)).outcome == "hit"


def test_full_dirty_set_predicts_legal_victim_addresses():
    model = SetAssociativeTagModel()
    addresses = [0x1000 + way * 0x2000 for way in range(5)]
    for addr in addresses[:4]:
        model.observe_access(_request(addr, CMD_WRITE), was_miss=True)

    prediction = model.predict_access(_request(addresses[4]))
    assert prediction.outcome == "miss"
    assert prediction.dirty_victim_required
    assert prediction.dirty_victims == frozenset(addr & ~0x3F for addr in addresses[:4])

    model.observe_access(_request(addresses[4]), was_miss=True)
    assert model.predict_access(_request(addresses[0])).outcome == "ambiguous"


def test_scoreboard_checks_dirty_writeback_address_and_every_data_beat():
    reference = CacheReferenceModel()
    scoreboard = CacheScoreboard(reference)
    addresses = [0x3000 + way * 0x2000 for way in range(5)]
    for way, addr in enumerate(addresses[:4]):
        for beat in range(8):
            reference.data[addr + beat * 8] = (way << 32) | beat
        reference.cache_tags.observe_access(_request(addr, CMD_WRITE), was_miss=True)

    request = _request(addresses[4])
    prediction = reference.cache_tags.predict_access(request, was_miss=True)
    victim = min(prediction.dirty_victims)
    memory_requests = [
        {
            "addr": victim,
            "cmd": CMD_WRITELST if beat == 7 else CMD_WRITEBST,
            "wmask": 0xFF,
            "wdata": reference.data[victim + beat * 8],
        }
        for beat in range(8)
    ]
    item = {"request": request, "memory_requests": memory_requests}
    scoreboard._check_dirty_writeback(item, prediction)

    memory_requests[3]["wdata"] ^= 1
    with pytest.raises(AssertionError, match="writeback beat 3"):
        scoreboard._check_dirty_writeback(item, prediction)


def test_tag_model_tracks_all_legal_full_set_victims():
    model = SetAssociativeTagModel()
    addresses = [0x1000 + way * 0x2000 for way in range(5)]

    for addr in addresses:
        model.observe_access(_request(addr), was_miss=True)

    states = model.candidate_states(0x1000 >> 6 & 0x7F)
    assert len(states) == model.WAYS
    assert all(len(state) == model.WAYS for state in states)
    # A reported hit is legal if the line remains in at least one candidate;
    # the observation then removes the candidates in which it was evicted.
    model.observe_access(_request(addresses[0]), was_miss=False)
    assert all(any(line.tag == addresses[0] >> 13 for line in state) for state in
               model.candidate_states(0x1000 >> 6 & 0x7F))


def test_tag_model_uses_highest_invalid_way_before_random_replacement():
    assert SetAssociativeTagModel.invalid_first_way(0b0000) == 3
    assert SetAssociativeTagModel.invalid_first_way(0b1000) == 2
    assert SetAssociativeTagModel.invalid_first_way(0b1100) == 1
    assert SetAssociativeTagModel.invalid_first_way(0b1110) == 0
    assert SetAssociativeTagModel.invalid_first_way(0b1111) is None


def test_probe_hit_invalidates_tag_and_release_uses_reference_data():
    reference = CacheReferenceModel()
    request = _request(0xA028, CMD_WRITE)
    request.wdata = 0xAABBCCDDEEFF0011
    request.wmask = 0xFF
    reference.predict(request)
    reference.cache_tags.observe_access(_request(request.addr), was_miss=True)

    assert reference.probe_release_data(request.addr) == [0xAABBCCDDEEFF0011, 0, 0, 0, 0, 0, 0, 0]
    reference.observe_probe(request.addr, was_hit=True)
    with pytest.raises(AssertionError, match="absent tag|impossible hit|predicted miss"):
        reference.observe_cache_access(_request(request.addr), was_miss=False)
    reference.observe_cache_access(_request(request.addr), was_miss=True)


@pytest.mark.parametrize("was_miss", [False, True])
def test_tag_model_rejects_impossible_hit_or_miss(was_miss):
    model = SetAssociativeTagModel()
    request = _request(0x8000)
    if was_miss:
        model.observe_access(request, was_miss=True)

    with pytest.raises(AssertionError, match="resident|absent|impossible|predicted"):
        model.observe_access(request, was_miss=was_miss)
