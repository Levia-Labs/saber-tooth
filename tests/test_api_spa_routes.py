import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from tests.test_api import svc  # noqa: F401


@pytest.mark.parametrize(
    "path", ["/beatsaver", "/beatsaver/playlists", "/beatsaver/playlists/52354", "/new"]
)
def test_client_routes_serve_the_shell_on_reload(svc, tmp_path, path):  # noqa: F811
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<html>shell</html>", encoding="utf-8")
    with TestClient(create_app(svc, web=web), base_url="http://localhost") as client:
        res = client.get(path)
    assert res.status_code == 200 and "shell" in res.text
