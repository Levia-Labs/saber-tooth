import shutil

from saber_tooth.fixer import DeleteWall, codec
from saber_tooth.mapio import load_map, write_map
from saber_tooth.model import Wall
from tests.test_api import MID
from tests.test_api import client as client
from tests.test_api import svc as svc
from tests.test_service import NAME, _propose


def test_wall_proposal_view_has_walls(client, svc):
    wall = Wall(4.0, 0, 0, 2.0, 1, 5)
    _propose(svc, MID, [DeleteWall("Hard", wall)], status="pending")
    view = client.get(f"/api/maps/{MID}/proposals").json()[0]
    expected = {"beat": 4.0, "x": 0, "y": 0, "duration": 2.0, "width": 1, "height": 5}
    assert view["walls_before"] == [expected]
    assert view["walls_after"] == []


def _store_walls(svc, walls):
    """Rewrite the stored map so its Hard difficulty carries `walls`."""
    folder = svc.levels / NAME
    bm = load_map(folder)
    bm.difficulties["Hard"].walls = list(walls)
    build = folder.parent.parent / "rebuild"
    write_map(bm, build, folder)
    for new in build.glob("*.dat"):
        shutil.copyfile(new, folder / new.name)


def test_wall_proposal_view_has_surrounding_walls(client, svc):
    deleted = Wall(4.0, 0, 0, 2.0, 1, 5)
    near, far = Wall(7.0, 3, 0, 1.0, 1, 5), Wall(40.0, 3, 0, 1.0, 1, 5)
    _store_walls(svc, [deleted, near, far])
    _propose(svc, MID, [DeleteWall("Hard", deleted)], status="pending")
    view = client.get(f"/api/maps/{MID}/proposals").json()[0]
    assert view["walls_context"] == [codec.wall_to_dict(near)]
    assert codec.wall_to_dict(deleted) in view["walls_before"]


def test_context_excludes_the_changed_wall(client, svc):
    deleted = Wall(4.0, 0, 0, 2.0, 1, 5)
    _store_walls(svc, [deleted])
    _propose(svc, MID, [DeleteWall("Hard", deleted)], status="pending")
    assert client.get(f"/api/maps/{MID}/proposals").json()[0]["walls_context"] == []
