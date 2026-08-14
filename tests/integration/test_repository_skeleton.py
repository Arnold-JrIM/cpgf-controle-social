from cpgf.settings.paths import REPO_ROOT

def test_core_directories_exist():
    for rel in ["config","data","docs","notebooks","scripts","src/cpgf","pages","tests",".github/workflows"]:
        assert (REPO_ROOT/rel).exists(), rel
