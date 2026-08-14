from cpgf.settings.paths import REPO_ROOT


def test_core_directories_exist():
    expected = [
        "config",
        "data",
        "docs",
        "notebooks",
        "scripts",
        "src/cpgf",
        "pages",
        "tests",
        ".github/workflows",
    ]

    for relative_path in expected:
        assert (REPO_ROOT / relative_path).exists(), relative_path
