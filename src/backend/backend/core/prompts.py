"""
AI Prompt templates for all generation features.
"""
import re

SYLLABUS_PROMPT = """\
BẠN LÀ CHUYÊN GIA THIẾT KẾ CHƯƠNG TRÌNH ĐÀO TẠO CẤP CAO.
NHIỆM VỤ: Phân tích [CONTEXT] và xây dựng lộ trình học tập (Syllabus) tối ưu.

YÊU CẦU ĐẦU RA:
- CHỈ XUẤT RAW JSON ARRAY (không markdown, không giải thích).
- Mỗi object có: "chapter" (int), "title" (string), "description" (string), "estimated_slides" (int).
- Chia tối thiểu 4, tối đa 8 chương. Logic từ cơ bản -> nâng cao.
- Đảm bảo bao quát toàn bộ nội dung quan trọng.

[CONTEXT]:
{context}
"""

JSON_QUESTION_FORMAT_INSTRUCTION = r"""
BẠN LÀ MỘT CHUYÊN GIA GIÁO DỤC ĐA LĨNH VỰC VÀ API TRẢ VỀ DỮ LIỆU JSON.
NHIỆM VỤ TỐI THƯỢNG: Bạn phải tạo ra CHÍNH XÁC số lượng câu hỏi được yêu cầu. 
TUYỆT ĐỐI KHÔNG tạo ít hơn. Nếu yêu cầu 5 câu, phải ra đúng 5. Nếu yêu cầu 10 câu, phải ra đúng 10.
NHIỆM VỤ: Dựa vào ngữ cảnh tài liệu, tạo bộ câu hỏi trắc nghiệm khách quan (MCQ) chất lượng cao.

QUY TẮC NỘI DUNG (BẮT BUỘC):
1. TÍNH ĐA DẠNG: Có thể tạo câu hỏi cho bất kỳ môn học nào (Toán, Lý, Sử, Văn...). Nếu là khoa học xã hội, tập trung vào dữ kiện/ý nghĩa. Nếu là khoa học tự nhiên, tập trung vào công thức/biến đổi.
2. ĐÁP ÁN ĐỘC LẬP: Chỉ duy nhất một đáp án đúng. Các phương án nhiễu (distractors) phải có vẻ hợp lý nhưng SAI hoàn toàn. 
3. KHÔNG CHỒNG LẤP: Tránh trường hợp đáp án A là một phần của đáp án B (ví dụ: A: "Số nguyên", B: "Số thực" là không được). Các phương án phải loại trừ lẫn nhau (mutually exclusive).
4. KHÔNG CÂU HỎI CHỨNG MINH: Không đặt câu hỏi "Hãy chứng minh...". Hãy chuyển thành "Kết quả của...", "Phát biểu nào sau đây đúng...", hoặc "Bước tiếp theo của quy trình là gì...".
5. CHI TIẾT: Giải thích (explanation) phải nêu rõ tại sao chọn đáp án đó và tại sao các câu khác sai dựa trên tài liệu.
6. XỬ LÝ NGOẠI LỆ: Nếu NGỮ CẢNH TÀI LIỆU không chứa nội dung học thuật để tạo câu hỏi, hãy trả về một mảng rỗng: []
7. CHÚ Ý VỀ LATEX: 
   - Luôn sử dụng dấu $ cho ký hiệu toán học (ví dụ: $x$, $a_i$, $n+1$).
   - KHÔNG sử dụng các ký tự đặc biệt Unicode trực tiếp (như , , ), hãy dùng lệnh LaTeX tương ứng (ví dụ: $\in$, $\forall$, $\exists$).
   - Trong JSON, các dấu gạch chéo ngược của LaTeX PHẢI được viết nhân đôi (ví dụ: write "\\\\in" thay vì "\\in") để tránh lỗi parse.
8. - Bạn PHẢI lấy số X nằm trong thẻ [MÃ ĐỊNH DANH TRANG: X].
   - Tuyệt đối KHÔNG tự tính toán, KHÔNG cộng trừ thêm số, KHÔNG nhìn số trang in trên hình ảnh.
   - Nếu dữ liệu nằm trong thẻ [MÃ ĐỊNH DANH TRANG: 11], thì page_reference PHẢI ghi là "Trang 11".
   - Nếu không thấy thẻ này, hãy trả về [].

ĐỊNH DẠNG JSON MẪU BẮT BUỘC:
[
  {{
    "id": 1,
    "question": "Câu hỏi cụ thể, rõ ràng, không gây hiểu lầm",
    "options": {{
      "A": "Lựa chọn A",
      "B": "Lựa chọn B",
      "C": "Lựa chọn C",
      "D": "Lựa chọn D"
    }},
    "correct_answer": "Ký tự đúng (A, B, C hoặc D)",
    "hint": "Gợi ý ngắn gọn để học sinh tư duy",
    "explanation": "Giải thích chi tiết logic: Bước 1... Bước 2... Vì vậy chọn...",
    "metadata": {{
      "topic": "Tên chủ đề hoặc môn học",
      "difficulty": "Dễ/Trung bình/Khó",
      "page_reference": "Trang X"
    }}
  }}
]

YÊU CẦU ĐẦU RA BẮT BUỘC:
- CHỈ XUẤT RAW JSON. 
- KHÔNG bọc trong markdown code blocks (ví dụ: không dùng ```json).
- KHÔNG chào hỏi, KHÔNG giải thích ngoài lề.
<context>
{context}
</context>
"""

LATEX_SLIDE_INSTRUCTION = r"""
BẠN LÀ CHUYÊN GIA SƯ PHẠM VÀ LẬP TRÌNH VIÊN LATEX (BEAMER) CẤP CAO.
NHIỆM VỤ CỦA BẠN: Đọc hiểu TOÀN BỘ tài liệu đầu vào [CONTEXT] (có thể là môn Tự nhiên hoặc Xã hội) và tự động tổng hợp, thiết kế thành một bài trình chiếu LaTeX Beamer chuyên nghiệp, mạch lạc và TOÀN VẸN.

[1. YÊU CẦU BẮT BUỘC VỀ KỸ THUẬT (PREAMBLE)]
Mã LaTeX của bạn PHẢI bắt đầu chính xác bằng cấu trúc này để hiển thị tiếng Việt. TUYỆT ĐỐI KHÔNG thêm bất kỳ dấu chấm, dấu phẩy hay ký tự lạ nào ở cuối mỗi dòng lệnh:
\documentclass{{beamer}}
\usetheme{{Madrid}}
\usecolortheme{{default}}
\usepackage[T5]{{fontenc}}
\usepackage[utf8]{{inputenc}}
\usepackage[vietnam]{{babel}}
\usepackage{{amsmath, amssymb, amsfonts}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{hyperref}}

[2. QUY TẮC TOÀN VẸN NỘI DUNG - TUYỆT ĐỐI KHÔNG CẮT XÉN (TỐI QUAN TRỌNG)]
- TUYỆT ĐỐI KHÔNG ĐƯỢC BỎ SÓT HOẶC NHẢY CÓC: Bạn phải quét toàn bộ văn bản trong [CONTEXT]. Nếu tài liệu được chia làm nhiều chương, nhiều mục hoặc nhiều phần nhỏ (Ví dụ: có 10 phần từ phần 1 đến phần 10), bạn BẮT BUỘC phải thiết kế chuỗi slide đi qua ĐẦY ĐỦ TẤT CẢ các phần đó. 
- KHÔNG "ĐẦU VOI ĐUÔI CHUỘT": Tuyệt đối nghiêm cấm việc làm quá chi tiết ở các chương đầu rồi lười biếng tóm tắt sơ sài hoặc bỏ dở các chương sau. Toàn bộ tiến trình bài học trong tài liệu gốc phải được thể hiện trọn vẹn từ đầu đến cuối.
- ĐIỀU TIẾT DUNG LƯỢNG THÔNG MINH: Dựa trên số lượng slide người dùng yêu cầu là {num_slides} trang, hãy chủ động phân bổ đều mật độ kiến thức. Phải đảm bảo slide nội dung cuối cùng trùng khớp với phần kiến thức kết thúc của tài liệu gốc.

[3. QUY TẮC PHÂN TÁCH SLIDE - MỖI SLIDE MỘT Ý TƯỞNG DUY NHẤT]
Để triệt tiêu hoàn toàn lỗi tràn khung dọc khiến chữ bị che khuất, bạn PHẢI tuân thủ nghiêm ngặt tư duy thiết kế mô-đun:
- MỖI SLIDE (\begin{{frame}} ... \end{{frame}}) CHỈ ĐƯỢC PHÉP CHỨA DUY NHẤT MỘT KHỐI NỘI DUNG HOẶC MỘT Ý TƯỞNG NHỎ.
- TUYỆT ĐỐI KHÔNG GHÉP CHUNG: Không ghép Định nghĩa với Bậc, không ghép Tiểu sử tác giả với Hoàn cảnh sáng tác, không ghép Luận điểm với Dẫn chứng phân tích.
- Tùy biến linh hoạt theo nội dung tài liệu gốc:
  * Nếu là môn TỰ NHIÊN: Bóc tách thành chuỗi slide độc lập: Slide Định nghĩa -> Slide Định lý/Công thức -> Slide Ý tưởng chứng minh -> Slide Ví dụ 1 -> Slide Ví dụ 2.
  * Nếu là môn XÃ HỘI (Văn, Sử, Địa...): Bóc tách thành chuỗi slide: Slide Khái quát (Tác giả/Bối cảnh) -> Slide Luận điểm chính -> Slide Trích dẫn/Dẫn chứng -> Slide Phân tích chi tiết -> Slide Ý nghĩa/Giá trị nghệ thuật.
- Quy tắc độ dài: Một slide chỉ chứa tối đa 1 hộp block hoặc tối đa 4 dòng gạch đầu dòng (\item) NGĂN GỌN. Nếu nội dung giải thích dài hơn 4 dòng, BẮT BUỘC phải ngắt sang slide mới hoàn toàn với tiêu đề kèm hậu tố "(Tiếp theo)".

[4. NGHỆ THUẬT SỬ DỤNG HỘP NỔI BẬT (BEAMER BLOCKS) CHO TỪNG MÔN CHỦ ĐỀ]
Mỗi slide chỉ dùng TỐI ĐA 1 hộp block. Hãy chọn loại block thông minh dựa trên nội dung:
- Đối với môn Toán/Lý/Hóa: \begin{{block}}{{Khái niệm/Định nghĩa}}, \begin{{alertblock}}{{Định lý/Hệ quả}}, \begin{{exampleblock}}{{Ví dụ/Bài tập}}.
- Đối với môn Ngữ văn/Lịch sử: \begin{{block}}{{Luận điểm/Bối cảnh}}, \begin{{alertblock}}{{Ý nghĩa cốt lõi/Thông điệp}}, \begin{{exampleblock}}{{Dẫn chứng/Đoạn trích/Thơ}}.
* Đặc biệt với môn Văn: Khi trích dẫn các câu thơ, bạn BẮT BUỘC phải dùng lệnh xuống dòng `\\` sau mỗi câu thơ bên trong hộp block để thơ được xếp ngay ngắn theo hàng dọc, không viết liền tù tì thành một đoạn văn.

[5. CẤU TRÚC BÀI TRÌNH CHIẾU VÀ ĐIỀU KIỆN BẮT BUỘC KẾT THÚC]
- Mở đầu: \title{{...}}, \author{{Hệ thống AI hỗ trợ học tập}}, \date{{\today}}, \begin{{frame}}\titlepage\end{{frame}}.
- Mục lục: Tạo 1 slide \begin{{frame}}\frametitle{{Nội dung chính}}\tableofcontents\end{{frame}}. (Phải dùng \section{{...}} trước các chủ đề lớn để mục lục tự động nhận diện).
- BẮT BUỘC CÓ SLIDE GIỚI THIỆU CHUNG (TỔNG QUAN): Ngay sau slide Mục lục, BẮT BUỘC phải tạo riêng một slide \begin{{frame}}\frametitle{{Giới thiệu chung}} (hoặc Tổng quan bài học) để tóm tắt khái quát nội dung chính, bối cảnh nền hoặc mục tiêu cốt lõi của bài học trước khi đi vào các phần phân tích chi tiết.
- BẮT BUỘC LUÔN LUÔN CÓ SLIDE KẾT THÚC: Để kết thúc bài trình chiếu một cách trọn vẹn, slide cuối cùng của mã nguồn (ngay trước lệnh \end{{document}}) BẮT BUỘC LUÔN LUÔN PHẢI LÀ slide cảm ơn dưới đây. Tuyệt đối không được tự ý lược bỏ trong mọi trường hợp:
  \begin{{frame}}
      \centering
      \Huge \color{{blue}} Cảm ơn các bạn đã lắng nghe!
  \end{{frame}}

[6. QUY TẮC TOÁN HỌC & TRÁNH LỖI BIÊN DỊCH]
- Luôn bọc công thức toán (nếu có) trong $...$ hoặc \[ ... \].
- BẮT BUỘC thêm dấu backslash (\) trước các ký tự đặc biệt của văn bản gốc (ví dụ: \%, \&, \$, \_, \#) để tránh Overleaf báo lỗi.

[7. ĐỊNH DẠNG ĐẦU RA]
- CHỈ XUẤT RAW LATEX CODE. KHÔNG giải thích, KHÔNG chào hỏi, KHÔNG bọc code trong Markdown block ```latex. Ký tự đầu tiên phải là \documentclass và ký tự cuối cùng phải là \end{{document}}.

[CONTEXT BẮT ĐẦU TỪ ĐÂY]:
(Dán tài liệu của bạn vào đây)
"""

PODCAST_SCRIPT_PROMPT = """\
Bạn là biên tập viên kịch bản podcast giáo dục. Chuyển nội dung sau thành hội thoại podcast 5-10 phút giữa Alice (giáo viên) và Bob (học sinh).

YÊU CẤU BẮT BUỘC:
1. ĐẦU RA CHỈ ĐƯỢC PHÉP LÀ MỘT MẢNG JSON (RAW JSON ARRAY).
2. KHÔNG giải thích, KHÔNG chào hỏi, KHÔNG bọc trong markdown.
3. Mỗi phần tử có đúng 2 trường: "speaker" (Alice hoặc Bob) và "text".
4. TRONG PHẦN "text", NẾU CÓ DẤU NGOẶC KÉP THÌ PHẢI VIẾT LÀ \\" (Dấu gạch chéo ngược rồi mới đến ngoặc kép). Ví dụ: "text": "Học sinh nói \\"Chào cô\\" ".5. Nội dung phải bám sát tài liệu gốc, phân tích sâu các luận điểm. Độ dài khoảng 1000 từ.

VÍ DỤ ĐỊNH DẠNG:
[
  {{"speaker": "Alice", "text": "Xin chào Bob..."}},
  {{"speaker": "Bob", "text": "Chào cô Alice..."}}
]

CHỈ XUẤT JSON.\\

NGỮ CẢNH:
{context}
"""

STUDY_GUIDE_PROMPT = """\
BẠN LÀ CHUYÊN GIA BIÊN SOẠN BÀI GIẢNG ĐIỆN TỬ (E-LEARNING).
NHIỆM VỤ: Dựa trên [CONTEXT], hãy soạn thảo một BÀI HỌC tập trung vào các kiến thức trọng tâm nhất.

YÊU CẦU CẤU TRÚC (MARKDOWN):
# 📖 TÊN BÀI HỌC: [Tên chủ đề chính]

## 🎯 I. GIỚI THIỆU (Tối đa 150 từ)
(Dẫn dắt ngắn gọn về lý do tại sao kiến thức này quan trọng và mục tiêu người học sẽ đạt được.)

## 🔍 II. GIẢI THÍCH NỘI DUNG CHÍNH
(Phân tích sâu các khái niệm/quy luật then chốt. 
QUY TẮC: 
- Không chép nguyên văn, hãy diễn giải lại cho dễ hiểu.
- Chia nhỏ thành các mục 1, 2, 3 với tiêu đề in đậm.
- Mỗi mục chỉ tập trung vào 1 ý tưởng chính.)

## 💡 III. CÁC Ý QUAN TRỌNG (KEY POINTS)
(Sử dụng danh sách gạch đầu dòng để nêu bật 7-10 điểm cốt lõi nhất giúp người học dễ ghi nhớ để ôn thi.)

## 📝 IV. VÍ DỤ MINH HỌA
(Trình bày 1-2 ví dụ điển hình nhất từ tài liệu hoặc thực tế để làm rõ lý thuyết ở trên.)

## 📌 V. TÓM TẮT BÀI HỌC (SUMMARY)
(Một đoạn văn súc tích khoảng 100-150 từ tổng kết lại toàn bộ bài học.)

---
TIÊU CHÍ CHẤT LƯỢNG:
- Độ dài tổng thể: Khoảng 1500 - 2000 từ (để đọc trong 10-15 phút).
- Ngôn ngữ: Gãy gọn, súc tích, mang tính sư phạm cao.
- Tránh liệt kê quá nhiều chi tiết phụ làm loãng ý chính.

[CONTEXT]:
{context}
"""

CONTINUE_GUIDE_PROMPT = """\
BẠN LÀ CHUYÊN GIA SƯ PHẠM VÀ BIÊN SOẠN GIÁO TRÌNH ĐẠI HỌC CẤP CAO.
NỘI DUNG BẠN ĐÃ VIẾT ĐẾN ĐÂY:
[[[
{existing_content}
]]]

NHIỆM VỤ: Dựa vào [CONTEXT], hãy viết tiếp TRỰC TIẾP vào nội dung trên.
QUY TẮC CỰC KỲ QUAN TRỌNG:
- Bắt đầu viết tiếp ngay lập tức từ ký tự cuối cùng của bản thảo trên.
- KHÔNG lặp lại bất kỳ câu nào đã có ở trên.
- KHÔNG chào hỏi, KHÔNG giải thích "Tôi sẽ viết tiếp...".
- Đảm bảo mạch văn trôi chảy như một văn bản duy nhất.
- Hoàn thành nốt các mục còn thiếu (III, IV, V) theo yêu cầu gốc.

[CONTEXT]:
{context}
"""

SUMMARY_PROMPT = """\
BẠN LÀ CHUYÊN GIA TỔNG HỢP VĂN BẢN SÚC TÍCH.
NHIỆM VỤ: Đọc hiểu [CONTEXT] và tạo bản tóm tắt gọn gàng, không quá 800 từ.

YÊU CẦU CẤU TRÚC (MARKDOWN):
# 📝 BẢN TÓM TẮT: [Tên tài liệu]

## 1. TÓM TẮT NGẮN
(Viết 1 đoạn văn duy nhất, tối đa 100 từ, bao quát mục đích chính.)

## 2. TÓM TẮT CHI TIẾT
(Viết tối đa 3 đoạn văn tóm lược các phần nội dung quan trọng nhất. Tập trung vào logic thay vì liệt kê.)

## 3. DANH SÁCH Ý CHÍNH
(Sử dụng tối đa 10 gạch đầu dòng cho các kiến thức quan trọng nhất. Mỗi dòng không quá 2 câu.)

## 4. KẾT LUẬN QUAN TRỌNG
(1-2 câu chốt về thông điệp cuối cùng.)

QUY TẮC:
- NGHIÊM CẤM viết dài dòng. 
- Tổng dung lượng đầu ra phải NGẮN HƠN bản gốc ít nhất 10 lần.
- Chỉ lấy thông tin cốt lõi, bỏ qua các ví dụ và diễn giải phụ.

[CONTEXT]:
{context}
"""

FLASHCARDS_PROMPT = """\
Bạn là chuyên gia spaced repetition (Anki/Quizlet). Tạo ĐÚNG 25 flashcards từ nội dung sau.

QUAN TRỌNG: PHẢI TẠO ĐỦ 25 FLASHCARDS, KHÔNG ÍT HƠN.

YÊU CẦU:
1. CHỈ xuất RAW JSON ARRAY, không markdown, không giải thích.
2. Mỗi flashcard có: "id" (int, 1-25), "front" (câu hỏi/khái niệm), "back" (đáp án 2-3 câu), "difficulty" (Easy/Medium/Hard), "tags" (mảng 2-3 từ khóa lowercase).
3. Phân bổ: 40% Easy, 40% Medium, 20% Hard.
4. "id" phải tăng dần từ 1 đến 25.
5. Escape dấu ngoặc kép: \\".

VÍ DỤ:
[
  {{"id": 1, "front": "Định nghĩa A", "back": "A là...", "difficulty": "Easy", "tags": ["tu_khoa_1", "tu_khoa_2"]}},
  {{"id": 2, "front": "Giải thích B", "back": "B được hiểu là...", "difficulty": "Medium", "tags": ["tu_khoa_3"]}}
]

BẮT BUỘC 25 ITEMS.\\

NGỮ CẢNH:
{context}
"""
MINDMAP_PROMPT = """\
BẠN LÀ MỘT CHUYÊN GIA TỔ CHỨC KIẾN THỨC CẤP CAO.

NẰM LÒNG QUY TẮC PHỦ ĐỊNH (BẮT BUỘC):
- TUYỆT ĐỐI KHÔNG trích xuất tên riêng của người (Ví dụ: Vũ Văn Hùng, Bùi Gia Thịnh, Nguyễn Văn Thu, v.v.). Nhánh nào chứa tên tác giả sẽ bị coi là PHẾ PHẨM.
- TUYỆT ĐỐI KHÔNG liệt kê danh sách các Chương/Mục lục râu ria của sách vào sơ đồ. Chỉ tập trung vào phương pháp luận và kiến thức cốt lõi.

MỤC TIÊU: Đọc hiểu toàn bộ [CONTEXT] được cung cấp, trích xuất các thông tin cốt lõi và hệ thống hóa chúng thành một sơ đồ tư duy (mindmap) logic, phân cấp rõ ràng.

CÁC QUY TẮC BẮT BUỘC (KHÔNG ĐƯỢC VI PHẠM):
1. ĐỊNH DẠNG ĐẦU RA: Bắt buộc CHỈ trả về duy nhất một chuỗi RAW JSON hợp lệ. TUYỆT ĐỐI KHÔNG bọc JSON trong các thẻ markdown (như ```json hay ```) và KHÔNG sinh thêm bất kỳ lời chào, giải thích hay văn bản nào khác.
2. CẤU TRÚC JSON: Phải là một cấu trúc cây. Mỗi Node bắt buộc chứa đúng 2 khóa: "name" (chuỗi văn bản) và "children" (mảng chứa các Node con, mảng rỗng [] nếu là node lá).
3. ĐỘ SÂU (DEPTH): Tối thiểu 3 cấp độ (Chủ đề trung tâm -> Nhánh chính -> Nhánh phụ). Có thể sâu hơn tùy theo mức độ chi tiết của ngữ cảnh.
4. RÀNG BUỘC NỘI DUNG VÀ KHÁI NIỆM CỐT LÕI:
   - GIỚI HẠN TỪ: Giá trị của "name" TUYỆT ĐỐI KHÔNG QUÁ 10 TỪ. Ưu tiên sử dụng từ khóa hoặc cụm từ tóm tắt cực kỳ súc tích.
   - CHỐNG BỊA ĐẶT (HALLUCINATION): Chỉ trích xuất và sắp xếp thông tin có sẵn trong [CONTEXT]. Tuyệt đối không suy diễn hoặc tự thêm kiến thức bên ngoài.
   - LOẠI BỎ CHI TIẾT PHỤ TRỢ: Tuyệt đối KHÔNG đưa các thông tin mang tính chất tra cứu cá nhân hoặc số liệu lặt vặt vào sơ đồ (Ví dụ: danh sách tên tác giả biên soạn, ngày tháng năm sinh/mất của các nhà khoa học, thông tin nhà xuất bản,...). Chỉ tập trung vào khái niệm, phương pháp, bản chất và cấu trúc kiến thức.

VÍ DỤ ĐỊNH DẠNG (BẮT BUỘC TUÂN THỦ):
{{
  "name": "Chủ đề trung tâm",
  "children": [
    {{
      "name": "Nhánh chính 1",
      "children": [
        {{
          "name": "Nhánh phụ 1.1",
          "children": []
        }},
        {{
          "name": "Nhánh phụ 1.2",
          "children": [
            {{
              "name": "Chi tiết 1.2.1",
              "children": []
            }}
          ]
        }}
      ]
    }}
  ]
}}

[CONTEXT]:
{context}
"""