import os

file_path = r"src\backend\services\resource_gen.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_format_schema = """    def _format_storyboard_schema(
        self,
        scenes: list[dict[str, Any]],
        video_title: str,
        video_mode: str,
        target_user: str,
        duration_sec: int,
        docs: list[Any],
    ) -> dict[str, Any]:
        formatted_scenes = []
        all_chunk_ids = list({doc.metadata.get("chunk_id", f"chunk_{i+1}") for i, doc in enumerate(docs[:4]) if hasattr(doc, "metadata") and doc.metadata.get("chunk_id")})
        if not all_chunk_ids:
            all_chunk_ids = ["chunk_1"]

        warnings = []
        is_ready = True
        seen_voiceovers = set()

        total_dur = 0
        for idx, s in enumerate(scenes):
            if not isinstance(s, dict):
                s = {"title": str(s)}
            dur = int(s.get("duration_seconds") or (15 if video_mode == "sixty_second" else 25))
            total_dur += dur
            stype = s.get("scene_type", "concept")
            vtmpl = s.get("visual_template", "concept_card")
            raw_title = str(s.get("title", ""))
            title = self._clean_generated_text(raw_title or f"Cảnh {idx+1}")

            # Part F Quality Checks on original input
            if raw_title.strip().lower() in ("ý chính", "contents", "nội dung") or "ghi nhớ ý chính" in raw_title.lower():
                warnings.append(f"Cảnh {idx+1}: Tiêu đề '{raw_title}' không đạt chuẩn.")
                is_ready = False
            if any(marker in str(s).lower() for marker in ["contents", "...", "debug", "page "]):
                warnings.append(f"Cảnh {idx+1}: Chứa ký tự rác hoặc số trang thô.")
                is_ready = False

            cids = s.get("source_chunk_ids", [])
            if not cids or not isinstance(cids, list) or len(cids) == 0:
                warnings.append(f"Cảnh {idx+1}: Thiếu source_chunk_ids.")
                is_ready = False
                cids = [all_chunk_ids[idx % len(all_chunk_ids)]]

            if title.lower() in ("ý chính", "contents", "nội dung"):
                title = f"Chủ đề trọng tâm {idx+1}"

            stext = s.get("screen_text", [])
            if isinstance(stext, str):
                stext = [line.strip() for line in stext.split("\\n") if line.strip()]
            elif not isinstance(stext, list):
                stext = [title]

            if len(stext) > 6 or any(len(str(line)) > 150 for line in stext):
                warnings.append(f"Cảnh {idx+1}: screen_text quá dài.")
                is_ready = False

            stext = [str(line)[:140] for line in stext[:5]]
            vo = self._clean_generated_text(str(s.get("voiceover", ""))) or f"{title}: {s.get('key_message', '')}"
            
            vo_clean = vo.strip().lower()
            if vo_clean in seen_voiceovers or len(vo_clean) < 10:
                if idx > 0:
                    warnings.append(f"Cảnh {idx+1}: Lời thoại voiceover bị lặp hoặc quá ngắn.")
                    is_ready = False
            seen_voiceovers.add(vo_clean)

            # Template mismatch check
            if vtmpl == "code_walkthrough" and not any("code" in str(line).lower() or "func" in str(line).lower() for line in stext):
                vtmpl = "concept_card"

            formatted_scenes.append({
                "scene_index": idx + 1,
                "scene_type": stype,
                "title": title,
                "key_message": str(s.get("key_message") or title)[:180],
                "screen_text": stext,
                "voiceover": vo,
                "visual_template": vtmpl,
                "visual_data": s.get("visual_data") or {"title": title, "bullets": stext},
                "duration_seconds": dur,
                "source_chunk_ids": cids,
            })

        est_dur = duration_sec or total_dur
        transcript = "\\n\\n".join([f"[{fs['title']}]\\n{fs['voiceover']}" for fs in formatted_scenes])
        srt = self._generate_srt_subtitles(formatted_scenes)

        qreport = {
            "engagement_score": 88 if is_ready else 65,
            "learning_score": 90 if is_ready else 68,
            "visual_score": 85 if is_ready else 65,
            "is_ready_to_render": is_ready,
            "warnings": warnings,
        }

        return {
            "video_title": video_title or "Video bài giảng AI",
            "video_mode": video_mode,
            "estimated_duration_seconds": est_dur,
            "target_user": target_user or "student",
            "quality_report": qreport,
            "scenes": formatted_scenes,
            "transcript": transcript,
            "subtitles_srt": srt,
        }"""

# Replace _format_storyboard_schema in resource_gen.py
marker = "    def _format_storyboard_schema("
if marker in content:
    parts = content.split(marker)
    # find where next method starts after _format_storyboard_schema
    next_marker = "    def regenerate_video_scene("
    parts2 = parts[1].split(next_marker)
    content = parts[0] + new_format_schema + "\n\n" + next_marker + parts2[1]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated _format_storyboard_schema with Part F quality checks.")
