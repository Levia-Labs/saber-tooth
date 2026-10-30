from saber_tooth import jobs_child


def test_the_busy_timeout_statement_matches_its_constant():
    # PRAGMA cannot take bound parameters, so the statement is a literal; keep the two in step.
    assert f"PRAGMA busy_timeout={jobs_child.BUSY_TIMEOUT_MS}" == jobs_child.BUSY_TIMEOUT_SQL
