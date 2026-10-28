"""The worn check with a fake OpenVR module; SteamVR is never touched."""

from types import SimpleNamespace

from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.vr.worn import WornMonitor, worn_from_level


class FakeOpenVr(SimpleNamespace):
    """Stands in for pyopenvr: records init and shutdown, answers scripted activity levels."""

    def __init__(self, levels, init_error=None):
        super().__init__(
            k_EDeviceActivityLevel_UserInteraction=1,
            k_EDeviceActivityLevel_Idle=0,
            k_EDeviceActivityLevel_Standby=3,
            k_unTrackedDeviceIndex_Hmd=0,
            VRApplication_Background=3,
            levels=list(levels),
            init_error=init_error,
            inits=0,
            shutdowns=0,
            asked=[],
        )

    def init(self, kind):
        if self.init_error:
            raise self.init_error
        self.inits += 1
        outer = self

        class System:
            def getTrackedDeviceActivityLevel(self, index):
                outer.asked.append(index)
                level = outer.levels.pop(0)
                if isinstance(level, Exception):
                    raise level
                return level

        return System()

    def shutdown(self):
        self.shutdowns += 1


def monitor(fake):
    lines = []
    return WornMonitor(lambda: fake, lines.append), lines


def test_user_interaction_means_worn():
    fake = FakeOpenVr([1])
    mon, _ = monitor(fake)
    assert mon.read(True) is True
    assert fake.asked == [0]


def test_idle_and_standby_mean_not_worn():
    mon, _ = monitor(FakeOpenVr([0, 3]))
    assert mon.read(True) is False
    assert mon.read(True) is False


def test_every_other_level_is_unknown():
    mon, _ = monitor(FakeOpenVr([2, 4, -1, 99]))
    assert [mon.read(True) for _ in range(4)] == [None, None, None, None]


def test_the_connection_is_reused_between_reads():
    fake = FakeOpenVr([1, 0, 1])
    mon, _ = monitor(fake)
    assert [mon.read(True) for _ in range(3)] == [True, False, True]
    assert fake.inits == 1


def test_a_missing_module_is_unknown_and_logged_once():
    lines = []
    mon = WornMonitor(lambda: None, lines.append)
    assert [mon.read(True) for _ in range(3)] == [None, None, None]
    assert len(lines) == 1 and "pyopenvr" in lines[0]


def test_steamvr_closed_means_unknown_and_closes_the_connection_once():
    fake = FakeOpenVr([1])
    mon, _ = monitor(fake)
    assert mon.read(True) is True
    assert mon.read(False) is None
    assert mon.read(False) is None
    assert fake.shutdowns == 1


def test_a_read_error_is_unknown_logged_once_and_reconnects_next_time():
    fake = FakeOpenVr([RuntimeError("compositor gone"), RuntimeError("again"), 1])
    mon, lines = monitor(fake)
    assert mon.read(True) is None
    assert mon.read(True) is None
    assert mon.read(True) is True
    assert fake.inits == 3 and fake.shutdowns == 2
    assert len(lines) == 1 and "compositor gone" in lines[0]


def test_a_failed_connection_is_unknown_and_logged_once():
    fake = FakeOpenVr([], init_error=RuntimeError("VRInitError_Init_NoServerForBackgroundApp"))
    mon, lines = monitor(fake)
    assert [mon.read(True) for _ in range(3)] == [None, None, None]
    assert len(lines) == 1 and "NoServerForBackgroundApp" in lines[0]


def test_a_module_without_the_constants_uses_the_openvr_values():
    bare = SimpleNamespace()
    assert worn_from_level(bare, 1) is True
    assert worn_from_level(bare, 0) is False
    assert worn_from_level(bare, 3) is False
    assert worn_from_level(bare, 2) is None


@given(st.integers(-1000, 1000))
def test_only_levels_zero_one_and_three_are_known(level):
    expected = {1: True, 0: False, 3: False}.get(level)
    assert worn_from_level(FakeOpenVr([]), level) is expected
