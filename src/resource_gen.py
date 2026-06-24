"""
Resource generation service: Quiz, Flashcard, Slide, Summary, Podcast, Study Guide.
Mapping: Features 6.4-6.9 [11, 13, 14]
"""
import os
import json
import time
import re
import urllib.parse
import shutil
import logging
from typing import List, Optional, Tuple, Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.core.config import (
    get_llm,
    format_docs,
    extract_json,
    sanitize_filename,
    get_course_path,
    QUESTIONS_DIR,
    AUDIO_DIR,
    GUIDES_DIR,
    FLASHCARDS_DIR,
    logger,
)
from backend.core.prompts import (
    COURSE_GENERATION_PROMPT,
    QUIZ_V2_PROMPT,
    SLIDES_V2_PROMPT,
    SUMMARY_V2_PROMPT, 
    FLASHCARDS_V2_PROMPT, 
    PODCAST_SCRIPT_PROMPT,
    STUDY_GUIDE_PROMPT,
    CONTINUE_GUIDE_PROMPT,
)

def clean_and_parse_json(raw_text: str) -> Any:
    """
    Trích xuất và làm sạch JSON bằng cách xử lý các dấu ngoặc kép nội bộ.
    """
    json_str = extract_json(raw_text)
    
    # Loại bỏ các ký tự điều khiển lạ
    json_str = "".join(ch for ch in json_str if ord(ch) >= 32 or ch in "\n\r\t")

    try:
        # Thử parse lần 1
        return json.loads(json_str, strict=False)
    except json.JSONDecodeError:
        # Nếu lỗi, dùng Regex để tìm các dấu " nằm giữa 2 ký tự chữ (dấu nháy lỗi) và thay bằng '
        # Ví dụ: "Nội dung "Vật lý" hay" -> "Nội dung 'Vật lý' hay"
        fixed_str = re.sub(r'([a-zA-Z0-9])"([a-zA-Z0-9])', r"\1'\2", json_str)
        try:
            return json.loads(fixed_str, strict=False)
        except:
            # Nếu vẫn lỗi, trả về mảng rỗng để không bị sập app
            return []


class ResourceGenerator:
    """
    Generates learning resources (Quiz, Flashcard, Slide, Summary, Podcast, Study Guide)
    from an initialized RAGChains instance.
    """

    def __init__(self, rag_chains):
        """
        Args:
            rag_chains: An initialized RAGChains instance with vectorstore.
        """
        self.rag = rag_chains
        self.course_id = rag_chains.course_id
        self.vectorstore = rag_chains.vectorstore
        
        """Tạo danh sách trích dẫn từ Metadata của tài liệu."""
    def _get_citations(self, docs):
        return [
            {
                "page": d.metadata.get("page", 1),
                "source": os.path.basename(d.metadata.get("source_file", d.metadata.get("source", "unknown"))),
                "chunk_id": d.metadata.get("chunk_id", f"chunk_{hash(d.page_content) % 1000}")
            } for d in docs[:3]
        ]

    def _clean_doc_text(self, doc, max_chars: int = 320) -> str:
        """Return compact text from a retrieved chunk for deterministic fallbacks."""
        text = doc.page_content
        text = re.sub(r"===\s*BẮT ĐẦU.*?===", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"===\s*KẾT THÚC.*?===", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"\[MÃ ĐỊNH DANH TRANG:\s*\d+\]", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bNỘI DUNG:\s*", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bMã định danh trang\s+\d+\s+nội dung\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"[^\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text or len(text) < 3:
            return ""
        return text[:max_chars].strip()

    def _doc_points(self, docs, limit: int = 8, max_chars: int = 220):
        points = []
        for doc in docs:
            text = self._clean_doc_text(doc, max_chars)
            if len(text) < 30:
                continue
            points.append(
                {
                    "text": text,
                    "page": doc.metadata.get("page", "?"),
                    "source": os.path.basename(
                        doc.metadata.get("source_file", doc.metadata.get("source", "unknown"))
                    ),
                    "chunk_id": doc.metadata.get("chunk_id", ""),
                }
            )
            if len(points) >= limit:
                break
        return points or [
            {
                "text": "Tài liệu đã được xử lý thành công, nhưng hệ thống chưa trích xuất được đoạn nội dung đủ dài cho bản nháp.",
                "page": "?",
                "source": "unknown",
                "chunk_id": "",
            }
        ]

    def _short_title(self, text: str, fallback: str) -> str:
        words = re.findall(r"\w+", text, flags=re.UNICODE)
        title = " ".join(words[:8]).strip()
        return title.capitalize() if title else fallback

    def _build_lesson_from_point(self, point, title: str, index_label: str):
        source_note = f"Trang {point['page']} - {point['source']}"
        text = point["text"]
        text_short = text[:180] if len(text) > 180 else text

        # Extract key terms from text for diverse generation (truncated to avoid excessive length)
        terms = [w.strip() for w in text.split()[:5] if len(w.strip()) > 3][:3]
        term_str = ", ".join(terms) if terms else "nội dung trọng tâm"

        return {
            "title": title,
            "duration": "20-30 phút",
            "objectives": [
                f"Nắm được khái niệm cốt lõi về {term_str} từ đoạn trích.",
                f"Phân tích được mối quan hệ giữa các ý trong phần {index_label}.",
            ],
            "lecture": (
                f"Phần {index_label} tập trung vào nội dung từ {source_note}.\n\n"
                f"{text}\n\n"
                "Khi học phần này, người học nên đọc kỹ đoạn gốc, xác định các khái niệm then chốt "
                "và liên hệ chúng với mục tiêu chung của tài liệu."
            ),
            "key_points": [
                f"Ý chính: {text_short}",
                f"Ví dụ/dẫn chứng từ nguồn: {source_note} cung cấp thông tin về {term_str}.",
                f"Liên hệ: Nội dung này có thể liên quan đến các khái niệm đã học trước đó về {term_str}.",
                f"Ứng dụng: Hãy tìm một tình huống thực tế để minh họa cho {term_str}.",
                f"Gợi mở: Nếu {term_str} thay đổi, hệ quả sẽ như thế nào theo tài liệu?",
            ],
            "activity": f"Yêu cầu người học tóm tắt phần {index_label} bằng 3 gạch đầu dòng, nêu 1 ví dụ cho {term_str}, và đặt 1 câu hỏi về nội dung chưa rõ.",
            "assessment": [
                f"Nhận biết: Thuật ngữ '{term_str}' được định nghĩa như thế nào trong tài liệu?",
                f"Thông hiểu: Hãy diễn giải lại bằng lời của bạn nội dung chính từ {source_note}.",
                f"Vận dụng: Áp dụng kiến thức về {term_str} để giải quyết tình huống: [tình huống từ nội dung tài liệu].",
            ],
            "citation": {
                "page": point["page"],
                "source": point["source"],
                "chunk_id": point["chunk_id"],
            },
        }

    def _normalize_course(self, course, docs, target_audience: str):
        points = self._doc_points(docs, limit=18, max_chars=620)
        if not isinstance(course, dict):
            return self._build_fallback_course(docs, target_audience)

        normalized = {
            "title": course.get("title") or "Khóa học từ tài liệu đã tải lên",
            "description": course.get("description")
            or f"Lộ trình học dành cho {target_audience or 'người học'}, bám sát nội dung tài liệu gốc.",
            "estimated_duration": course.get("estimated_duration") or "3-5 giờ",
            "chapters": [],
        }

        raw_chapters = course.get("chapters") or course.get("syllabus") or []
        if not isinstance(raw_chapters, list) or not raw_chapters:
            return self._build_fallback_course(docs, target_audience)

        point_cursor = 0
        for chapter_index, raw_chapter in enumerate(raw_chapters[:6], 1):
            chapter = raw_chapter if isinstance(raw_chapter, dict) else {"title": str(raw_chapter)}
            raw_lessons = chapter.get("lessons") or []
            if not isinstance(raw_lessons, list) or not raw_lessons:
                raw_lessons = [{"title": f"Bài {chapter_index}.1: Nội dung trọng tâm"}]

            lessons = []
            for lesson_index, raw_lesson in enumerate(raw_lessons[:3], 1):
                lesson = raw_lesson if isinstance(raw_lesson, dict) else {"title": str(raw_lesson)}
                point = points[point_cursor % len(points)]
                point_cursor += 1
                title = lesson.get("title") or f"Bài {chapter_index}.{lesson_index}: Nội dung trọng tâm"
                enriched = self._build_lesson_from_point(
                    point,
                    title,
                    f"{chapter_index}.{lesson_index}",
                )

                for field in ["duration", "activity"]:
                    if lesson.get(field):
                        enriched[field] = lesson[field]

                for field in ["objectives", "key_points", "assessment"]:
                    if isinstance(lesson.get(field), list) and lesson[field]:
                        enriched[field] = lesson[field]

                if isinstance(lesson.get("lecture"), str) and lesson["lecture"].strip():
                    enriched["lecture"] = lesson["lecture"].strip()

                lessons.append(enriched)

            normalized["chapters"].append(
                {
                    "title": chapter.get("title") or chapter.get("chapter") or f"Chương {chapter_index}",
                    "description": chapter.get("description")
                    or f"Chương này hệ thống hóa {len(lessons)} bài học chính từ tài liệu.",
                    "lessons": lessons,
                }
            )

        return normalized

    def _build_fallback_course(self, docs, target_audience: str):
        points = self._doc_points(docs, limit=6, max_chars=620)
        chapters = []
        for index, point in enumerate(points, 1):
            title = self._short_title(point["text"], f"Nội dung chính {index}")
            chapters.append(
                {
                    "title": f"Chương {index}: {title}",
                    "description": f"Hệ thống hóa nội dung trọng tâm từ trang {point['page']} của tài liệu.",
                    "lessons": [
                        self._build_lesson_from_point(
                            point,
                            f"Bài {index}.1: Đọc hiểu nội dung trang {point['page']}",
                            f"{index}.1",
                        ),
                        self._build_lesson_from_point(
                            point,
                            f"Bài {index}.2: Ghi nhớ và vận dụng ý chính",
                            f"{index}.2",
                        ),
                    ],
                }
            )
        return {
            "title": "Khóa học từ tài liệu đã tải lên",
            "description": f"Lộ trình học MVP dành cho {target_audience or 'người học'}, được dựng trực tiếp từ các đoạn nội dung đã index trong tài liệu.",
            "estimated_duration": "3-5 giờ",
            "chapters": chapters,
        }

    def _build_fallback_summary(self, docs, summary_type: str):
        points = self._doc_points(docs, limit=8, max_chars=260)
        bullets = "\n".join(
            f"- Trang {point['page']}: {point['text']}" for point in points
        )
        return (
            "# BẢN TÓM TẮT TÀI LIỆU\n\n"
            f"Loại tóm tắt: `{summary_type}`.\n\n"
            "Các ý chính được trích trực tiếp từ tài liệu:\n\n"
            f"{bullets}\n\n"
            "Bản này được tạo ở chế độ dự phòng để bảo đảm demo vẫn có nội dung khi LLM hoặc parser gặp lỗi."
        )

    def _build_fallback_quiz(self, docs, quantity: int, difficulty: str):
        points = self._doc_points(docs, limit=max(1, min(quantity, 10)), max_chars=220)
        questions = []
        for index in range(max(1, min(quantity, 10))):
            point = points[index % len(points)]
            questions.append(
                {
                    "question": f"Ý nào sau đây phản ánh đúng nội dung ở trang {point['page']}?",
                    "options": [
                        point["text"][:140],
                        "Một nhận định không được tài liệu cung cấp rõ ràng.",
                        "Một kết luận mở rộng ngoài phạm vi tài liệu.",
                        "Một phương án dùng để gây nhiễu trong câu hỏi.",
                    ],
                    "correct": 0,
                    "explanation": f"Đáp án đúng lấy trực tiếp từ chunk metadata page={point['page']}, source={point['source']}.",
                    "difficulty": difficulty,
                }
            )
        return questions

    def _build_fallback_slides(self, docs, num_slides: int):
        points = self._doc_points(docs, limit=max(1, min(num_slides, 10)), max_chars=220)
        slides = []
        for index in range(max(1, min(num_slides, 10))):
            point = points[index % len(points)]
            title = f"Trang {point['page']}: {self._short_title(point['text'], 'Nội dung trọng tâm')}"
            slides.append(
                {
                    "title": title,
                    "content": point["text"],
                    "layout_hint": "title-and-content",
                    "image_suggestion": "Nội dung được trích xuất trực tiếp từ tài liệu gốc.",
                    "citation": {
                        "page": point["page"],
                        "source": point["source"],
                        "chunk_id": point["chunk_id"],
                    },
                }
            )
        return slides
        
    def generate_syllabus_only(self, target_audience: str = "sinh viên"):
        """Tạo khung chương trình học thuật ổn định, không bị lỗi JSON dài."""
        # Lấy dữ liệu tổng quan (k=15 là đủ cho syllabus)
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 15})
        docs = retriever.invoke("mục lục nội dung kiến thức chính bài giảng")
        citations = self._get_citations(docs)
        
        from backend.core.prompts import SYLLABUS_ONLY_PROMPT
        
        try:
            prompt = ChatPromptTemplate.from_template(SYLLABUS_ONLY_PROMPT)
            # Syllabus không cần quá dài, 2000 tokens là cực kỳ an toàn
            chain = prompt | get_llm(temperature=0, max_output_tokens=2000) | StrOutputParser()
            
            res = chain.invoke({
                "context": format_docs(docs),
                "target_audience": target_audience
            })
            
            # Sử dụng hàm parse siêu mạnh bạn đã viết
            syllabus_data = clean_and_parse_json(res)
            
            # Lưu kết quả vào file để Frontend truy xuất
            save_path = os.path.join(get_course_path(self.course_id)["guides"], "syllabus_outline.json")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(syllabus_data, f, indent=2, ensure_ascii=False)
                
            return {"syllabus": syllabus_data, "citations": citations}
            
        except Exception as e:
            logger.error(f"Syllabus generation failed: {e}")
            # Bản dự phòng tối giản nếu AI vẫn viết sai
            return {
                "syllabus": {
                    "course_title": "Khóa học từ tài liệu",
                    "chapters": [{"chapter_title": "Chương 1: Tổng quan", "lessons": [{"lesson_title": "Bài 1: Giới thiệu"}]}]
                },
                "error": str(e)
            }
    
    
    def generate_course_structure(self, user_prompt: str, target_audience: str):
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 10})
        docs = retriever.invoke(user_prompt or "tổng quan")
        citations = self._get_citations(docs)
        try:
            prompt = ChatPromptTemplate.from_template(COURSE_GENERATION_PROMPT)
            chain = prompt | get_llm(temperature=0, max_output_tokens=6000) | StrOutputParser()
            res = chain.invoke({
                "context": format_docs(docs),
                "user_prompt": user_prompt or "Không có",
                "target_audience": target_audience or "người học chung"
            })
            course = clean_and_parse_json(res)
            result = {
                "course": self._normalize_course(course, docs, target_audience),
                "citations": citations,
            }
            # Save to course JSON file for GET endpoint
            course_path = get_course_path(self.course_id)["course"]
            with open(course_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            return result
        except Exception as e:
            logger.warning("Course generation failed, using fallback: %s", e)
            result = {
                "course": self._build_fallback_course(docs, target_audience),
                "citations": citations,
            }
            # Save fallback too so GET can retrieve
            course_path = get_course_path(self.course_id)["course"]
            with open(course_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            return result

    # 4.2 Summary
    def generate_summary_v2(self, summary_type: str = "detailed"):
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 15})
        docs = retriever.invoke("nội dung trọng tâm")
        citations = self._get_citations(docs)
        try:
            prompt = ChatPromptTemplate.from_template(SUMMARY_V2_PROMPT)
            chain = prompt | get_llm(temperature=0.2) | StrOutputParser()
            res = chain.invoke({
                "context": format_docs(docs),
                "type": summary_type
            })
            if not res or not res.strip():
                raise ValueError("LLM returned an empty summary.")
            return {"summary": res, "citations": citations}
        except Exception as e:
            logger.warning("Summary generation failed, using fallback: %s", e)
            return {
                "summary": self._build_fallback_summary(docs, summary_type),
                "citations": citations,
            }

    # 4.3 Flashcards
    def generate_flashcards_v2(self, count: int):
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 15})
        docs = retriever.invoke("khái niệm định nghĩa")
        citations = self._get_citations(docs)

        try:
            prompt = ChatPromptTemplate.from_template(FLASHCARDS_V2_PROMPT)
            chain = prompt | get_llm(temperature=0.3) | StrOutputParser()
            res = chain.invoke({"context": format_docs(docs), "count": count})
            flashcards = json.loads(extract_json(res))
            if not isinstance(flashcards, list) or not flashcards:
                raise ValueError("LLM did not return a non-empty flashcard array.")
            return {"flashcards": flashcards[:count], "citations": citations}
        except Exception as e:
            logger.warning("Flashcard LLM generation failed, using fallback: %s", e)
            return {
                "flashcards": self._build_fallback_flashcards(docs, count),
                "citations": citations,
            }

    def _build_fallback_flashcards(self, docs, count: int):
        """Build simple citation-backed flashcards when LLM output is unavailable."""
        cards = []
        for doc in docs:
            text = self._clean_doc_text(doc, 280)
            if not text:
                continue
            answer = text
            if len(answer) < 40:
                continue
            page = doc.metadata.get("page", "?")
            source = os.path.basename(
                doc.metadata.get("source_file", doc.metadata.get("source", "unknown"))
            )
            cards.append(
                {
                    "question": f"Ý chính cần ghi nhớ ở trang {page} là gì?",
                    "answer": answer,
                    "citation": {
                        "page": page,
                        "source": source,
                        "chunk_id": doc.metadata.get("chunk_id", ""),
                    },
                }
            )
            if len(cards) >= count:
                break

        if cards:
            return cards
        return [
            {
                "question": "Tài liệu này cần được ôn tập như thế nào?",
                "answer": "Hãy xem lại các phần chính trong tài liệu và tạo câu hỏi theo từng khái niệm quan trọng.",
                "citation": {"page": "?", "source": "unknown", "chunk_id": ""},
            }
        ]

    # 4.4 Quiz
    def generate_quiz_v2(self, topic: str, quantity: int, difficulty: str):
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 15})
        docs = retriever.invoke(topic)
        citations = self._get_citations(docs)
        try:
            prompt = ChatPromptTemplate.from_template(QUIZ_V2_PROMPT)
            chain = prompt | get_llm(temperature=0.3) | StrOutputParser()
            res = chain.invoke({
                "context": format_docs(docs), "topic": topic,
                "quantity": quantity, "difficulty": difficulty
            })
            questions = json.loads(extract_json(res))
            if not isinstance(questions, list) or not questions:
                raise ValueError("LLM did not return a non-empty quiz array.")
            return {"questions": questions[:quantity], "citations": citations}
        except Exception as e:
            logger.warning("Quiz generation failed, using fallback: %s", e)
            return {
                "questions": self._build_fallback_quiz(docs, quantity, difficulty),
                "citations": citations,
            }

    

    def _image_suggestion_to_keyword(self, suggestion: str) -> str:
        """
        Convert a Vietnamese image suggestion to an English Unsplash/Picsum keyword.
        Uses a simple keyword mapping for common educational/academic topics.
        Falls back to generic 'education learning' if no match found.
        """
        suggestion_lower = suggestion.lower()

        keyword_map = [
            # Sciences
            (["vật lí", "vật lý", "physics", "thí nghiệm", "experiment"], "physics laboratory experiment"),
            (["hóa học", "chemistry", "phân tử", "molecule"], "chemistry science"),
            (["sinh học", "biology", "tế bào", "cell", "sinh vật"], "biology nature"),
            (["toán", "math", "số học", "algebra", "geometry"], "mathematics chalkboard"),
            (["thiên văn", "vũ trụ", "astronomy", "space", "universe"], "astronomy space stars"),
            # Social/History
            (["lịch sử", "history", "chiến tranh", "war"], "history museum"),
            (["địa lý", "geography", "bản đồ", "map"], "world map geography"),
            (["kinh tế", "economy", "tài chính", "finance"], "business finance"),
            (["xã hội", "society", "con người", "people"], "people community"),
            # Technology
            (["công nghệ", "technology", "máy tính", "computer", "lập trình", "code"], "technology computer"),
            (["robot", "ai", "trí tuệ nhân tạo", "artificial intelligence"], "artificial intelligence robot"),
            (["điện", "electric", "mạch điện", "circuit"], "electronics circuit"),
            # Education generic
            (["học sinh", "student", "trường", "school", "lớp", "classroom"], "students classroom learning"),
            (["giáo viên", "teacher", "giảng dạy", "teaching"], "teacher classroom"),
            (["sách", "book", "đọc sách", "reading", "thư viện", "library"], "books library reading"),
            (["khóa học", "course", "bài học", "lesson"], "education study"),
            # Nature/Environment
            (["thiên nhiên", "nature", "môi trường", "environment"], "nature environment"),
            (["năng lượng", "energy", "mặt trời", "solar", "gió", "wind"], "renewable energy solar"),
            # Art/Literature
            (["văn học", "literature", "thơ", "poetry", "truyện"], "literature books"),
            (["nghệ thuật", "art", "hội họa", "painting"], "art museum painting"),
        ]

        for keywords, result in keyword_map:
            if any(kw in suggestion_lower for kw in keywords):
                return result

        return "education learning knowledge"


    def _get_slide_image_url(self, image_suggestion: str, slide_index: int) -> str:
        """
        Sử dụng model FLUX để tạo ảnh phong cách Microsoft Designer/Fluent Design.
        """
        # 1. Làm sạch từ khóa
        clean_keyword = re.sub(r'[^\w\s]', '', image_suggestion).strip()
        if len(clean_keyword) > 40: clean_keyword = clean_keyword[:40]
        
        # 2. PROMPT SIÊU CẤP (Phong cách Microsoft Designer/Glassmorphism)
        # Style: 3D, Soft Lighting, Pastel Colors, Microsoft Fluent Design
        style_prompt = (
            f"Hyper-realistic 3D isometric educational icon of {clean_keyword}, "
            f"Microsoft Designer style, Fluent Design, soft claymorphism, "
            f"pastel color palette, studio lighting, white background, high detail, 8k"
        )
        
        # 3. Mã hóa URL
        encoded_prompt = urllib.parse.quote(style_prompt)
        
        # 4. Sử dụng Model FLUX (Model xịn nhất của Pollinations)
        # model=flux giúp ảnh trông cực kỳ nghệ thuật và chuyên nghiệp
        return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&model=flux&seed={slide_index + 123}"

    def generate_slides_v2(self, topic: str, num_slides: int):
        guides_dir = get_course_path(self.course_id)["guides"]
        os.makedirs(guides_dir, exist_ok=True)
        save_path = os.path.join(guides_dir, "slides_data.json")

        # Tăng k=30 để RAG lấy được nhiều nội dung sâu bên trong sách hơn
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 30})
        docs = retriever.invoke(topic if topic else "nội dung kiến thức chính bài học")
        
        # --- BỘ LỌC TRANG RÁC (Bỏ qua tác giả, lời nói đầu) ---
        cleaned_docs = []
        garbage = ["tổng chủ biên", "chủ biên", "nhà xuất bản", "ban biên tập", "lời nói đầu", "mục lục", "vũ văn hùng", "nguyên văn thu"]
        for d in docs:
            text = d.page_content.lower()
            # Bỏ qua nếu chứa từ khóa rác và nằm ở các trang đầu
            if any(kw in text for kw in garbage) and d.metadata.get("page", 0) <= 6:
                continue
            cleaned_docs.append(d)

        # Nếu lọc xong vẫn còn rác, ưu tiên lấy các docs ở trang sau (page > 5)
        final_docs = cleaned_docs if len(cleaned_docs) > 2 else docs[5:]
        citations = self._get_citations(final_docs)

        try:
            # Ép AI làm đúng format và in đậm
            prompt = ChatPromptTemplate.from_template(SLIDES_V2_PROMPT)
            chain = prompt | get_llm(temperature=0) | StrOutputParser()
            res = chain.invoke({
                "context": format_docs(final_docs), 
                "topic": topic if topic else "kiến thức Vật Lý", 
                "num_slides": num_slides
            })
            
            from backend.core.config import clean_and_parse_json
            slides = clean_and_parse_json(res)
            
            if not isinstance(slides, list) or len(slides) == 0:
                raise ValueError("AI returned invalid slide format")

            result = {"slides": slides[:num_slides], "citations": citations}
            
            # Lưu file JSON
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            return result

        except Exception as e:
            logger.error(f"AI Slide Error: {e}")
            # Bản dự phòng thông minh (Không lấy trang 1)
            fallback_slides = []
            for i in range(min(num_slides, len(final_docs))):
                d = final_docs[i]
                fallback_slides.append({
                    "title": f"Kiến thức trọng tâm {i+1}",
                    "content": d.page_content[:250] + "...",
                    "image_suggestion": "physics education"
                })
            return {"slides": fallback_slides, "citations": citations}

    def generate_slides_html(self, topic: str = "", num_slides: int = 10) -> str:
        guides_dir = get_course_path(self.course_id)["guides"]
        save_path = os.path.join(guides_dir, "slides_data.json")
        
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                generated = json.load(f)
        else:
            generated = self.generate_slides_v2(topic=topic, num_slides=num_slides)
        
        slides = generated.get("slides", [])

        def md_to_html(text):
            if not text: return ""
            # 1. Thay thế các cặp ** thành thẻ <strong>
            text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
            # 2. Xóa bỏ các dấu ** bị thừa ở cuối câu hoặc lẻ loi
            text = text.replace("**", "")
            return text

        sections = []
        for idx, item in enumerate(slides):
            title = md_to_html(item.get("title", ""))
            content = item.get("content", "")
            # Tách dòng và làm sạch
            lines = [md_to_html(l.strip("- *")) for l in content.split("\n") if l.strip()]
            bullets_html = "".join([f"<li>{l}</li>" for l in lines[:5]])
            
            img_url = self._get_slide_image_url(item.get("image_suggestion", ""), idx)

            sections.append(f"""
            <section>
                <div class="slide-container">
                    <div class="content-side">
                        <div class="eyebrow">AI COURSE GENERATOR</div>
                        <h2 class="slide-title">{title}</h2>
                        <ul class="bullet-list">{bullets_html}</ul>
                    </div>
                    <div class="image-side">
                        <div class="img-wrapper">
                            <img src="{img_url}" alt="Slide Illustration" 
                                onerror="this.src='https://loremflickr.com/800/800/physics,science'">
                        </div>
                    </div>
                </div>
            </section>
            """)

        # --- CSS FULL MÀN HÌNH (NOTEBOOK LM STYLE) ---
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/reveal.css">
            <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap">
            <style>
                :root {{ --accent: #4F46E5; --text: #111827; }}
                html, body, .reveal {{ background: #F3F4F6; width: 100vw; height: 100vh; margin: 0; }}
                .slide-container {{ 
                    display: flex !important; width: 100vw; height: 100vh; 
                    background: white; align-items: stretch; margin: 0; 
                }}
                .content-side {{ flex: 1.2; padding: 80px; display: flex; flex-direction: column; justify-content: center; text-align: left; }}
                .image-side {{ flex: 1; background: #F9FAFB; display: flex; align-items: center; justify-content: center; padding: 40px; }}
                .img-wrapper {{ width: 100%; height: 80%; filter: drop-shadow(0 20px 40px rgba(0,0,0,0.1)); display: flex; justify-content: center; }}
                .img-wrapper img {{ max-width: 90%; max-height: 90%; object-fit: contain; border-radius: 24px; }}
                .eyebrow {{ font-size: 14px; font-weight: 800; color: var(--accent); letter-spacing: 3px; margin-bottom: 20px; font-family: 'Inter'; }}
                .slide-title {{ font-family: 'Inter'; font-size: 50px !important; font-weight: 800 !important; color: var(--text) !important; line-height: 1.1 !important; margin-bottom: 40px !important; text-transform: none !important; }}
                .bullet-list {{ list-style: none !important; margin: 0 !important; padding: 0 !important; }}
                .bullet-list li {{ font-family: 'Inter'; font-size: 26px; color: #4B5563; margin-bottom: 20px; position: relative; padding-left: 45px; line-height: 1.4; }}
                .bullet-list li::before {{ content: "•"; position: absolute; left: 0; color: var(--accent); font-size: 40px; line-height: 1; }}
                strong {{ color: var(--text); font-weight: 800; }}
            </style>
        </head>
        <body>
            <div class="reveal"><div class="slides">{"".join(sections)}</div></div>
            <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/reveal.js"></script>
            <script>
                Reveal.initialize({{ width: '100%', height: '100%', margin: 0, center: false, transition: 'slide', hash: true }});
            </script>
        </body>
        </html>
        """
        
    

    

    # ═══════════════════════════════════════════════════════════════════════════
    # PODCAST — Feature 6.7 [14]
    # ═══════════════════════════════════════════════════════════════════════════
    
    

    def generate_podcast_script(self) -> dict:
        """Generate podcast dialogue script with citations."""
        self.rag._require_ready()
        try:
            logger.info(" -> Đang tạo kịch bản podcast (LLM)...")
            raw = self.rag.audio_chain.invoke({})
            clean = extract_json(raw)
            data = json.loads(clean, strict=False)

            script = []
            if isinstance(data, list):
                script = data
            elif isinstance(data, dict):
                for key in ["podcast", "script", "segments", "dialogue"]:
                    if key in data and isinstance(data[key], list):
                        script = data[key]
                        break
                if not script:
                    for val in data.values():
                        if isinstance(val, list):
                            script = val
                            break

            if not script:
                raise ValueError("Không tìm thấy mảng hội thoại trong JSON trả về.")

            audio_dir = get_course_path(self.course_id)["audio"]
            os.makedirs(audio_dir, exist_ok=True)
            script_path = os.path.join(audio_dir, "podcast_script.json")

            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(script, f, indent=2, ensure_ascii=False)

            # Retrieve relevant docs for citations
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
            docs = retriever.invoke("nội dung podcast tổng quan")
            citations = self._get_citations(docs)

            return {"script": script, "citations": citations}
        except Exception as e:
            logger.error(f"[PodcastScript] LỖI: {e}")
            raise

    def generate_podcast_audio(self) -> str:
        """Chuyển kịch bản thành MP3 - Bản sửa lỗi lọc ký tự đặc biệt và xử lý file rỗng."""
        import edge_tts
        import asyncio
        import shutil
        import threading
        import re
        from pydub import AudioSegment

        # Ép đường dẫn FFmpeg cho Mac
        possible_ffmpeg = ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "ffmpeg"]
        for path in possible_ffmpeg:
            if shutil.which(path):
                AudioSegment.converter = path
                break

        def clean_text_for_tts(text: str) -> str:
            """Loại bỏ các ký tự LaTeX và ký tự đặc biệt gây lỗi TTS."""
            # Xóa các ký hiệu toán học $...$
            text = re.sub(r'\$.*?\$', '', text)
            # Xóa các ký tự backslash và lệnh LaTeX
            text = text.replace('\\', ' ')
            # Chỉ giữ lại chữ cái, số, dấu câu tiếng Việt cơ bản
            text = re.sub(r'[^\w\s,.\?!\-áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵĐđ]', ' ', text)
            # Xóa khoảng trắng thừa
            return re.sub(r'\s+', ' ', text).strip()

        self.rag._require_ready()
        try:
            audio_dir = get_course_path(self.course_id)["audio"]
            script_path = os.path.join(audio_dir, "podcast_script.json")
            final_audio_path = os.path.join(audio_dir, "podcast_full.mp3")

            with open(script_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # --- 1. CHUẨN HÓA & LÀM SẠCH VĂN BẢN ---
            script = []
            items = raw_data if isinstance(raw_data, list) else []
            if isinstance(raw_data, dict):
                for val in raw_data.values():
                    if isinstance(val, list): items = val; break
            
            for item in items:
                if isinstance(item, dict):
                    raw_text = str(item.get("text", ""))
                    cleaned_text = clean_text_for_tts(raw_text)
                    if len(cleaned_text) > 1:
                        script.append({
                            "speaker": str(item.get("speaker", "Alice")),
                            "text": cleaned_text
                        })

            temp_dir = os.path.join(audio_dir, "temp_chunks")
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)

            # --- 2. HÀM CHẠY TTS (Có bắt lỗi từng dòng) ---
            async def tts_worker():
                voices = {"Alice": "vi-VN-HoaiMyNeural", "Bob": "vi-VN-NamMinhNeural"}
                for i, line in enumerate(script):
                    voice = voices.get(line["speaker"], voices["Alice"])
                    chunk_path = os.path.join(temp_dir, f"line_{i:03d}.mp3")
                    try:
                        comm = edge_tts.Communicate(line["text"], voice)
                        await comm.save(chunk_path)
                    except Exception as e:
                        logger.error(f" -> Bỏ qua dòng {i+1} do lỗi TTS: {e}")
                        # Không tạo file rỗng, để tí nữa logic merge sẽ tự bỏ qua

            def start_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(tts_worker())
                new_loop.close()

            logger.info(" -> Đang chuyển văn bản thành giọng nói...")
            thread = threading.Thread(target=start_loop)
            thread.start()
            thread.join()

            # --- 3. GỘP FILE (Thông minh: Bỏ qua file lỗi/rỗng) ---
            logger.info(" -> Đang ráp nối các đoạn âm thanh hợp lệ...")
            combined = AudioSegment.empty()
            chunks = sorted([f for f in os.listdir(temp_dir) if f.endswith(".mp3")])
            
            valid_count = 0
            for chunk_file in chunks:
                path = os.path.join(temp_dir, chunk_file)
                # Kiểm tra file có nội dung (không phải 0 byte)
                if os.path.getsize(path) > 100: 
                    try:
                        segment = AudioSegment.from_mp3(path)
                        combined += segment
                        combined += AudioSegment.silent(duration=600)
                        valid_count += 1
                    except Exception:
                        logger.warning(f" -> File {chunk_file} bị lỗi decode, bỏ qua.")

            if valid_count == 0:
                raise RuntimeError("Không có đoạn âm thanh nào hợp lệ để tạo Podcast.")

            combined.export(final_audio_path, format="mp3")
            shutil.rmtree(temp_dir)
            logger.info(f"✅ Podcast thành công với {valid_count} đoạn hội thoại!")
            return final_audio_path

        except Exception as e:
            logger.error(f"[PodcastAudio] LỖI: {str(e)}")
            raise RuntimeError(f"Lỗi hệ thống âm thanh: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # STUDY GUIDE — Feature 6.8 [14]
    # ═══════════════════════════════════════════════════════════════════════════

    def generate_study_guide(self) -> dict:
        """Generate structured study guide with auto-continue logic and citations."""
        self.rag._require_ready()

        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 15})
        docs = retriever.invoke("nội dung chi tiết hệ thống hóa kiến thức")
        full_context = "\n\n".join([doc.page_content for doc in docs])

        logger.info(" -> Đang tạo phần 1 của Study Guide...")
        guide_content = self.rag.guide_chain.invoke({"topic": "nội dung chi tiết"}).strip()

        max_parts = 2
        for i in range(max_parts):
            if any(marker in guide_content for marker in ["V. CÂU HỎI", "📌 V.", "TÓM TẮT BÀI HỌC"]):
                break

            logger.info(f" -> Phát hiện nội dung bị cắt cụt, đang viết tiếp phần {i+2}...")

            continue_llm = get_llm(temperature=0.2)
            continue_prompt = ChatPromptTemplate.from_messages([
                ("system", CONTINUE_GUIDE_PROMPT),
                ("human", "Hãy viết tiếp bản thảo."),
            ])
            continue_chain = continue_prompt | continue_llm | StrOutputParser()

            last_context = guide_content[-1000:]
            additional_content = continue_chain.invoke({
                "context": full_context,
                "existing_content": last_context
            }).strip()

            if guide_content[-1] in [".", "!", "?", "}", "]", "\n"]:
                guide_content += "\n\n" + additional_content
            else:
                guide_content += " " + additional_content

            time.sleep(2)

        guide_content = guide_content.replace("---", "").replace("---", "")

        guides_dir = get_course_path(self.course_id)["guides"]
        os.makedirs(guides_dir, exist_ok=True)
        guide_path = os.path.join(guides_dir, "study_guide.md")

        with open(guide_path, "w", encoding="utf-8") as f:
            f.write(guide_content)

        citations = self._get_citations(docs)
        return {"guide": guide_content, "citations": citations}

    # ═══════════════════════════════════════════════════════════════════════════
    # FLASHCARDS — Feature 6.9 [14]
    # ═══════════════════════════════════════════════════════════════════════════