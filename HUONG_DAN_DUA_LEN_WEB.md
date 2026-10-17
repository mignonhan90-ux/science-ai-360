# SCIENCE AI 360 — Đưa bản demo lên web, không cài Python trên Windows

**Đây là bản xem thử công khai, không phải hệ thống production.** Chưa nhập tên, ảnh, điểm hay thông tin học sinh thật. Tài khoản mẫu và dữ liệu mẫu là công khai; bất kỳ ai biết đường link đều có thể đăng nhập. Dữ liệu SQLite trên hosting miễn phí có thể bị xóa khi khởi động lại hoặc triển khai mới.

## Cách làm đơn giản qua GitHub + Render

1. Tạo tài khoản tại https://github.com và https://render.com (đăng nhập Render bằng GitHub).
2. Giải nén gói ZIP. Vào GitHub > **New repository** > đặt tên `science-ai-360` > Create repository.
3. Trong repository, chọn **Add file > Upload files**. Tải lên **toàn bộ file bên trong** thư mục `science-ai-360-cloud` (không phải chỉ tải file ZIP), giữ nguyên thư mục `static/` và `tests/`. Commit changes.
4. Trong Render, chọn **New > Blueprint** và chọn repository vừa tạo. Render sẽ đọc `render.yaml` để tạo dịch vụ Docker. Xem lại gói dịch vụ, giá và quyền truy cập trước khi xác nhận. Gói miễn phí nếu còn được cung cấp có thể ngủ khi không dùng; giá và giới hạn có thể thay đổi.
5. Đợi trạng thái deploy thành **Live**. Mở URL dạng `https://science-ai-360-preview-....onrender.com` do Render cấp (không đoán URL).
6. Đăng nhập thử: `giaovien` / `Teacher123!` hoặc `hocsinh` / `Student123!`. **Chỉ dùng dữ liệu giả.**

Nếu giao diện mở nhưng không đăng nhập được, vào Render > service > **Environment**, kiểm tra `ENABLE_DEMO_ACCOUNTS=1`, rồi **Manual Deploy**. Nếu lỗi, vào Render > **Logs** và gửi ảnh hoặc đoạn lỗi để sửa.

## Trước khi triển khai thật cho trường học

Phải bổ sung tài khoản riêng (không dùng mật khẩu demo), chống thử mật khẩu hàng loạt, quyền truy cập từng lớp, lưu trữ dữ liệu bền vững (PostgreSQL), HTTPS, giới hạn yêu cầu, backup, quản lý dữ liệu cá nhân trẻ em, nhật ký kiểm toán và kiểm thử bảo mật. **Chưa tích hợp AI tạo sinh**.

## Chạy kiểm thử (dành cho người phát triển)

`python -m unittest discover -s tests -v`
