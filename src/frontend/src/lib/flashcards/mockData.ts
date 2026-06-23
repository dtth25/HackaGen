import { Flashcard } from './types';

export const mockFlashcards: Flashcard[] = [
  {
    id: 'fc_1',
    front: 'Machine Learning là gì?',
    back: 'Machine Learning (ML) là một nhánh của AI cho phép máy tính học hỏi từ dữ liệu mà không cần lập trình tường minh. Nó xây dựng các model từ dữ liệu huấn luyện để đưa ra dự đoán hoặc quyết định.',
    citations: [
      { page: 1, source: 'ml_textbook.pdf', chunk_id: 'chunk_001' },
      { page: 3, source: 'ml_textbook.pdf', chunk_id: 'chunk_003' },
    ],
  },
  {
    id: 'fc_2',
    front: 'Supervised Learning là gì?',
    back: 'Supervised Learning là phương pháp học có giám sát, trong đó model được huấn luyện trên bộ dữ liệu có nhãn (labeled data). Input là features, output là target label. Ví dụ: Classification, Regression.',
    citations: [
      { page: 5, source: 'ml_textbook.pdf', chunk_id: 'chunk_005' },
    ],
  },
  {
    id: 'fc_3',
    front: 'Classification vs Regression',
    back: 'Classification: Dự đoán nhãn phân loại (ví dụ: có/không, loại A/B/C). Regression: Dự đoán giá trị liên tục (ví dụ: giá nhà, nhiệt độ). Cả hai đều thuộc Supervised Learning.',
    citations: [
      { page: 8, source: 'ml_textbook.pdf', chunk_id: 'chunk_008' },
      { page: 10, source: 'ml_textbook.pdf', chunk_id: 'chunk_010' },
    ],
  },
  {
    id: 'fc_4',
    front: 'Logistic Regression hoạt động như thế nào?',
    back: 'Logistic Regression sử dụng hàm sigmoid để chuyển đổi output thành xác suất (0-1). Áp dụng threshold (thường 0.5) để phân loại. Tối ưu bằng Cross-Entropy Loss.',
    citations: [
      { page: 10, source: 'ml_textbook.pdf', chunk_id: 'chunk_010' },
    ],
  },
  {
    id: 'fc_5',
    front: 'Decision Tree là gì?',
    back: 'Decision Tree là model cây quyết định, phân chia dữ liệu dựa trên feature. Mỗi node là điều kiện (if-else), mỗi leaf là kết quả dự đoán. Dễ diễn giải, dễ overfitting.',
    citations: [
      { page: 14, source: 'ml_textbook.pdf', chunk_id: 'chunk_014' },
    ],
  },
  {
    id: 'fc_6',
    front: 'Linear Regression formula là gì?',
    back: 'y = wx + b, trong đó: y là giá trị dự đoán, w là weight (hệ số góc), x là input feature, b là bias (intercept). Mục tiêu: tìm w và b tối ưu để minimize MSE.',
    citations: [
      { page: 22, source: 'ml_textbook.pdf', chunk_id: 'chunk_022' },
    ],
  },
  {
    id: 'fc_7',
    front: 'Unsupervised Learning là gì?',
    back: 'Unsupervised Learning là học không giám sát, làm việc với dữ liệu không có nhãn. Mục tiêu: tìm cấu trúc ẩn, pattern, cluster trong dữ liệu. Ví dụ: Clustering, Dimensionality Reduction.',
    citations: [
      { page: 35, source: 'ml_textbook.pdf', chunk_id: 'chunk_035' },
    ],
  },
  {
    id: 'fc_8',
    front: 'K-means Clustering hoạt động như thế nào?',
    back: 'K-means chia dữ liệu thành K cluster. Thuật toán: 1) Khởi tạo K centroids ngẫu nhiên, 2) Gán điểm vào centroid gần nhất, 3) Cập nhật centroid, 4) Lặp đến hội tụ.',
    citations: [
      { page: 38, source: 'ml_textbook.pdf', chunk_id: 'chunk_038' },
    ],
  },
  {
    id: 'fc_9',
    front: 'PCA là gì?',
    back: 'PCA (Principal Component Analysis) là phương pháp giảm chiều dữ liệu, giữ lại các thành phần chính có phương sai lớn nhất. Giúp giảm nhiễu và tăng tốc độ huấn luyện.',
    citations: [
      { page: 45, source: 'ml_textbook.pdf', chunk_id: 'chunk_045' },
    ],
  },
  {
    id: 'fc_10',
    front: 'Neural Network cơ bản có gì?',
    back: 'Neural Network gồm: Input Layer (nhận dữ liệu), Hidden Layer(s) (xử lý), Output Layer (kết quả). Mỗi neuron tính: output = activation(w·x + b). Activation function: ReLU, Sigmoid, Tanh.',
    citations: [
      { page: 50, source: 'ml_textbook.pdf', chunk_id: 'chunk_050' },
    ],
  },
  {
    id: 'fc_11',
    front: 'Deep Learning là gì?',
    back: 'Deep Learning là ML sử dụng Neural Network với nhiều hidden layers (sâu). Cho phép học biểu diễn phức tạp từ dữ liệu thô. Ứng dụng: Computer Vision, NLP, Speech Recognition.',
    citations: [
      { page: 55, source: 'ml_textbook.pdf', chunk_id: 'chunk_055' },
    ],
  },
  {
    id: 'fc_12',
    front: 'CNN (Convolutional Neural Network) là gì?',
    back: 'CNN là kiến trúc NN chuyên cho ảnh. Gồm: Convolution (trích xuất feature), Pooling (giảm chiều), Fully Connected (phân loại). Tự động học filter patterns từ ảnh.',
    citations: [
      { page: 62, source: 'ml_textbook.pdf', chunk_id: 'chunk_062' },
    ],
  },
];

export const mockFlashcardCourseName = 'Machine Learning Fundamentals';
export const mockFlashcardCourseId = 'course_ml_001';