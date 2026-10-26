from saber_tooth.fixer import DeleteWall
from saber_tooth.model import Wall
from tests.test_api import MID
from tests.test_api import client as client
from tests.test_api import svc as svc
from tests.test_service import _propose


def test_wall_proposal_view_has_walls(client, svc):
    wall = Wall(4.0, 0, 0, 2.0, 1, 5)
    _propose(svc, MID, [DeleteWall("Hard", wall)], status="pending")
    view = client.get(f"/api/maps/{MID}/proposals").json()[0]
    expected = {"beat": 4.0, "x": 0, "y": 0, "duration": 2.0, "width": 1, "height": 5}
    assert view["walls_before"] == [expected]
    assert view["walls_after"] == []
