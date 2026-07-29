import runpy
from unittest.mock import Mock

import pytest

from vcs_tree import cli


def test_main_forwards_cli_options(monkeypatch):
    scan = Mock()
    monkeypatch.setattr(cli, "vcs_tree", scan)

    assert cli.main(["somewhere", "--flat", "--text-symbols"]) == 0
    scan.assert_called_once_with("somewhere", tree_mode=False, text_symbols=True)


def test_parser_defaults_to_current_directory(monkeypatch):
    scan = Mock()
    monkeypatch.setattr(cli, "vcs_tree", scan)

    assert cli.main([]) == 0
    scan.assert_called_once_with(".", tree_mode=True, text_symbols=False)


def test_help_exits_successfully(capsys):
    with pytest.raises(SystemExit, match="0"):
        cli.main(["--help"])

    assert "Parallel VCS repo scanner" in capsys.readouterr().out


def test_module_launcher_exits_with_main_result(monkeypatch):
    monkeypatch.setattr(cli, "main", lambda: 7)

    with pytest.raises(SystemExit, match="7"):
        runpy.run_module("vcs_tree.__main__", run_name="__main__")
