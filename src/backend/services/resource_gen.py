"""
Resource generation service: Quiz, Flashcard, Slide, Summary, Podcast, Study Guide.
Mapping: Features 6.4-6.9 [11, 13, 14]
"""
import os
import json
import time
import re
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
        
    def _get_citations(self, docs):
        """Tạo danh sách trích dẫn từ Metadata của tài liệu."""
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
        text = re.sub(r"\s+", " ", text).strip()
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
        return {
            "title": title,
            "duration": "20-30 phút",
            "objectives": [
                "Nắm được ý chính và thuật ngữ trọng tâm của phần này.",
                "Giải thích lại nội dung bằng ngôn ngữ của người học.",
            ],
            "lecture": (
                f"Phần {index_label} tập trung vào nội dung từ {source_note}.\n\n"
                f"{point['text']}\n\n"
                "Khi học phần này, người học nên đọc kỹ đoạn gốc, xác định các khái niệm then chốt "
                "và liên hệ chúng với mục tiêu chung của tài liệu."
            ),
            "key_points": [
                point["text"][:180],
                f"Nội dung này được trace từ {source_note}.",
                "Cần ghi nhớ mối liên hệ giữa ý chính, ví dụ và mục tiêu bài học.",
            ],
            "activity": "Yêu cầu người học tóm tắt phần này bằng 3 gạch đầu dòng và nêu 1 ví dụ minh họa.",
            "assessment": [
                "Ý chính của phần này là gì?",
                "Chi tiết nào trong tài liệu chứng minh cho ý chính đó?",
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
            slides.append(
                {
                    "title": f"Slide {index + 1}: Trang {point['page']}",
                    "content": f"- {point['text']}\n- Nguồn: {point['source']}",
                    "layout_hint": "title-and-content",
                    "image_suggestion": "Sơ đồ hoặc minh họa đơn giản cho ý chính của slide.",
                }
            )
        return slides
        
    def generate_course_structure(self, user_prompt: str, target_audience: str):
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 10})
        docs = retriever.invoke(user_prompt or "tổng quan")
        citations = self._get_citations(docs)
        try:
            prompt = ChatPromptTemplate.from_template(COURSE_GENERATION_PROMPT)
            chain = prompt | get_llm(temperature=0.3) | StrOutputParser()
            res = chain.invoke({
                "context": format_docs(docs),
                "user_prompt": user_prompt or "Không có",
                "target_audience": target_audience or "người học chung"
            })
            course = json.loads(extract_json(res))
            return {
                "course": self._normalize_course(course, docs, target_audience),
                "citations": citations,
            }
        except Exception as e:
            logger.warning("Course generation failed, using fallback: %s", e)
            return {
                "course": self._build_fallback_course(docs, target_audience),
                "citations": citations,
            }

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

    # 4.5 Slides
    def generate_slides_v2(self, topic: str, num_slides: int):
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 15})
        docs = retriever.invoke(topic)
        citations = self._get_citations(docs)
        try:
            prompt = ChatPromptTemplate.from_template(SLIDES_V2_PROMPT)
            chain = prompt | get_llm(temperature=0.1) | StrOutputParser()
            res = chain.invoke({
                "context": format_docs(docs), "topic": topic, "num_slides": num_slides
            })
            slides = json.loads(extract_json(res))
            if not isinstance(slides, list) or not slides:
                raise ValueError("LLM did not return a non-empty slide array.")
            return {"slides": slides[:num_slides], "citations": citations}
        except Exception as e:
            logger.warning("Slides generation failed, using fallback: %s", e)
            return {
                "slides": self._build_fallback_slides(docs, num_slides),
                "citations": citations,
            }
        
    

    

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

