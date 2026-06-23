from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from app.rag.loader import load_txt_documents
from app.rag.models import RagChunk, RagDocument


DEFAULT_OUTPUT = Path("data/rag_curated")
TITLE_NOISE = (
    "投档情况",
    "专业计划公布",
    "招生专业公布",
    "招生专业计划",
    "附件",
)
USELESS_CONTENT_MARKERS = (
    "请见附件",
    "详见附件",
)
INTENT_RULES = [
    {
        "key": "registration_time",
        "question": "{year}年广东成人高考报名时间是什么时候？",
        "aliases": ["广东成考什么时候报名？", "成人高考几号开始报名？", "成考报名截止时间是什么时候？"],
        "patterns": [
            r"网上注册报名时间为(?P<value>[^。；;]+)",
            r"考生网上注册报名[:：]?(?P<value>[^；;。]+)",
            r"报名时间为(?P<value>[^。；;]+)",
        ],
        "answer": "{year}年广东成人高考报名时间为{value}。",
        "tags": ["报名", "报名时间"],
    },
    {
        "key": "registration_fee",
        "question": "{year}年广东成人高考报名费是多少？",
        "aliases": ["广东成考报名费用是多少？", "成人高考考试费怎么收？", "成考每科多少钱？"],
        "patterns": [
            r"考试收费标准为(?P<value>每科\s*\d+元)",
            r"报名费和考试费[^。；;]*?(?P<value>每科\s*\d+元)",
        ],
        "answer": "根据{year}年相关通知，广东成人高考考试收费标准为{value}。",
        "tags": ["报名", "费用", "报名费"],
    },
    {
        "key": "registration_process",
        "question": "{year}年广东成人高考怎么报名？",
        "aliases": ["成人高考报名流程是什么？", "广东成考如何报名？", "成考网上报名怎么操作？"],
        "patterns": [
            r"(?:报名流程|报名方式)[^。；;]*?(?P<value>网上[^。；;]+(?:。|；|;)?[^。；;]*)",
            r"考生必须本人登录网上报名系统(?P<value>[^。；;]+)",
        ],
        "answer": "{year}年广东成人高考报名需按通知要求通过网上报名系统办理，{value}",
        "tags": ["报名", "报名流程", "网上报名"],
    },
    {
        "key": "registration_qualification",
        "question": "{year}年广东成人高考报名条件是什么？",
        "aliases": ["成人高考报名需要什么学历？", "专升本报名条件是什么？", "高起专报名条件是什么？"],
        "patterns": [
            r"(?:报考条件|报名条件|招生对象和报考条件)(?P<value>[^附件]{80,420})",
            r"(?:报考专升本的考生|报考高起本或高起专的考生)(?P<value>[^。]{30,260})",
        ],
        "answer": "{year}年广东成人高考报名条件需以当年招生通知为准。资料中提到：{value}",
        "tags": ["报名", "报名条件", "学历条件"],
    },
    {
        "key": "exam_time",
        "question": "{year}年广东成人高考考试时间是什么时候？",
        "aliases": ["成人高考什么时候考试？", "广东成考几号考试？"],
        "patterns": [
            r"成人高考(?:将于|于)(?P<value>[^。；;]+?)(?:举行|进行|开考)",
            r"考试时间[:：]?(?P<value>[^。；;]+)",
        ],
        "answer": "{year}年广东成人高考考试时间为{value}。",
        "tags": ["考试", "考试时间"],
    },
    {
        "key": "score_query",
        "question": "{year}年广东成人高考成绩什么时候公布？",
        "aliases": ["成人高考成绩怎么查询？", "广东成考成绩查询方式是什么？"],
        "patterns": [
            r"(?P<value>\d{1,2}月\d{1,2}日\d{1,2}[:：]\d{2}起[^。；;]*查询成绩)",
            r"成绩(?:于|将于)(?P<value>[^。；;]+?)(?:公布|发布)",
            r"考试成绩公布(?P<value>[^。]{30,260})",
        ],
        "answer": "{year}年广东成人高考成绩公布/查询安排为：{value}",
        "tags": ["成绩", "成绩查询", "成绩公布"],
    },
    {
        "key": "score_review",
        "question": "{year}年广东成人高考成绩可以复核吗？",
        "aliases": ["成人高考成绩复核怎么申请？", "成考成绩复查截止时间是什么？"],
        "patterns": [
            r"成绩复核(?P<value>[^。]{50,360})",
            r"复查分数(?P<value>[^。]{50,360})",
        ],
        "answer": "{year}年广东成人高考成绩复核安排为：{value}",
        "tags": ["成绩", "成绩复核"],
    },
    {
        "key": "admission_time",
        "question": "{year}年广东成人高考录取时间是什么时候？",
        "aliases": ["成人高考录取什么时候开始？", "广东成考录取结果什么时候出？"],
        "patterns": [
            r"录取工作于(?P<value>[^。；;]+?)(?:进行|开始)",
            r"录取(?:将于|工作将于|工作于)(?P<value>[^。；;]+?)(?:进行|开始)",
            r"录取工作(?P<value>[^。；;]*\d{1,2}月[^。；;]+)",
        ],
        "answer": "{year}年广东成人高考录取时间为{value}。",
        "tags": ["录取", "录取时间"],
    },
    {
        "key": "admission_query",
        "question": "{year}年广东成人高考录取结果怎么查询？",
        "aliases": ["成人高考录取查询方式是什么？", "广东成考录取结果在哪里查？"],
        "patterns": [
            r"(?P<value>考生也可自行查询[^。]{40,360})",
            r"录取结果[^。]{0,40}(?P<value>通过[^。]{40,360})",
            r"查询录取结果(?P<value>[^。]{30,260})",
        ],
        "answer": "{year}年广东成人高考录取结果查询方式为：{value}",
        "tags": ["录取", "录取结果", "查询方式"],
    },
    {
        "key": "cutoff_score",
        "question": "{year}年广东成人高考录取最低分数线是多少？",
        "aliases": ["成人高考分数线是多少？", "广东成考最低录取分数线是多少？"],
        "patterns": [
            r"录取最低分数线[^。]*如下[:：]?(?P<value>[^。]{80,520})",
            r"各批次录取最低分数线[^。]*如下[:：]?(?P<value>[^。]{80,520})",
        ],
        "answer": "{year}年广东成人高考录取最低分数线资料摘要：{value}",
        "tags": ["录取", "分数线"],
    },
    {
        "key": "volunteer_collection",
        "question": "{year}年广东成人高考征集志愿什么时候填？",
        "aliases": ["成人高考征集志愿对象是谁？", "广东成考征集志愿怎么填？"],
        "patterns": [
            r"征集志愿时间(?P<value>[^。；;]+)",
            r"征集志愿填报方式(?P<value>[^。]{40,320})",
        ],
        "answer": "{year}年广东成人高考征集志愿安排为：{value}",
        "tags": ["征集志愿", "志愿填报"],
    },
    {
        "key": "admission_ticket",
        "question": "{year}年广东成人高考准考证什么时候打印？",
        "aliases": ["成人高考准考证怎么打印？", "广东成考准考证打印入口是什么？"],
        "patterns": [
            r"(?P<value>报名成功的考生可于[^。]{10,180}(?:下载并打印准考证|打印准考证)[^。]*)",
            r"(?P<value>考生可于[^。]{10,180}(?:下载并打印准考证|打印准考证)[^。]*)",
            r"(?P<value>准考证打印[^。]{20,220})",
        ],
        "answer": "{year}年广东成人高考准考证相关安排为：{value}",
        "tags": ["准考证", "准考证打印"],
    },
]


@dataclass
class CuratedBuildSummary:
    source_dir: str
    output_dir: str
    document_count: int
    policy_chunk_count: int
    faq_chunk_count: int
    merged_chunk_count: int
    skipped_low_value_documents: int


def build_curated_knowledge(source_dir: Path, output_dir: Path = DEFAULT_OUTPUT) -> CuratedBuildSummary:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    documents = load_txt_documents(source_dir)
    useful_documents = [document for document in documents if not _is_low_value_document(document)]
    policy_chunks: list[RagChunk] = []
    faq_chunks: list[RagChunk] = []

    for document in useful_documents:
        policy_chunks.extend(_curated_policy_chunks(document))
        faq_chunks.extend(_curated_faq_chunks(document))

    faq_chunks = _deduplicate_chunks(faq_chunks)
    merged_chunks = [*faq_chunks, *policy_chunks]

    _write_jsonl(output_dir / "documents.jsonl", useful_documents)
    _write_jsonl(output_dir / "policy_chunks.jsonl", policy_chunks)
    _write_jsonl(output_dir / "faq_chunks.jsonl", faq_chunks)
    _write_jsonl(output_dir / "chunks.jsonl", merged_chunks)
    _write_report(
        output_dir / "README.md",
        source_dir,
        output_dir,
        len(documents),
        len(useful_documents),
        policy_chunks,
        faq_chunks,
    )

    return CuratedBuildSummary(
        source_dir=str(source_dir),
        output_dir=str(output_dir),
        document_count=len(useful_documents),
        policy_chunk_count=len(policy_chunks),
        faq_chunk_count=len(faq_chunks),
        merged_chunk_count=len(merged_chunks),
        skipped_low_value_documents=len(documents) - len(useful_documents),
    )


def _curated_policy_chunks(document: RagDocument) -> list[RagChunk]:
    chunks: list[RagChunk] = []
    sections = _split_semantic_sections(document.text)
    for section_title, section_text in sections:
        section_text = _clean_text(section_text)
        if _is_low_value_text(section_text):
            continue
        for index, content in enumerate(_split_by_sentence_window(section_text), start=1):
            if _is_low_value_text(content):
                continue
            chunks.append(
                RagChunk(
                    chunk_id=f"{document.doc_id}_{document.year or 'unknown'}_{_slug(section_title or 'section')}_{index:03d}",
                    type="policy_chunk",
                    content=content,
                    year=document.year,
                    source_doc_id=document.doc_id,
                    source_title=document.title,
                    source_url=document.url,
                    section=section_title,
                    aliases=_aliases_for_text(document, section_title, content),
                )
            )
    return chunks


def _curated_faq_chunks(document: RagDocument) -> list[RagChunk]:
    if not document.year:
        return []
    normalized = _clean_text(document.text)
    chunks: list[RagChunk] = []
    for rule in INTENT_RULES:
        for pattern in rule["patterns"]:
            match = re.search(pattern, normalized)
            if not match:
                continue
            value = _clean_answer_value(match.groupdict().get("value") or match.group(0))
            value = _post_process_value(str(rule["key"]), value)
            if len(value) < 4:
                continue
            question = rule["question"].format(year=document.year)
            answer = rule["answer"].format(year=document.year, value=value)
            chunks.append(
                RagChunk(
                    chunk_id=f"faq_{document.year}_{rule['key']}_{document.doc_id}",
                    type="faq",
                    question=question,
                    answer=answer,
                    content=f"问：{question}\n答：{answer}",
                    aliases=[str(item) for item in rule["aliases"]],
                    year=document.year,
                    source_doc_id=document.doc_id,
                    source_title=document.title,
                    source_url=document.url,
                    section="、".join(str(item) for item in rule["tags"]),
                )
            )
            break
    return chunks


def _split_semantic_sections(text: str) -> list[tuple[str | None, str]]:
    cleaned = _clean_text(text)
    pattern = re.compile(r"(?=(?:[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）|附件\d*[:：]?)[^。；;]{2,80})")
    starts = [match.start() for match in pattern.finditer(cleaned)]
    if not starts:
        return [(None, cleaned)] if cleaned else []
    if starts[0] > 0:
        starts.insert(0, 0)

    sections: list[tuple[str | None, str]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(cleaned)
        section = cleaned[start:end].strip()
        if not section:
            continue
        title_match = re.match(r"(.{2,70}?)(?:。|；|;|$)", section)
        title = title_match.group(1).strip() if title_match else None
        sections.append((title, section))
    return sections


def _split_by_sentence_window(text: str, target_size: int = 520, max_size: int = 850) -> list[str]:
    if len(text) <= max_size:
        return [text]
    sentences = [part for part in re.split(r"(?<=[。；;])", text) if part]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) > target_size:
            chunks.append(current)
            current = sentence
        else:
            current += sentence
        while len(current) > max_size:
            chunks.append(current[:max_size])
            current = current[max_size - 120 :]
    if current:
        chunks.append(current)
    return chunks


def _aliases_for_text(document: RagDocument, section: str | None, content: str) -> list[str]:
    aliases: list[str] = []
    text = f"{document.title} {section or ''} {content}"
    if "报名" in text:
        aliases.extend(["报名时间", "报名条件", "报名流程", "报名材料", "网上报名"])
    if "录取" in text:
        aliases.extend(["录取时间", "录取结果", "录取查询", "录取分数线"])
    if "成绩" in text:
        aliases.extend(["成绩公布", "成绩查询", "成绩复核"])
    if "准考证" in text:
        aliases.extend(["准考证打印", "打印准考证"])
    if "征集志愿" in text:
        aliases.extend(["征集志愿", "志愿填报"])
    if document.year:
        aliases.append(f"{document.year}年成人高考")
    return sorted(set(aliases))


def _is_low_value_document(document: RagDocument) -> bool:
    title = document.title
    text = _clean_text(document.text)
    if len(text) < 180 and any(marker in title for marker in TITLE_NOISE):
        return True
    if len(text) < 220 and any(marker in text for marker in USELESS_CONTENT_MARKERS):
        return True
    return False


def _is_low_value_text(text: str) -> bool:
    stripped = _clean_text(text)
    if len(stripped) < 90:
        return True
    if any(marker in stripped for marker in USELESS_CONTENT_MARKERS) and len(stripped) < 260:
        return True
    if stripped.endswith(("通知如下：", "事项通知如下：")) and len(stripped) < 260:
        return True
    return False


def _clean_text(text: str) -> str:
    text = re.sub(r"https?://[A-Za-z0-9./_%?=&:#-]+", "", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def _clean_answer_value(value: str) -> str:
    value = _clean_text(value).strip("：:，,；;。")
    return value[:420]


def _post_process_value(rule_key: str, value: str) -> str:
    if rule_key == "registration_qualification":
        value = re.split(r"(?:二、报名时间|报名时间和方式|报名方式|附件)", value)[0]
        sentences = re.split(r"(?<=[。；;])", value)
        useful = [
            sentence
            for sentence in sentences
            if any(keyword in sentence for keyword in ("户籍", "居住证", "学历", "毕业证", "专升本", "高起本", "高起专", "港澳", "台湾", "侨民"))
        ]
        value = "".join(useful) or value
    return value[:320].strip("：:，,；;。")


def _slug(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text).strip("_")[:50] or "section"


def _deduplicate_chunks(chunks: list[RagChunk]) -> list[RagChunk]:
    seen: set[tuple[str | None, str | None, str | None]] = set()
    unique: list[RagChunk] = []
    for chunk in chunks:
        key = (chunk.year, chunk.question, chunk.answer)
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique


def _write_jsonl(path: Path, rows: list[object]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            payload = row.to_dict() if hasattr(row, "to_dict") else asdict(row)
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _write_report(
    path: Path,
    source_dir: Path,
    output_dir: Path,
    raw_count: int,
    useful_count: int,
    policy_chunks: list[RagChunk],
    faq_chunks: list[RagChunk],
) -> None:
    faq_by_year: dict[str, int] = {}
    for chunk in faq_chunks:
        faq_by_year[chunk.year or "unknown"] = faq_by_year.get(chunk.year or "unknown", 0) + 1
    report = [
        "# Curated Adult Exam RAG Knowledge Base",
        "",
        f"- Source: `{source_dir}`",
        f"- Output: `{output_dir}`",
        f"- Raw documents: {raw_count}",
        f"- Useful documents: {useful_count}",
        f"- Policy chunks: {len(policy_chunks)}",
        f"- FAQ chunks: {len(faq_chunks)}",
        f"- Merged chunks: {len(policy_chunks) + len(faq_chunks)}",
        "",
        "## FAQ Count By Year",
        "",
    ]
    for year, count in sorted(faq_by_year.items(), reverse=True):
        report.append(f"- {year}: {count}")
    path.write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a curated RAG knowledge base from adult exam txt documents.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT, type=Path)
    args = parser.parse_args()
    summary = build_curated_knowledge(args.source, args.output)
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
