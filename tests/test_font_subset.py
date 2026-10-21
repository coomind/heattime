"""3-3: the bundled Korean font subset covers KS X 1001 Hangul, ASCII and every character in the app text."""
from fontTools.ttLib import TTFont
from scripts.build_font_subset import OUT, WEIGHTS, app_chars, ks_x_1001_hangul, report


def test_subset_has_ks_x_1001_hangul_ascii_and_all_app_characters():
    for weight in WEIGHTS:
        cmap = set(TTFont(OUT/f'ibm-plex-sans-kr-subset-{weight}.woff').getBestCmap())
        assert {ord(c) for c in ks_x_1001_hangul()} <= cmap
        assert set(range(0x20, 0x7F)) <= cmap
        assert report(cmap)['missing_in_subset'] == [], 'run scripts/build_font_subset.py after changing app text'


def test_app_uses_the_subset_not_the_full_font_package():
    from pathlib import Path
    main = (Path(__file__).resolve().parents[1]/'frontend/src/main.jsx').read_text(encoding='utf-8')
    assert "import './fonts/fonts.css'" in main and '@fontsource/ibm-plex-sans-kr' not in main
    assert len(app_chars()) > 300
