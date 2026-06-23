from pathlib import Path


def test_rag_source_display_keeps_only_filename_and_score():
    app_js = Path("static/app.js").read_text(encoding="utf-8")
    render_start = app_js.index("function renderRagSources")
    render_end = app_js.index("function renderQuickReplies")
    render_source = app_js[render_start:render_end]

    assert "source.source_title || \"未命名文件\"" in render_source
    assert "得分 " in render_source
    assert "chunk_id" not in render_source
    assert "no-id" not in render_source
