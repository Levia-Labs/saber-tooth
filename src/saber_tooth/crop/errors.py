"""Errors of the crop feature; the API turns a CropError into HTTP 422."""


class CropError(ValueError):
    """A crop cannot be planned or written; the message names the reason."""


class NoNotes(CropError):
    """No Standard difficulty has a note."""


class InvalidWindow(CropError):
    """The requested start and end break a window rule."""
