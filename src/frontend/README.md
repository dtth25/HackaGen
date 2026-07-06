# AI Course Generator Frontend

Frontend này là Next.js App Router app cho Document-to-Study-Pack flow. README root ở `../../README.md` là runbook chính để setup cả backend và frontend từ máy sạch; file này chỉ ghi các lệnh frontend cần nhớ.

## Requirements

- Node.js 20+ và npm.
- Backend FastAPI đang chạy, mặc định ở `http://127.0.0.1:8000`.

## Setup

```bash
npm install
```

## Run Dev

```bash
npm run dev
```

Mở `http://localhost:3000`.

Frontend gọi backend qua Next.js proxy `/api/backend/*`. Nếu backend không chạy ở port mặc định, set:

```bash
BACKEND_API_BASE_URL=http://127.0.0.1:8001
```

`NEXT_PUBLIC_API_BASE_URL` vẫn được hỗ trợ như alias cũ, nhưng `BACKEND_API_BASE_URL` là biến nên dùng cho proxy hiện tại.

## Production Demo

```bash
npm run build
npm run start
```

## Checks

```bash
npm run lint
npm run build
```

## Low-Memory Windows Notes

Next.js 16 dùng Turbopack mặc định cho `next dev` nếu không chỉ định flag. Project này để `npm run dev` chạy `next dev --webpack` nhằm nhẹ hơn cho laptop Windows 8GB RAM. Chỉ dùng `npm run dev:turbo` khi cần benchmark hoặc debug Turbopack.

Nếu `node.exe` dùng quá nhiều RAM hoặc terminal bị treo:

```powershell
taskkill /F /IM node.exe
Remove-Item -Recurse -Force .next
npm run dev
```

Các mẹo khác:

- Đóng dev server trùng lặp trước khi chạy server mới.
- Nếu memory tăng sau một phiên dài, chạy `npm run fresh` để xóa `.next` và restart dev server.
