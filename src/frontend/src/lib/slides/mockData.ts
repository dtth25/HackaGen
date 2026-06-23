import { Slide } from './types';

export const mockSlides: Slide[] = [
  {
    id: 'slide_1',
    title: 'Giới thiệu Machine Learning',
    content: {
      type: 'bullets',
      items: [
        'Machine Learning là nhánh của AI',
        'Cho phép máy tính học hỏi từ dữ liệu',
        'Ứng dụng: Computer Vision, NLP, Recommendation',
      ],
    },
    layoutSuggestion: 'Tiêu đề lớn + bullet points',
    imageSuggestion: 'Hình ảnh minh họa khái niệm ML',
    citations: [
      { page: 1, source: 'ml_textbook.pdf', chunk_id: 'chunk_001' },
    ],
  },
  {
    id: 'slide_2',
    title: 'Các loại Machine Learning',
    content: {
      type: 'bullets',
      items: [
        'Supervised Learning: có nhãn, ví dụ Classification, Regression',
        'Unsupervised Learning: không nhãn, ví dụ Clustering, PCA',
        'Reinforcement Learning: học qua reward/penalty',
      ],
    },
    layoutSuggestion: '3 cột hoặc 3 bullet',
    imageSuggestion: 'Sơ đồ phân loại các loại ML',
    citations: [
      { page: 3, source: 'ml_textbook.pdf', chunk_id: 'chunk_003' },
    ],
  },
  {
    id: 'slide_3',
    title: 'Supervised Learning',
    content: {
      type: 'bullets',
      items: [
        'Input: Features (X)',
        'Output: Label (y)',
        'Mục tiêu: Hàm f sao cho f(X) ≈ y',
        'Ví dụ: Dự đoán giá nhà, phân loại email spam',
      ],
    },
    layoutSuggestion: 'Bullet points',
    imageSuggestion: 'Biểu đồ so sánh input-output',
    citations: [
      { page: 5, source: 'ml_textbook.pdf', chunk_id: 'chunk_005' },
    ],
  },
  {
    id: 'slide_4',
    title: 'Supervised: Classification vs Regression',
    content: {
      type: 'two-column',
      leftColumn: [
        'Classification',
        '• Dự đoán nhãn rời rạc',
        '• Ví dụ: Spam/Not Spam',
        '• Metric: Accuracy, F1-score',
      ],
      rightColumn: [
        'Regression',
        '• Dự đoán giá trị liên tục',
        '• Ví dụ: Giá nhà, nhiệt độ',
        '• Metric: MSE, MAE, R²',
      ],
    },
    layoutSuggestion: 'Hai cột so sánh',
    imageSuggestion: 'Bảng so sánh trực quan',
    citations: [
      { page: 8, source: 'ml_textbook.pdf', chunk_id: 'chunk_008' },
    ],
  },
  {
    id: 'slide_5',
    title: 'Logistic Regression',
    content: {
      type: 'bullets',
      items: [
        'Dùng hàm Sigmoid: σ(z) = 1 / (1 + e^-z)',
        'Output là xác suất (0 đến 1)',
        'Threshold 0.5 để phân loại',
        'Loss: Cross-Entropy',
      ],
    },
    layoutSuggestion: 'Công thức lớn + bullet giải thích',
    imageSuggestion: 'Đồ thị Sigmoid function',
    citations: [
      { page: 10, source: 'ml_textbook.pdf', chunk_id: 'chunk_010' },
    ],
  },
  {
    id: 'slide_6',
    title: 'Decision Tree',
    content: {
      type: 'bullets',
      items: [
        'Cây quyết định: if-else lặp lại',
        'Node: điều kiện trên feature',
        'Leaf: kết quả dự đoán',
        'Ưu: dễ diễn giải | Nhược: dễ overfitting',
      ],
    },
    layoutSuggestion: 'Sơ đồ cây + bullet',
    imageSuggestion: 'Ví dụ cây quyết định nhỏ',
    citations: [
      { page: 14, source: 'ml_textbook.pdf', chunk_id: 'chunk_014' },
    ],
  },
  {
    id: 'slide_7',
    title: 'Unsupervised Learning',
    content: {
      type: 'bullets',
      items: [
        'Làm việc với dữ liệu KHÔNG nhãn',
        'Mục tiêu: tìm pattern, cấu trúc ẩn',
        'Ứng dụng: phân nhóm khách hàng, giảm chiều',
      ],
    },
    layoutSuggestion: 'Background tối, text sáng',
    imageSuggestion: 'Hình ảnh cluster',
    citations: [
      { page: 35, source: 'ml_textbook', chunk_id: 'chunk_035' },
    ],
  },
  {
    id: 'slide_8',
    title: 'K-means Clustering',
    content: {
      type: 'bullets',
      items: [
        'Bước 1: Khởi tạo K centroids',
        'Bước 2: Gán điểm vào centroid gần nhất',
        'Bước 3: Cập nhật centroid (mean)',
        'Bước 4: Lặp đến hội tụ',
      ],
    },
    layoutSuggestion: 'Numbered list',
    imageSuggestion: 'Animation hoặc sơ đồ K-means',
    citations: [
      { page: 38, source: 'ml_textbook.pdf', chunk_id: 'chunk_038' },
    ],
  },
  {
    id: 'slide_9',
    title: 'Neural Networks',
    content: {
      type: 'title-only',
      mainText: 'Input Layer → Hidden Layer(s) → Output Layer',
    },
    layoutSuggestion: 'Sơ đồ kiến trúc NN',
    imageSuggestion: 'Đồ thị kiến trúc neural network',
    citations: [
      { page: 50, source: 'ml_textbook.pdf', chunk_id: 'chunk_050' },
    ],
  },
  {
    id: 'slide_10',
    title: 'Tóm tắt',
    content: {
      type: 'bullets',
      items: [
        'Supervised: Classification, Regression',
        'Unsupervised: Clustering, PCA',
        'Neural Networks → Deep Learning → CNN',
        'Citation-First: mọi nội dung đều có trích dẫn',
      ],
    },
    layoutSuggestion: 'Slide tóm tắt cuối',
    imageSuggestion: 'Logo AI Course Generator',
    citations: [
      { page: 62, source: 'ml_textbook.pdf', chunk_id: 'chunk_062' },
    ],
  },
];

export const mockSlideCourseName = 'Machine Learning Fundamentals';
export const mockSlideCourseId = 'course_ml_001';