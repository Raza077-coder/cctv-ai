"""Unit tests for tracking, behavior analytics, motion, ANPR normalization."""
from app.analytics.behavior import BehaviorAnalyzer, ZoneAnalyzer
from app.analytics.crowd import crowd_level, zone_counts
from app.anpr.plate import normalize_plate
from app.tracking.tracker import IoUTracker, _iou
import pytest


class FakeDet:
    def __init__(self, class_name, bbox):
        self.class_name = class_name
        self.bbox = bbox


def test_iou():
    a = (0, 0, 10, 10)
    assert _iou(a, (0, 0, 10, 10)) == pytest.approx(1.0)
    assert _iou(a, (20, 20, 30, 30)) == 0.0
    assert 0.3 < _iou(a, (0, 5, 10, 15)) < 0.4


def test_tracker_assigns_stable_ids():
    tracker = IoUTracker()
    dets1 = [FakeDet("person", (0, 0, 40, 80)), FakeDet("car", (100, 100, 200, 140))]
    r1 = tracker.update(dets1)
    ids1 = {tid for tid, _, _ in r1}
    assert len(ids1) == 2

    # same objects slightly moved -> same IDs
    dets2 = [FakeDet("person", (2, 1, 42, 81)), FakeDet("car", (101, 100, 201, 141))]
    r2 = tracker.update(dets2)
    ids2 = {tid for tid, _, _ in r2}
    assert ids1 == ids2


def test_tracker_class_consistency():
    tracker = IoUTracker()
    tracker.update([FakeDet("person", (0, 0, 40, 80))])
    # a car overlapping the person should NOT take the person's ID
    r = tracker.update([FakeDet("car", (0, 0, 40, 80))])
    person_id = tracker.update([])
    car_ids = {tid for tid, _, cls in r if cls == "car"}
    assert len(car_ids) == 1
    assert car_ids != person_id


def test_zone_point_in_polygon():
    poly = [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert ZoneAnalyzer.point_in_polygon(50, 50, poly)
    assert not ZoneAnalyzer.point_in_polygon(150, 150, poly)
    assert not ZoneAnalyzer.point_in_polygon(10, 10, [])


def test_behavior_restricted_zone():
    analyzer = BehaviorAnalyzer()
    analyzer.set_zone([[0, 0], [200, 0], [200, 200], [0, 200]])
    results = analyzer.analyze([(7, (10, 10, 20, 60), "person")], people_count=1, now=100.0)
    rules = {r.rule for r in results}
    assert "restricted_zone" in rules


def test_behavior_loitering_and_crowd():
    analyzer = BehaviorAnalyzer(loiter_seconds=2, crowd_threshold=3)
    # loitering: same person across many frames
    results = analyzer.analyze([(1, (10, 10, 30, 80), "person")], people_count=1, now=0.0)
    results = analyzer.analyze([(1, (10, 10, 30, 80), "person")], people_count=1, now=3.0)
    rules = {r.rule for r in results}
    assert "loitering" in rules

    # crowd
    results = analyzer.analyze([], people_count=5, now=6.0)
    rules = {r.rule for r in results}
    assert "crowd" in rules


def test_behavior_wrong_direction():
    analyzer = BehaviorAnalyzer(expected_flow=(0.0, -1.0))
    # feed 5+ frames moving downward (against the expected upward flow)
    frames = [(0.0, 10), (0.1, 60), (0.2, 110), (0.3, 160), (0.4, 210)]
    all_rules: set[str] = set()
    for now, y in frames:
        results = analyzer.analyze([(1, (10, y, 30, y + 70), "person")], people_count=0, now=now)
        all_rules |= {r.rule for r in results}
    assert "wrong_direction" in all_rules


def test_crowd_levels():
    assert crowd_level(0) == "empty"
    assert crowd_level(1) == "low"
    assert crowd_level(5) == "moderate"
    assert crowd_level(10) == "high"
    assert crowd_level(20) == "critical"


def test_zone_counts():
    people = [(25.0, 25.0), (75.0, 75.0)]
    cells = zone_counts(people, grid=(2, 2))
    total = sum(c["count"] for c in cells)
    assert total == 2
    assert len(cells) == 4


def test_normalize_plate():
    assert normalize_plate("ABC-123") == "ABC123"
    assert normalize_plate("  le 8 8 1 2 ") == "LE8812"
    assert normalize_plate("xyz") == "XYZ"
