from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.safe_fs import windows_safe_component
from saber_tooth.service.errors import RenameInvalid
from saber_tooth.service.rename import MAX_NAME, validate_map_name


@given(st.text(max_size=200))
def test_accepted_names_are_trimmed_and_make_safe_folders(raw):
    try:
        name, folder = validate_map_name(raw)
    except RenameInvalid:
        return
    assert name == raw.strip()
    assert 1 <= len(name) <= MAX_NAME
    assert "/" not in name and "\\" not in name
    assert windows_safe_component(folder)
    assert folder == folder.strip()
