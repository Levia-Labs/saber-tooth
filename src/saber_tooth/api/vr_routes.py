"""HTTP route for the VR runtime status; the logic lives in vr_status.py."""

from fastapi import FastAPI

from saber_tooth.api.vr_status import VrStatusClient


def register(app: FastAPI, client: VrStatusClient) -> None:
    @app.get("/api/vr/status")
    def vr_status():
        return client.status()
