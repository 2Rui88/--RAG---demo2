import json
from pathlib import Path

from app.rag.build_chunks import build_rag_chunks
from app.rag.chunker import chunk_policy_document
from app.rag.faq import generate_faq_chunks
from app.rag.loader import parse_txt_document


def write_sample_doc(tmp_path: Path) -> Path:
    path = tmp_path / "013_2025年广东省成人高校招生考试报名公告.txt"
    path.write_text(
        "\n".join(
            [
                "2025年广东省成人高校招生考试报名公告",
                "",
                "https://eea.gd.gov.cn/crgk/content/post_4768330.html",
                "",
                "根据有关文件规定，现将相关事项公告如下：",
                "一、招生对象和报名条件",
                "报考高起本或高起专的考生应为高级中等教育学校毕业生或者具有同等学力人员。",
                "二、报名时间和方式",
                "考生网上注册报名：9月9日9时—12日17时；考生网上缴费确认：9月9日9时—15日18时。",
                "三、网上缴费、确认报名",
                "我省成人高考考试收费标准为每科37元。未在规定时间缴费的考生将视为自行放弃报名及考试资格。",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_parse_txt_document_extracts_metadata_and_body(tmp_path):
    path = write_sample_doc(tmp_path)

    document = parse_txt_document(path)

    assert document.doc_id == "013"
    assert document.title == "2025年广东省成人高校招生考试报名公告"
    assert document.url == "https://eea.gd.gov.cn/crgk/content/post_4768330.html"
    assert document.year == "2025"
    assert document.source == "广东省教育考试院"
    assert document.text.startswith("根据有关文件规定")
    assert "https://" not in document.text


def test_parse_txt_document_keeps_body_after_url_on_same_line(tmp_path):
    path = tmp_path / "015_关于做好广东省2025年成人高考报名工作的通知.txt"
    path.write_text(
        "关于做好广东省2025年成人高考报名工作的通知\n"
        "https://eea.gd.gov.cn/crgk/content/post_4765939.html各地级以上市教育局："
        "考生网上注册报名：9月9日9时—12日17时；考生网上缴费确认：9月9日9时—15日18时。",
        encoding="utf-8",
    )

    document = parse_txt_document(path)

    assert document.text.startswith("各地级以上市教育局")
    assert "考生网上注册报名" in document.text
    assert "https://" not in document.text


def test_chunk_policy_document_uses_section_metadata(tmp_path):
    document = parse_txt_document(write_sample_doc(tmp_path))

    chunks = chunk_policy_document(document, target_size=120, max_size=180)

    assert chunks
    assert all(chunk.type == "policy_chunk" for chunk in chunks)
    assert any(chunk.section == "一、招生对象和报名条件" for chunk in chunks)
    assert any(chunk.section == "二、报名时间和方式" for chunk in chunks)
    assert chunks[0].source_title == document.title
    assert chunks[0].source_url == document.url


def test_generate_faq_chunks_extracts_high_confidence_questions(tmp_path):
    document = parse_txt_document(write_sample_doc(tmp_path))

    faqs = generate_faq_chunks(document)

    questions = [chunk.question for chunk in faqs]
    assert "2025年广东成人高考报名时间是什么时候？" in questions
    assert "2025年广东成人高考报名费是多少？" in questions
    fee = next(chunk for chunk in faqs if "报名费" in (chunk.question or ""))
    assert "每科37元" in (fee.answer or "")
    assert fee.source_doc_id == "013"


def test_generate_faq_chunks_handles_compacted_policy_text(tmp_path):
    path = tmp_path / "015_关于做好广东省2025年成人高考报名工作的通知.txt"
    path.write_text(
        "\n".join(
            [
                "关于做好广东省2025年成人高考报名工作的通知",
                "https://eea.gd.gov.cn/crgk/content/post_4765939.html",
                "二、报名时间和方式（一）报名时间考生网上注册报名：9月9日9时—12日17时；考生网上提交材料：9月9日9时—13日12时；考生网上缴费确认：9月9日9时—15日18时；报名点现场资格审核：9月9日9时—15日12时。",
                "（三）网上缴费、确认报名根据相关通知，我省成人高考考试收费标准为每科37元。审核通过的考生应在规定时间内认真核对本人缴费项目、确认缴费。",
            ]
        ),
        encoding="utf-8",
    )
    document = parse_txt_document(path)

    faqs = generate_faq_chunks(document)

    assert any(chunk.question == "2025年广东成人高考报名时间是什么时候？" for chunk in faqs)
    assert any(chunk.question == "2025年广东成人高考报名费是多少？" for chunk in faqs)


def test_build_rag_chunks_writes_expected_jsonl_files(tmp_path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "rag"
    source_dir.mkdir()
    write_sample_doc(source_dir)

    summary = build_rag_chunks(source_dir, output_dir)

    assert summary.document_count == 1
    assert summary.policy_chunk_count > 0
    assert summary.faq_chunk_count >= 2
    for name in ["documents.jsonl", "policy_chunks.jsonl", "faq_chunks.jsonl", "chunks.jsonl"]:
        assert (output_dir / name).exists()

    merged = [json.loads(line) for line in (output_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {item["type"] for item in merged} == {"policy_chunk", "faq"}


def test_build_rag_chunks_deduplicates_faq_questions_by_year(tmp_path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "rag"
    source_dir.mkdir()
    write_sample_doc(source_dir)
    duplicate = source_dir / "015_关于做好广东省2025年成人高考报名工作的通知.txt"
    duplicate.write_text((source_dir / "013_2025年广东省成人高校招生考试报名公告.txt").read_text(encoding="utf-8"), encoding="utf-8")

    build_rag_chunks(source_dir, output_dir)

    faqs = [json.loads(line) for line in (output_dir / "faq_chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    keys = [(item["year"], item["question"]) for item in faqs]
    assert len(keys) == len(set(keys))
