# **Tài Liệu Yêu Cầu Sản Phẩm**

## **1\. Thông tin chung**

### **1.1 Tên sản phẩm**

**AI Course Generator**

### **1.2 Mô tả ngắn**

AI Course Generator là một nền tảng web cho phép người dùng upload tài liệu học tập như PDF, DOCX hoặc TXT, sau đó sử dụng AI để phân tích nội dung và tự động tạo ra các tài nguyên học tập như khóa học, bài học, bản tóm tắt, flashcard, quiz, slide và bản đồ tư duy.

Sản phẩm hướng tới việc giúp học sinh, giáo viên, người tự học và các trung tâm đào tạo tiết kiệm thời gian trong quá trình đọc hiểu, tóm tắt, ghi nhớ và xây dựng nội dung học tập từ tài liệu dài.

---

## **2\. Tổng quan sản phẩm**

### **2.1 Mục tiêu tổng quan**

Sản phẩm hướng tới việc xây dựng một trang web có thể nhận tài liệu do người dùng cung cấp, phân tích nội dung tài liệu bằng AI, sau đó tạo ra các nội dung học tập có cấu trúc.

Hệ thống cần có khả năng tạo ra:

* Khóa học  
* Danh sách chương  
* Danh sách bài học  
* Tóm tắt nội dung tài liệu  
* Flashcard  
* Quiz  
* Slide thuyết trình  
* Bản đồ tư duy  
* Nội dung phản hồi theo prompt riêng của người dùng

### **2.2 Giá trị sản phẩm**

Sản phẩm giúp người dùng biến một tài liệu dài và khó xử lý thành những nội dung học tập dễ hiểu, dễ nhớ và dễ sử dụng.

Thay vì phải mất nhiều giờ để đọc, tóm tắt, tạo bài học, tạo slide và tạo câu hỏi ôn tập, người dùng có thể sử dụng AI để tự động tạo ra các tài nguyên học tập chỉ trong thời gian ngắn.

---

## **3\. Vấn đề cần giải quyết**

Người dùng thường gặp khó khăn khi phải xử lý các tài liệu dài. Việc đọc hiểu, tóm tắt, ghi nhớ, tạo slide và tạo câu hỏi kiểm tra thường mất rất nhiều thời gian.

Các vấn đề chính bao gồm:

* Tốn nhiều thời gian để đọc và hiểu tài liệu dài  
* Khó tìm ra các ý chính quan trọng  
* Mất công tóm tắt nội dung thủ công  
* Mất thời gian tạo slide để thuyết trình hoặc giảng dạy  
* Khó tạo flashcard để ghi nhớ kiến thức  
* Khó tạo quiz để kiểm tra lại nội dung đã học  
* Khó biến tài liệu thô thành một khóa học có cấu trúc rõ ràng

Sản phẩm giải quyết các vấn đề trên bằng cách sử dụng AI để tự động phân tích tài liệu và tạo ra các nội dung học tập như khóa học, bài học, tóm tắt, flashcard, quiz, slide và bản đồ tư duy.

---

## **4\. Đối tượng người dùng**

Sản phẩm hướng tới các nhóm người dùng sau:

* Học sinh  
* Giáo viên  
* Người tự học  
* Trung tâm đào tạo  
* Người cần xử lý tài liệu học tập dài  
* Người cần tạo nhanh nội dung thuyết trình hoặc giảng dạy

---

## **5\. Mục tiêu sản phẩm**

Các mục tiêu chính của sản phẩm bao gồm:

* Giúp người dùng tạo khóa học nhanh hơn  
* Biến tài liệu dài thành các bài học có cấu trúc  
* Tự động tạo tóm tắt nội dung  
* Tự động tạo flashcard để hỗ trợ ghi nhớ  
* Tự động tạo quiz để kiểm tra kiến thức  
* Tự động tạo nội dung slide để thuyết trình  
* Tự động tạo bản đồ tư duy để hệ thống hóa kiến thức  
* Cho phép người dùng nhập prompt riêng để yêu cầu AI xử lý tài liệu theo nhu cầu  
* Xây dựng giao diện web dễ dùng, dễ demo và phù hợp với người học

---

## **6\. Tính năng chính**

## **6.1 Upload tài liệu**

### **Mô tả**

Người dùng có thể upload tài liệu học tập lên hệ thống để AI phân tích và xử lý.

### **Định dạng file hỗ trợ**

* PDF  
* DOCX  
* TXT

### **Hành vi mong muốn**

* Người dùng chọn file từ máy tính  
* Hệ thống nhận file  
* Hệ thống kiểm tra định dạng file  
* Hệ thống từ chối file không hợp lệ  
* Hệ thống trích xuất nội dung text từ tài liệu  
* Hệ thống chuẩn bị nội dung để AI xử lý

### **Kết quả mong muốn**

* File được upload thành công  
* Nội dung tài liệu được trích xuất thành dạng text  
* Nội dung sau khi trích xuất có thể được dùng để tạo khóa học, tóm tắt, flashcard, quiz, slide và mind map

### **Tiêu chí hoàn thành**

* Người dùng upload được file PDF, DOCX hoặc TXT  
* Hệ thống báo lỗi khi người dùng upload file sai định dạng  
* Hệ thống không bị crash khi file rỗng, lỗi hoặc không đọc được  
* Backend trả về phản hồi rõ ràng cho frontend  
* Frontend hiển thị trạng thái upload thành công hoặc thất bại

---

## **6.2 Tạo khóa học**

### **Mô tả**

Hệ thống sử dụng nội dung tài liệu và prompt của người dùng để tạo ra một khóa học có cấu trúc.

### **Dữ liệu đầu vào**

* Nội dung tài liệu đã được trích xuất  
* Prompt hoặc yêu cầu của người dùng  
* Đối tượng học nếu người dùng nhập  
* Độ dài hoặc mức độ chi tiết mong muốn nếu có

### **Kết quả mong muốn**

Hệ thống tạo ra một khóa học gồm:

* Tên khóa học  
* Mô tả khóa học  
* Danh sách chương  
* Danh sách bài học  
* Tổng quan nội dung khóa học

### **Tiêu chí hoàn thành**

* Khóa học có tên rõ ràng  
* Khóa học có mô tả ngắn gọn  
* Khóa học có danh sách chương  
* Mỗi chương có danh sách bài học  
* Nội dung khóa học liên quan đến tài liệu người dùng upload  
* Kết quả không bị rỗng hoặc quá chung chung

---

## **6.3 Tạo bài học**

### **Mô tả**

Hệ thống tạo nội dung bài học dựa trên outline của khóa học và nội dung tài liệu gốc.

### **Kết quả mong muốn**

Mỗi bài học cần có:

* Tên bài học  
* Phần giới thiệu  
* Phần giải thích nội dung chính  
* Các ý quan trọng  
* Ví dụ minh họa nếu cần  
* Tóm tắt ngắn cuối bài

### **Tiêu chí hoàn thành**

* Mỗi bài học có tiêu đề rõ ràng  
* Nội dung bài học bám sát tài liệu  
* Bài học có cấu trúc dễ đọc  
* Có phần key points để người học dễ ghi nhớ  
* Có phần tóm tắt ngắn sau mỗi bài  
* Nội dung không bị rỗng, không quá ngắn và không lạc đề

---

## **6.4 Tạo bản tóm tắt**

### **Mô tả**

Hệ thống tạo bản tóm tắt từ tài liệu người dùng upload.

### **Kết quả mong muốn**

Hệ thống có thể tạo ra:

* Tóm tắt ngắn  
* Tóm tắt chi tiết  
* Danh sách ý chính  
* Kết luận quan trọng từ tài liệu

### **Tiêu chí hoàn thành**

* Bản tóm tắt phải bám sát tài liệu gốc  
* Bản tóm tắt dễ hiểu  
* Không bỏ qua các ý quan trọng  
* Không thêm thông tin không có trong tài liệu nếu không cần thiết  
* Người dùng có thể dùng bản tóm tắt để nắm nhanh nội dung tài liệu

---

## **6.5 Tạo flashcard**

### **Mô tả**

Hệ thống tạo flashcard dựa trên các ý chính, khái niệm quan trọng và nội dung bài học.

### **Kết quả mong muốn**

Mỗi flashcard gồm:

* Mặt trước: câu hỏi, khái niệm hoặc từ khóa  
* Mặt sau: câu trả lời hoặc giải thích  
* Trạng thái ghi nhớ của người dùng

### **Trạng thái flashcard**

Người dùng có thể đánh dấu flashcard theo các trạng thái:

* Đã nhớ  
* Chưa nhớ  
* Nhớ một phần

### **Tiêu chí hoàn thành**

* Flashcard được tạo từ nội dung tài liệu hoặc bài học  
* Mỗi flashcard có mặt trước và mặt sau  
* Người dùng có thể chuyển qua lại giữa các flashcard  
* Người dùng có thể đánh dấu trạng thái ghi nhớ  
* Nội dung flashcard ngắn gọn, rõ ràng và dễ học

---

## **6.6 Tạo quiz**

### **Mô tả**

Hệ thống tạo câu hỏi kiểm tra dựa trên nội dung tài liệu hoặc bài học đã tạo.

### **Kết quả mong muốn**

Quiz cần có:

* Câu hỏi trắc nghiệm  
* Các đáp án lựa chọn  
* Đáp án đúng  
* Giải thích đáp án nếu có thể

### **Tiêu chí hoàn thành**

* Quiz liên quan đến nội dung tài liệu  
* Mỗi câu hỏi có các đáp án rõ ràng  
* Mỗi câu hỏi có một đáp án đúng  
* Người dùng có thể chọn đáp án  
* Người dùng có thể xem kết quả sau khi làm quiz  
* Nếu có giải thích đáp án, phần giải thích phải dễ hiểu

---

## **6.7 Tạo slide**

### **Mô tả**

Hệ thống tạo nội dung slide từ tài liệu hoặc khóa học đã tạo.

### **Kết quả mong muốn**

Slide cần có:

* Tiêu đề slide  
* Nội dung chính của từng slide  
* Gợi ý bố cục  
* Gợi ý hình ảnh hoặc biểu đồ nếu cần  
* Nội dung phù hợp để thuyết trình

### **Tiêu chí hoàn thành**

* Slide có cấu trúc rõ ràng  
* Mỗi slide không chứa quá nhiều chữ  
* Nội dung slide bám sát tài liệu  
* Slide phù hợp để dùng trong giảng dạy hoặc thuyết trình  
* Người dùng có thể xem hoặc copy nội dung slide

---

## **6.8 Tạo bản đồ tư duy**

### **Mô tả**

Hệ thống tạo bản đồ tư duy để giúp người dùng hệ thống hóa kiến thức từ tài liệu.

### **Kết quả mong muốn**

Mind map cần có:

* Chủ đề trung tâm  
* Các nhánh chính  
* Các nhánh phụ  
* Mối liên hệ giữa các ý

### **Tiêu chí hoàn thành**

* Mind map thể hiện được cấu trúc kiến thức chính  
* Các nhánh liên quan trực tiếp đến nội dung tài liệu  
* Nội dung dễ hiểu và dễ dùng để ôn tập  
* Có thể hiển thị trên giao diện web dưới dạng cây hoặc sơ đồ đơn giản

---

## **6.9 Xử lý prompt tùy chỉnh**

### **Mô tả**

Người dùng có thể nhập yêu cầu riêng để AI xử lý tài liệu theo mục đích cụ thể.

### **Ví dụ prompt**

* Tóm tắt tài liệu này trong 5 ý chính  
* Tạo slide để thuyết trình trong 5 phút  
* Tạo quiz mức độ khó  
* Giải thích tài liệu này cho học sinh cấp 3  
* Tạo flashcard để ôn tập nhanh  
* Biến tài liệu này thành một khóa học gồm 5 bài

### **Tiêu chí hoàn thành**

* Hệ thống nhận prompt từ người dùng  
* AI xử lý prompt dựa trên tài liệu đã upload  
* Kết quả trả về phù hợp với yêu cầu của người dùng  
* Nếu prompt quá mơ hồ, hệ thống vẫn trả lời theo cách hợp lý hoặc yêu cầu người dùng nhập rõ hơn

---

## **7\. Luồng sử dụng của người dùng**

Luồng sử dụng chính của sản phẩm:

1. Người dùng mở trang web  
2. Người dùng upload tài liệu  
3. Hệ thống kiểm tra định dạng file  
4. Hệ thống trích xuất nội dung từ tài liệu  
5. Người dùng chọn chức năng muốn tạo  
6. Người dùng nhập thêm prompt nếu cần  
7. Hệ thống gửi dữ liệu đến AI để xử lý  
8. Hệ thống trả về kết quả  
9. Người dùng xem kết quả trên giao diện web  
10. Người dùng có thể tiếp tục tạo thêm slide, flashcard, quiz, summary hoặc mind map

---

## **8\. Yêu cầu cho từng team**

## **8.1 Team Backend**

### **Mục tiêu**

Team Backend chịu trách nhiệm xây dựng hệ thống xử lý phía server, bao gồm nhận dữ liệu từ frontend, xử lý file, trích xuất nội dung tài liệu, gọi AI và trả kết quả về cho frontend.

### **Nhiệm vụ chính**

* Xây dựng API cho frontend gọi đến  
* Xử lý upload file  
* Kiểm tra định dạng file  
* Trích xuất nội dung từ PDF, DOCX và TXT  
* Gửi nội dung đến AI để xử lý  
* Tạo course, lesson, summary, flashcard, quiz, slide và mind map  
* Xử lý prompt tùy chỉnh của người dùng  
* Trả dữ liệu về frontend dưới dạng JSON  
* Xử lý lỗi rõ ràng  
* Không để lộ API key trong source code

### **API dự kiến**

| Method | Endpoint | Chức năng |
| ----- | ----- | ----- |
| POST | `/api/upload` | Upload tài liệu |
| POST | `/api/generate-course` | Tạo khóa học |
| POST | `/api/generate-summary` | Tạo bản tóm tắt |
| POST | `/api/generate-flashcards` | Tạo flashcard |
| POST | `/api/generate-quiz` | Tạo quiz |
| POST | `/api/generate-slides` | Tạo nội dung slide |
| POST | `/api/generate-mindmap` | Tạo bản đồ tư duy |
| POST | `/api/custom-prompt` | Xử lý prompt tùy chỉnh |

### **Kết quả cần bàn giao**

* Backend chạy được local  
* API hoạt động ổn định  
* Có file hướng dẫn chạy backend  
* Có file `.env.example`  
* Có dữ liệu mẫu để test  
* Có tài liệu mô tả API cho frontend

---

## **8.2 Team Frontend**

### **Mục tiêu**

Team Frontend chịu trách nhiệm xây dựng giao diện web để người dùng có thể upload tài liệu, chọn chức năng, nhập prompt và xem kết quả do AI tạo ra.

### **Nhiệm vụ chính**

* Xây dựng giao diện trang chủ  
* Xây dựng giao diện upload tài liệu  
* Xây dựng giao diện nhập prompt  
* Xây dựng giao diện hiển thị khóa học  
* Xây dựng giao diện hiển thị summary  
* Xây dựng giao diện flashcard  
* Xây dựng giao diện quiz  
* Xây dựng giao diện slide  
* Xây dựng giao diện mind map  
* Kết nối API với backend  
* Hiển thị trạng thái loading khi AI đang xử lý  
* Hiển thị lỗi khi backend gặp vấn đề  
* Làm giao diện dễ demo và dễ sử dụng

### **Các trang dự kiến**

| Trang | Đường dẫn | Chức năng |
| ----- | ----- | ----- |
| Trang chủ | `/` | Giới thiệu sản phẩm |
| Trang tạo nội dung | `/generate` | Upload file và chọn chức năng |
| Trang kết quả khóa học | `/course/[id]` | Xem khóa học đã tạo |
| Trang flashcard | `/flashcards/[id]` | Học bằng flashcard |
| Trang quiz | `/quiz/[id]` | Làm quiz |
| Trang slide | `/slides/[id]` | Xem nội dung slide |
| Trang mind map | `/mindmap/[id]` | Xem bản đồ tư duy |

### **Component cần có**

* Navbar  
* UploadBox  
* PromptInput  
* FeatureSelector  
* CourseOutline  
* LessonCard  
* SummaryBox  
* FlashcardViewer  
* QuizCard  
* SlidePreview  
* MindMapViewer  
* LoadingState  
* ErrorMessage  
* Button  
* Card

### **Kết quả cần bàn giao**

* Frontend chạy được bằng `npm run dev`  
* Giao diện hoàn chỉnh các chức năng chính  
* Kết nối được với backend  
* Có loading state  
* Có error state  
* Giao diện không bị vỡ trên màn hình laptop  
* Giao diện phù hợp để demo hackathon

---

## **8.3 Team QA**

### **Mục tiêu**

Team QA chịu trách nhiệm kiểm thử sản phẩm để đảm bảo các chức năng chính hoạt động đúng, app ít lỗi và có thể demo ổn định.

### **Nhiệm vụ chính**

* Viết test case cho các chức năng chính  
* Test upload tài liệu  
* Test tạo khóa học  
* Test tạo summary  
* Test tạo flashcard  
* Test tạo quiz  
* Test tạo slide  
* Test tạo mind map  
* Test prompt tùy chỉnh  
* Test giao diện frontend  
* Test API backend  
* Test luồng sử dụng từ đầu đến cuối  
* Ghi nhận bug và báo lại cho team liên quan  
* Kiểm tra lại bug sau khi đã sửa  
* Chuẩn bị checklist trước khi demo

### **Bảng test case mẫu**

| ID | Chức năng | Trường hợp test | Input | Kết quả mong muốn | Trạng thái |
| ----- | ----- | ----- | ----- | ----- | ----- |
| TC01 | Upload | Upload file PDF hợp lệ | `sample.pdf` | Upload thành công | Pass/Fail |
| TC02 | Upload | Upload file sai định dạng | `file.exe` | Hiển thị lỗi định dạng | Pass/Fail |
| TC03 | Upload | Upload file rỗng | File rỗng | Hiển thị lỗi phù hợp | Pass/Fail |
| TC04 | Course | Tạo khóa học từ tài liệu hợp lệ | PDF hợp lệ | Tạo course thành công | Pass/Fail |
| TC05 | Summary | Tạo tóm tắt | Tài liệu hợp lệ | Có bản tóm tắt | Pass/Fail |
| TC06 | Flashcard | Tạo flashcard | Nội dung bài học | Có danh sách flashcard | Pass/Fail |
| TC07 | Quiz | Tạo quiz | Nội dung bài học | Có câu hỏi và đáp án | Pass/Fail |
| TC08 | Slide | Tạo slide | Nội dung tài liệu | Có nội dung slide | Pass/Fail |
| TC09 | Mind map | Tạo mind map | Nội dung tài liệu | Có các nhánh chính | Pass/Fail |
| TC10 | UI | Kiểm tra giao diện | Màn hình nhỏ | Giao diện không vỡ | Pass/Fail |

### **Kết quả cần bàn giao**

* File test case  
* Danh sách bug  
* Trạng thái bug  
* Checklist demo  
* Báo cáo test cuối cùng

---

## **8.4 Team Nội dung và Thuyết trình sản phẩm**

### **Mục tiêu**

Team Nội dung và Thuyết trình chịu trách nhiệm xây dựng câu chuyện sản phẩm, nội dung slide, kịch bản demo và phần trình bày trước ban giám khảo.

### **Nhiệm vụ chính**

* Viết mô tả sản phẩm  
* Xây dựng problem statement  
* Xây dựng solution statement  
* Viết nội dung slide  
* Chuẩn bị kịch bản thuyết trình  
* Chuẩn bị kịch bản demo sản phẩm  
* Phân công người nói  
* Chuẩn bị câu trả lời cho các câu hỏi có thể gặp  
* Làm nổi bật giá trị sản phẩm

### **Cấu trúc slide đề xuất**

1. Tên sản phẩm  
2. Vấn đề cần giải quyết  
3. Giải pháp của sản phẩm  
4. Đối tượng người dùng  
5. Các tính năng chính  
6. Demo sản phẩm  
7. Công nghệ sử dụng  
8. Điểm nổi bật của sản phẩm  
9. Kế hoạch phát triển trong tương lai  
10. Kết luận

### **Kịch bản demo đề xuất**

1. Mở trang web  
2. Giới thiệu giao diện upload tài liệu  
3. Upload một file mẫu  
4. Nhập prompt hoặc chọn chức năng tạo nội dung  
5. Bấm nút tạo nội dung  
6. Hiển thị khóa học được tạo  
7. Hiển thị summary  
8. Hiển thị flashcard  
9. Hiển thị quiz  
10. Hiển thị slide hoặc mind map  
11. Kết luận giá trị sản phẩm

### **Kết quả cần bàn giao**

* Slide thuyết trình  
* Script thuyết trình  
* Script demo sản phẩm  
* Danh sách câu hỏi dự kiến từ ban giám khảo  
* Phân công người trình bày  
* Câu chuyện sản phẩm rõ ràng và thuyết phục

---

## **9\. Yêu cầu phi chức năng**

Sản phẩm cần đáp ứng các yêu cầu sau:

* Giao diện dễ sử dụng  
* Nội dung hiển thị dễ đọc  
* Có trạng thái loading khi AI đang xử lý  
* Có thông báo lỗi rõ ràng  
* Không làm lộ API key  
* Hệ thống không bị crash khi backend lỗi  
* Hệ thống không bị crash khi file upload không hợp lệ  
* Thời gian phản hồi phù hợp cho demo  
* Cấu trúc code dễ chia team làm việc  
* Dữ liệu trả về từ backend phải có format rõ ràng

---

## **10\. Phạm vi chưa làm trong phiên bản đầu**

Phiên bản đầu tiên chưa cần có:

* Đăng nhập tài khoản  
* Thanh toán  
* Mobile app riêng  
* Dashboard admin nâng cao  
* Hệ thống phân quyền người dùng  
* Realtime collaboration  
* Lưu lịch sử học tập đầy đủ  
* AI chính xác tuyệt đối trong mọi trường hợp  
* Export file hoàn chỉnh sang PowerPoint hoặc PDF nếu không kịp thời gian

---

## **11\. Tiêu chí thành công**

Sản phẩm được coi là hoàn thành nếu đạt các tiêu chí sau:

* Người dùng upload được tài liệu  
* Hệ thống đọc được nội dung tài liệu  
* Hệ thống tạo được khóa học từ tài liệu  
* Hệ thống tạo được bài học  
* Hệ thống tạo được summary  
* Hệ thống tạo được flashcard  
* Hệ thống tạo được quiz  
* Hệ thống tạo được nội dung slide  
* Hệ thống tạo được mind map hoặc dữ liệu mind map  
* Người dùng có thể nhập prompt tùy chỉnh  
* Frontend kết nối được với backend  
* Giao diện có loading và error state  
* App có thể demo ổn định  
* Bài thuyết trình giải thích rõ vấn đề, giải pháp và giá trị sản phẩm

---

## **12\. Hướng phát triển tương lai**

Sau phiên bản đầu tiên, sản phẩm có thể phát triển thêm:

* Đăng nhập tài khoản  
* Lưu lịch sử khóa học  
* Export khóa học sang PDF  
* Export slide sang PowerPoint  
* Hỗ trợ nhiều ngôn ngữ  
* Cá nhân hóa lộ trình học  
* Theo dõi tiến độ học tập  
* Dashboard cho giáo viên  
* Chia sẻ khóa học cho người khác  
* Tạo đề kiểm tra tự động theo mức độ khó  
* Tích hợp chatbot hỏi đáp theo từng khóa học

